"""
The annotation walker, which renders a type and everything nested in it on an explicit stack instead of by recursion.

It also holds the readers of starred aliases and type parameters that the signature headers share.
"""

from __future__ import annotations

import typing  # probed at runtime for names typing_extensions backports
from dataclasses import dataclass
from enum import Enum
from operator import attrgetter
from re import fullmatch, sub
from sys import version_info
from types import GenericAlias
from typing import (
    TYPE_CHECKING,
    Concatenate,
    Final,
    ForwardRef,
    NewType,
    ParamSpec,
    ParamSpecArgs,
    ParamSpecKwargs,
    TypeVar,
    TypeVarTuple,
    get_args,
    get_origin,
)

from sphinx.ext.autodoc.mock import ismock
from sphinx.util import rst
from sphinx.util.inspect import TypeAliasForwardRef

from sphinx_autodoc_typehints._objects import alias_lookup_names
from sphinx_autodoc_typehints._private_imports import INVALID_BUILTIN_CLASSES
from sphinx_autodoc_typehints._refs import MyTypeAliasForwardRef, WrittenTypeAlias, is_type_alias, split_arguments
from sphinx_autodoc_typehints._types import sentinel

from ..context import render_context
from ..deferred import defer_alias_choice
from ..intersphinx import inventory, type_mapping
from .aliases import (
    alias_crossref,
    alias_name_reference,
    can_expand_alias,
    reaches_itself,
    underlying_type_alias,
)
from .names import (
    PYDATA_ANNOTATIONS,
    fixup_module_name,
    get_annotation_args,
    get_annotation_class_name,
    get_annotation_module,
    name_prefix,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable
    from typing import TypeAliasType

    from sphinx.config import Config

    from sphinx_autodoc_typehints._types import Hint, RenderNode, TypeParam

    from ..context import TypehintsFormatter

    # yields the annotations nested in a node, receives each one rendered, and yields _Rendered last
    type _Frame = Generator[RenderNode | _Rendered, str, None]


def format_annotation(annotation: RenderNode, config: Config, *, short_literals: bool = False) -> str:
    """
    Render `annotation` as reST cross-reference markup, walking it on an explicit stack in place of recursion.

    A PEP 695 type alias may reference itself (`type T = int | list[T]`), and a generic one may do so through its
    subscripted form (`type T[X] = X | list[T[X]]`). Python supports such a type, yet expanding it goes on forever,
    and a recursive walk would exhaust the interpreter recursion limit. An alias referencing itself renders as a
    cross-reference to its own name.
    """
    # active holds the aliases under expansion on the path from the root, so a self-reference does not expand again
    stack: list[tuple[_Frame, RenderNode]] = [
        (_format_node(annotation, config, short_literals=short_literals), annotation)
    ]
    active = {id(alias)} if (alias := underlying_type_alias(annotation)) is not None else set()
    rendered: str | None = None
    while True:
        frame, node = stack[-1]
        child = next(frame) if rendered is None else frame.send(rendered)
        if isinstance(child, _Rendered):
            stack.pop()
            if (alias := underlying_type_alias(node)) is not None:
                active.discard(id(alias))
            if not stack:
                return child.text
            rendered = child.text
        elif (alias := underlying_type_alias(child)) is not None and id(alias) in active and reaches_itself(alias):
            rendered = alias_crossref(alias, config) or alias_name_reference(alias, config)
        else:
            stack.append((_format_node(child, config, short_literals=short_literals), child))
            if alias is not None:
                active.add(id(alias))
            rendered = None


@dataclass(frozen=True, slots=True)
class _Rendered:
    text: str


def _format_node(annotation: RenderNode, config: Config, *, short_literals: bool) -> _Frame:
    formatter: TypehintsFormatter | None = config.typehints_formatter
    if (
        formatter is not None
        # the written name is ours to show, the formatter sees the type it stands for
        and (text := formatter(annotation.value if isinstance(annotation, WrittenTypeAlias) else annotation, config))
        is not None
    ) or (text := _atom(annotation, config)) is not None:
        yield _Rendered(text)
    elif (unstarred := unstar(annotation)) is not None:
        # render it the way `*Ts` renders
        unpacked = typing.Unpack[
            unstarred  # ty: ignore[invalid-type-form]  # https://github.com/astral-sh/ty/issues/727
        ]
        yield _Rendered((yield unpacked))
    elif isinstance(annotation, (tuple, list)):
        parts: list[str] = []
        yield from _format_into(parts, annotation)
        if isinstance(annotation, list):
            yield _Rendered(f"\\[{', '.join(parts)}]")
        else:
            yield _Rendered(f"({parts[0]}, )" if len(parts) == 1 else f"({', '.join(parts)})")
    elif isinstance(annotation, TypeAliasForwardRef):
        yield from _forward_alias(annotation, config)
    elif is_type_alias(annotation):
        yield from _type_alias(annotation, config)
    elif is_type_alias(alias := get_origin(annotation)) or isinstance(alias, TypeAliasForwardRef):
        yield from _subscripted_alias(annotation, alias, config)
    else:
        yield from _class_reference(annotation, config, short_literals=short_literals)


def _atom(annotation: RenderNode, config: Config) -> str | None:
    if isinstance(annotation, ForwardRef):
        return annotation.__forward_arg__
    if annotation is None or annotation is type(None):
        return ":py:obj:`None`"
    if annotation is Ellipsis:
        return ":py:data:`...<Ellipsis>`"
    # a PEP 661 sentinel stands for itself, so the reference names it in its defining module rather than by its type
    if isinstance(annotation, sentinel):
        module = fixup_module_name(config, annotation.__module__)
        return f":py:data:`{name_prefix(config)}{module}.{annotation.__name__}`"
    # a subscripted mock, such as `Thing[int]` of a module in `autodoc_mock_imports`, keeps only `str()` of the
    # subscript, `<class 'int'>` or `numpy.float64`, as its name and the subscripted object as its module, so this
    # reads the arguments back from that text
    if ismock(annotation) and not (name := getattr(annotation, "__name__", "")).isidentifier():
        text = sub(r"<class '([^']+)'>", r"\1", name).removeprefix("(").removesuffix(")")
        return f":py:class:`~{annotation.__module__}`\\ \\[{_format_mock_arguments(text)}]"
    return None


def _format_mock_arguments(text: str) -> str:
    return ", ".join(_format_mock_argument(stripped) for part in split_arguments(text) if (stripped := part.strip()))


def _format_mock_argument(part: str) -> str:
    if fullmatch(r"[\w.]+", part):
        return f":py:class:`{'~' if '.' in part else ''}{part}`"
    # an argument is itself subscripted, as `dict[str, typing.Any]`, or a list of them, as `Callable` takes
    if match := fullmatch(r"([\w.]*)\[(.*)\]", part):
        name, arguments = match.groups()
        subscript = f"\\[{_format_mock_arguments(arguments)}]"
        return f"{_format_mock_argument(name)}\\ {subscript}" if name else subscript
    return f"``{part}``"


def unstar(annotation: RenderNode) -> GenericAlias | None:
    """Return the alias `*tuple[int, ...]` stars, a starred alias keeping its class and only flagging the star."""
    if isinstance(annotation, GenericAlias) and annotation.__unpacked__:
        return GenericAlias(
            annotation.__origin__,  # ty: ignore[invalid-argument-type]  # any origin works at runtime
            annotation.__args__,
        )
    return None


# a generator cannot hand back a list without ending, so the caller passes the one to fill
def _format_into(parts: list[str], nodes: Iterable[RenderNode]) -> _Frame:
    for annotation in nodes:
        rendered = yield annotation
        parts.append(rendered)


def _forward_alias(annotation: TypeAliasForwardRef, config: Config) -> _Frame:
    prefix = name_prefix(config)
    context = render_context(config)
    module_prefix = context.module_prefix
    if isinstance(annotation, WrittenTypeAlias) and not context.signature:
        rendered = yield annotation.value
        for candidate in reversed(alias_lookup_names(module_prefix, annotation.name)):
            linked = f":py:type:`{prefix}{candidate}`"
            rendered = defer_alias_choice(config, linked, rendered, objtype="type") or rendered
        yield _Rendered(rendered)
    elif (env := context.env) is not None and (
        documented := next(
            (
                candidate
                for candidate in alias_lookup_names(module_prefix, annotation.name)
                if (entry := env.domains.python_domain.objects.get(candidate)) is not None and entry.objtype == "type"
            ),
            None,
        )
    ) is not None:
        yield _Rendered(f":py:type:`{prefix}{documented}`")
    elif isinstance(annotation, WrittenTypeAlias):
        # signature text is final once written, so only an alias documented by now can show
        yield _Rendered((yield annotation.value))
    elif isinstance(annotation, MyTypeAliasForwardRef) and annotation.crossref:
        yield _Rendered(f":py:type:`{prefix}{annotation.name}`")
    elif isinstance(annotation, MyTypeAliasForwardRef) and annotation.configured:
        # the target may have its documentation as data or in a document Sphinx reads later, and the value may be
        # display text alone, so link it only where the reference resolves once Sphinx has read every document
        linked = f":py:obj:`{prefix}{annotation.name}`"
        yield _Rendered(defer_alias_choice(config, linked, annotation.name) or annotation.name)
    else:
        yield _Rendered(annotation.name)


def _type_alias(annotation: TypeAliasType, config: Config) -> _Frame:
    if (crossref := alias_crossref(annotation, config)) is not None:
        yield _Rendered(crossref)
    else:
        # named before the value evaluates, which can run a TYPE_CHECKING block that imports the module re-exporting it
        reference = alias_name_reference(annotation, config)
        if can_expand_alias(annotation, config):
            expanded = yield annotation.__value__
            yield _Rendered(defer_alias_choice(config, reference, expanded) or expanded)
        else:
            yield _Rendered(reference)


# `NDArray[np.void]` of `type NDArray[ScalarT] = ...` is a plain types.GenericAlias, which would otherwise render
# as the name of its class
def _subscripted_alias(
    annotation: Hint | NewType | None, alias: TypeAliasType | TypeAliasForwardRef, config: Config
) -> _Frame:
    args = get_args(annotation)
    expanded: str | None = None
    if isinstance(alias, TypeAliasForwardRef):
        rendered_alias = yield alias
    elif (crossref := alias_crossref(alias, config)) is not None:
        rendered_alias = crossref
    else:
        # the runtime accepts a subscript of any arity, and a TypeVarTuple or ParamSpec absorbs any count
        if (
            any(not isinstance(param, TypeVar) for param in alias.__type_params__)
            or len(alias.__type_params__) == len(args)
        ) and can_expand_alias(alias, config):
            if isinstance(value := alias.__value__, TypeVar):
                # `type Ident[X] = X` has a bare type param as its value, which the substitution replaces whole
                substituted = dict(zip(alias.__type_params__, args, strict=False)).get(value, value)
            else:
                try:
                    substituted = value[args]
                except TypeError:  # the value ignores its type params, e.g. `type Count[X] = int`
                    substituted = value
            expanded = yield substituted
        # cannot expand, so name the alias instead of leaking its type params
        rendered_alias = alias_name_reference(alias, config)
    parts: list[str] = []
    yield from _format_into(parts, args)
    subscripted = f"{rendered_alias}\\ \\[{', '.join(parts)}]"
    yield _Rendered(subscripted if expanded is None else defer_alias_choice(config, subscripted, expanded) or expanded)


def _class_reference(annotation: Hint | NewType | None, config: Config, *, short_literals: bool) -> _Frame:
    try:
        module = get_annotation_module(annotation)
        class_name = get_annotation_class_name(annotation, module)
        args = get_annotation_args(annotation, module, class_name)
    except ValueError:
        yield _Rendered(str(annotation).strip("'"))
    else:
        # where the docs place a class Python defines elsewhere, such as pathlib.Path living in pathlib._local from 3.13
        if documented := INVALID_BUILTIN_CLASSES.get((module, class_name)):
            module, _, class_name = documented.rpartition(".")
        module = fixup_module_name(config, module)
        # typing_extensions backports names to older Pythons, and the Python docs list a backported name under typing
        if module == "typing_extensions" and hasattr(typing, class_name):
            module = "typing"
        internal_path = f"{module}.{class_name}"
        local_path: str | None = None
        if mapped := type_mapping(config).get(internal_path):
            local_path = internal_path
            module, _, class_name = mapped.rpartition(".")
        full_name = f"{module}.{class_name}" if module != "builtins" else class_name
        fully_qualified = config.typehints_fully_qualified
        is_bars_union = bool(
            (version_info >= (3, 14) and full_name == "typing.Union")
            or full_name == "types.UnionType"
            or (config.always_use_bars_union and type(annotation).__qualname__ == "_UnionGenericAlias")
            or getattr(annotation, "__typehints_bars__", False)
        )
        # the inventory may document another Python version, and intersphinx resolves only the role its entry has
        documented = inventory(render_context(config).env)
        # a typing_extensions name is the same kind of object as its typing counterpart
        pydata_key = ("typing" if module == "typing_extensions" else module, class_name)
        role = next((kind for kind in ("class", "data") if full_name in documented.get(f"py:{kind}", {})), None) or (
            "data" if pydata_key in PYDATA_ANNOTATIONS else "class"
        )
        yield from _named_class(
            _Reference(
                annotation=annotation,
                config=config,
                full_name="" if is_bars_union else full_name,
                role=role,
                prefix="" if fully_qualified or full_name == class_name else "~",
                fully_qualified=fully_qualified,
                local_path=local_path,
                args=args,
                is_bars_union=is_bars_union,
                short_literals=short_literals,
            )
        )


@dataclass(slots=True)
class _Reference:
    annotation: Hint | NewType | None
    config: Config
    full_name: str
    role: str
    prefix: str
    fully_qualified: bool
    local_path: str | None
    args: tuple[RenderNode, ...]
    is_bars_union: bool
    short_literals: bool
    args_format: str = "\\[{}]"
    formatted_args: str | None = ""


def _named_class(reference: _Reference) -> _Frame:
    special = next((handle for matches, handle in _SPECIAL_FORMS if matches(reference)), None)
    # a form that renders whole ends the frame here, others only change how the arguments render
    if special is not None and (frame := special(reference)) is not None:
        yield from frame
    if reference.args and not reference.formatted_args:
        parts: list[str] = []
        # typing stores the parameter list filling a ParamSpec slot as a tuple
        yield from _format_into(parts, (list(arg) if isinstance(arg, tuple) else arg for arg in reference.args))
        reference.formatted_args = reference.args_format.format(", ".join(parts))
    text = f":py:{reference.role}:`{reference.prefix}{reference.full_name}`"
    if reference.local_path is not None:
        # a type the project documents itself links there, the intersphinx name is only the fallback
        local = f":py:{reference.role}:`{name_prefix(reference.config)}{reference.local_path}`"
        text = defer_alias_choice(reference.config, local, text) or text
    yield _Rendered(f"{text}{'\\ ' if reference.formatted_args else ''}{reference.formatted_args}")


def _new_type(reference: _Reference) -> _Frame:
    config = reference.config
    # a signature names the class itself, a bare typing.NewType, as any class; a docstring field reads its supertype,
    # and the AttributeError a bare one raises there stays
    if not isinstance(annotation := reference.annotation, NewType):
        if not render_context(config).signature:
            attrgetter("__supertype__")(annotation)
        return
    module = fixup_module_name(config, annotation.__module__)
    qualified = f"{module}.{annotation.__name__}" if module else annotation.__name__
    text = f":py:class:`{'' if reference.fully_qualified or not module else '~'}{qualified}`"
    # a signature names the type alone, as Python writes it
    if render_context(config).signature:
        yield _Rendered(text)
    else:
        yield _Rendered(f"{text} ({(yield annotation.__supertype__)})")


def _annotated(reference: _Reference) -> _Frame:
    # the form itself, a bare typing.Annotated, has no origin, and the AttributeError reading it raises stays
    yield _Rendered((yield attrgetter("__origin__")(reference.annotation)))


def _type_variable(reference: _Reference) -> _Frame:
    # the class itself, as typing.TypeVar, renders as any class does
    if not isinstance(annotation := reference.annotation, TypeVar | ParamSpec | TypeVarTuple):
        return
    config = reference.config
    if annotation in (context := render_context(config)).declared_type_params:
        # the signature lists it with its bound, constraints and default already
        yield _Rendered(f"``{annotation.__name__}``")
    elif context.signature:
        # a signature names a module-level one by its defining module, as Python writes it
        module = fixup_module_name(config, annotation.__module__)
        yield _Rendered(f":py:class:`{name_prefix(config)}{module}.{annotation.__name__}`")
    else:
        # typing.TypeVarTuple has neither a bound nor a variance, only the typing_extensions backport adds them
        fields = type_param_fields(annotation, lambda dunder: getattr(annotation, f"__{dunder}__", None))
        params: dict[str, str | bool] = {}
        if "bound" in fields:
            params["bound"] = yield fields["bound"]
        params |= {kind: True for kind in ("covariant", "contravariant") if getattr(annotation, f"__{kind}__", None)}
        if "default" in fields:
            params["default"] = yield fields["default"]
        # the escaped space lets a role follow the = without a visible gap
        keywords = "".join(f", {k}=\\ {v}" for k, v in params.items())
        reference.args_format = f"\\(``{annotation.__name__}``{', {}' if reference.args else ''}{keywords})"
        reference.formatted_args = None if reference.args else reference.args_format


def type_param_fields[Value](param: TypeParam, read: Callable[[str], Value]) -> dict[str, Value]:
    """Return the bound and the default `param` declares, as `read` gives the attribute of each kind."""
    fields: dict[str, Value] = {}
    # an unbound ParamSpec reports NoneType as its bound before CPython gh-151955
    if (bound := read("bound")) is not None and bound is not type(None):
        fields["bound"] = bound
    # PEP 696 defaults exist on typing from 3.13 and on typing_extensions before that
    if getattr(param, "has_default", lambda: False)():
        fields["default"] = read("default")
    return fields


def _param_spec_component(reference: _Reference) -> _Frame:
    # the class itself, as typing.ParamSpecArgs, renders as any class does
    if not isinstance(annotation := reference.annotation, ParamSpecArgs | ParamSpecKwargs):
        return
    if annotation.__origin__ in (context := render_context(reference.config)).declared_type_params or context.signature:
        # its repr is the P.args form a signature writes
        yield _Rendered(f"``{annotation!r}``")
    else:
        reference.formatted_args = f"\\(``{annotation.__origin__.__name__}``)"


def _optional(reference: _Reference) -> None:  # pragma: <3.14 cover
    reference.args = tuple(x for x in reference.args if x is not type(None))


def _union_with_none(reference: _Reference) -> None:  # pragma: <3.14 cover
    if not reference.config.simplify_optional_unions:
        reference.args_format = f"\\[:py:data:`{reference.prefix}typing.Union`\\ \\[{{}}]]"
        reference.full_name = "typing.Optional"
        reference.role = "data"
        _optional(reference)


def _empty_tuple(reference: _Reference) -> None:
    # the empty tuple shows a subscript with no arguments, which bare tuple, of any length, lacks
    reference.formatted_args = "\\[()]"


def _callable(reference: _Reference) -> _Frame:
    parts: list[str] = []
    yield from _format_into(parts, reference.args)
    first = reference.args[0]
    # a ParamSpec or Concatenate stands for the whole parameter list, so it takes no brackets of its own
    params = (
        parts[0] if isinstance(first, ParamSpec) or get_origin(first) is Concatenate else f"\\[{', '.join(parts[:-1])}]"
    )
    reference.formatted_args = f"\\[{params}, {parts[-1]}]"


def _literal(reference: _Reference) -> _Frame:
    literal_parts: list[str] = []
    for arg in reference.args:
        if isinstance(arg, Enum):
            module = fixup_module_name(reference.config, (enum_cls := type(arg)).__module__)
            member = f"{enum_cls.__qualname__}.{arg.name}"
            if not module:
                literal_parts.append(f":py:attr:`{member}`")
            elif reference.fully_qualified:
                literal_parts.append(f":py:attr:`{module}.{member}`")
            else:
                # a ~ would keep only the member name, and members of different enums would read the same
                literal_parts.append(f":py:attr:`{member} <{module}.{member}>`")
        else:
            # an inline literal cannot hold a backtick, the literal role takes it escaped
            literal_parts.append(f":literal:`{rst.escape(text)}`" if "`" in (text := repr(arg)) else f"``{text}``")
    if reference.short_literals:
        yield _Rendered(" | ".join(literal_parts))
    else:
        reference.formatted_args = f"\\[{', '.join(literal_parts)}]"


def _bars_union(reference: _Reference) -> _Frame:
    if reference.args:
        parts: list[str] = []
        yield from _format_into(parts, reference.args)
        yield _Rendered(" | ".join(parts))
    else:
        yield _Rendered(f":py:{'class' if version_info >= (3, 14) else 'data'}:`{reference.prefix}typing.Union`")


# built once, as every class reference walks it; the first test to match picks the handler, so the order matters
_SPECIAL_FORMS: Final[tuple[tuple[Callable[[_Reference], bool], Callable[[_Reference], _Frame | None]], ...]] = (
    (lambda ref: ref.full_name == "typing.NewType", _new_type),
    (lambda ref: ref.full_name == "typing.Annotated", _annotated),
    (lambda ref: ref.full_name in {"typing.TypeVar", "typing.ParamSpec", "typing.TypeVarTuple"}, _type_variable),
    (lambda ref: ref.full_name in {"typing.ParamSpecArgs", "typing.ParamSpecKwargs"}, _param_spec_component),
    (lambda ref: ref.full_name == "typing.Optional", _optional),
    (lambda ref: ref.full_name in {"typing.Union", "types.UnionType"} and type(None) in ref.args, _union_with_none),
    (
        lambda ref: ref.full_name in {"tuple", "typing.Tuple"} and getattr(ref.annotation, "__args__", None) == (),
        _empty_tuple,
    ),
    (
        lambda ref: (
            ref.full_name in {"typing.Callable", "collections.abc.Callable"}
            and bool(ref.args)
            and ref.args[0] is not ...
        ),
        _callable,
    ),
    (lambda ref: ref.full_name == "typing.Literal" and bool(ref.args), _literal),
    (lambda ref: ref.is_bars_union, _bars_union),
)


__all__ = [
    "format_annotation",
    "type_param_fields",
    "unstar",
]
