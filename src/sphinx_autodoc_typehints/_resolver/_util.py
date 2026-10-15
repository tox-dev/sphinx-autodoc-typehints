"""Shared utilities for type hint resolution."""

from __future__ import annotations

import ast
import inspect
import sys
import textwrap
import types
from collections import defaultdict
from functools import cache, partial
from typing import TYPE_CHECKING, Any, Final, Union, cast, get_args, get_origin, get_type_hints

from sphinx.errors import PycodeError
from sphinx.pycode import ModuleAnalyzer
from sphinx.pycode.parser import VariableCommentPicker

from sphinx_autodoc_typehints._annotations import (
    MyTypeAliasForwardRef,
    WrittenTypeAlias,
    alias_lookup_names,
    enclosing_scopes,
)

if sys.version_info >= (3, 14):  # pragma: >=3.14 cover
    from typing import evaluate_forward_ref

    from annotationlib import Format, ForwardRef, get_annotations

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Mapping

    from sphinx.environment import BuildEnvironment

_DOCUMENTED: Final = "sphinx_autodoc_typehints_documented"
_UNION: Final = "__sphinx_autodoc_typehints_union__"
_SUBSCRIPT: Final = "__sphinx_autodoc_typehints_subscript__"
#: Per module, what its ``TYPE_CHECKING`` block binds a name to that the module binds to something else at runtime.
SHADOWED_BY_GUARD: Final[dict[str, dict[str, Any]]] = {}


def note_documented(env: BuildEnvironment, name: str) -> None:
    """Remember that autodoc documents ``name`` on the page being read, so its header is the extension's to render."""
    cast("set[str]", env.temp_data.setdefault(_DOCUMENTED, set())).add(name)


def is_documented(env: BuildEnvironment, name: str) -> bool:
    """
    Tell whether autodoc documents ``name`` on the page being read.

    autodoc already looked such a name up, so looking it up again runs no package ``__getattr__`` autodoc did not run;
    looking up a name written by hand could import, raise, or rename what autodoc documents later.
    """
    return name in (env.temp_data.get(_DOCUMENTED) or ())


def get_obj_location(obj: Any) -> str | None:
    try:
        filepath = inspect.getsourcefile(obj) or inspect.getfile(obj)
    except TypeError:
        return None
    # code without a file, such as the __init__ a dataclass generates, is named like <string>
    if filepath.startswith("<"):
        return None
    try:
        lineno = inspect.getsourcelines(obj)[1]
    except (OSError, TypeError):
        return filepath
    else:
        return f"{filepath}:{lineno}"


def type_hints(obj: Any, globalns: dict[str, Any] | None, localns: Mapping[str, Any] | None) -> dict[str, Any]:
    """
    Return :func:`typing.get_type_hints` with the extras, reading a name a guard shadows as the guard binds it.

    A class whose ``__class_getitem__`` hands back the class itself, as SQLAlchemy's ``TypeEngine`` does, evaluates
    ``TypeEngine[Any]`` to a bare ``TypeEngine``, so an annotation left holding one is evaluated again from its source.
    """
    if sys.version_info >= (3, 14) and _reads_shadowed_name(obj):  # pragma: >=3.14 cover
        hints = _hints_from_source(obj, globalns, localns)
    elif isinstance(obj, type) and any(guarded_names(base) for base in obj.__mro__):
        hints = _hints_of_bases(obj, globalns, localns, _declared_hints)
    else:
        hints = get_type_hints(obj, globalns, localns, include_extras=True)
    if not (dropped := {key for key, hint in hints.items() if any(map(_dropped_arguments, _parts(hint)))}):
        return hints
    return hints | {
        key: _evaluated_again(hints[key], source, scope_globals, scope_locals)
        for key, source, scope_globals, scope_locals in _written_sources(obj, dropped, globalns, localns)
    }


def _parts(hint: Any) -> Iterator[Any]:
    yield hint
    # the parameters of a Callable come as a list
    for argument in hint if isinstance(hint, list) else get_args(hint):
        yield from _parts(argument)


def _dropped_arguments(part: Any) -> bool:
    return isinstance(part, type) and get_origin(part) is None and _drops_arguments(part)


def _kept_arguments(part: Any) -> bool:
    # such a class subscripts to itself, so only evaluate_annotation builds a generic alias of it
    return isinstance(part, types.GenericAlias) and _drops_arguments(part.__origin__)


def _drops_arguments(cls: type) -> bool:
    # the standard library subscripts its classes in C, only a __class_getitem__ written in Python can drop arguments
    method = inspect.getattr_static(cls, "__class_getitem__", None)
    return inspect.isfunction(getattr(method, "__func__", method))


def _written_sources(
    obj: Any, keys: set[str], globalns: dict[str, Any] | None, localns: Mapping[str, Any] | None
) -> Iterator[tuple[str, str, dict[str, Any], Mapping[str, Any]]]:
    """
    Yield each of ``keys`` with its annotation as the source writes it and the namespaces it evaluates in.

    A class yields its bases first, so the class that declares an attribute last comes last, as get_type_hints orders
    them.
    """
    if inspect.isroutine(obj) or isinstance(obj, types.ModuleType):
        written = written_annotations(obj) if inspect.isroutine(obj) else _source_annotations(obj.__name__, "")
        scope_globals = annotation_globals(obj) if globalns is None else globalns
        scope_locals = scope_globals if localns is None else localns
        yield from ((key, written[key], scope_globals, scope_locals) for key in keys & written.keys())
        # the __init__ a dataclass or attrs generates takes its annotations from the fields the class body writes
        if (
            inspect.isroutine(obj)
            and (unwritten := keys - written.keys())
            and isinstance(owner := _owning_class(obj), type)
        ):
            yield from _written_sources(owner, unwritten, None, localns)
        return
    # the attribute of an instance is annotated in its class
    for base in reversed((obj if isinstance(obj, type) else type(obj)).__mro__):
        base_globals = annotation_globals(base) if globalns is None else globalns
        base_locals = dict(vars(base)) if localns is None else localns
        if localns is None and globalns is None:
            base_globals, base_locals = base_locals, base_globals
        # a generic class binds its type parameters in a scope of their own, neither the module nor the class body
        if params := {param.__name__: param for param in getattr(base, "__type_params__", ())}:
            base_locals = {**base_locals, **params}
        written = _source_annotations(base.__module__, base.__qualname__)
        yield from ((key, written[key], dict(base_globals), base_locals) for key in keys & written.keys())


def _owning_class(routine: Any) -> Any:
    return object_at(getattr(defining_module(routine), "__name__", None), routine.__qualname__.split(".")[:-1])


def _source_annotations(module: str, qualname: str) -> dict[str, str]:
    """
    Return the annotations the body of ``qualname`` writes, the module's own for an empty name.

    autodoc replaces the annotations a module and its classes hold with what it evaluated, so only the source has them.
    """
    try:
        analyzer = ModuleAnalyzer.for_module(module)
        analyzer.analyze()
    except PycodeError:
        return {}
    return {attribute: source for (scope, attribute), source in _unambiguous(analyzer).items() if scope == qualname}


@cache
def _unambiguous(analyzer: ModuleAnalyzer) -> dict[tuple[str, str], str]:
    """
    Return the annotations of the analyzed source that are written one way only.

    Sphinx keeps the last annotation written for a name, which under ``if``/``else`` may be the branch that did not run.
    """
    picker = _AnnotationsPicker(analyzer.code.splitlines(keepends=True), "utf-8")
    picker.visit(ast.parse(analyzer.code, type_comments=True))
    return {key: written.pop() for key, written in picker.written.items() if len(written) == 1}


class _AnnotationsPicker(VariableCommentPicker):
    def __init__(self, buffers: list[str], encoding: str) -> None:
        super().__init__(buffers, encoding)
        self.written: defaultdict[tuple[str, str], set[str]] = defaultdict(set)

    def add_variable_annotation(self, name: str, annotation: ast.AST) -> None:
        super().add_variable_annotation(name, annotation)
        if qualname := self.get_qualname_for(name):
            key = ".".join(qualname[:-1]), name
            self.written[key].add(self.annotations[key])


def _evaluated_again(hint: Any, source: str, globalns: dict[str, Any], localns: Mapping[str, Any]) -> Any:
    try:
        value = evaluate_annotation(source, globalns, localns)
        # a quoted annotation evaluates to the string inside it
        if isinstance(value, str):
            value = evaluate_annotation(value, globalns, localns)
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        return hint
    # an alias named in the source holds the forward references get_type_hints resolved, so it only wins when it kept
    # the arguments it was evaluated for
    return value if any(map(_kept_arguments, _parts(value))) else hint


def evaluate_annotation(source: str, globalns: dict[str, Any], localns: Mapping[str, Any]) -> Any:
    """Evaluate an annotation written as ``source``, keeping the arguments a class subscripted in it drops."""
    tree = _KeepArguments().visit(ast.parse(source, mode="eval"))
    # a nested scope, such as a generator expression or a lambda, reads the globals but not the locals, so the helpers
    # go in a copy of the globals, which leaves those of the module untouched
    namespace = {**globalns, _SUBSCRIPT: _subscript}
    try:
        return eval(compile(ast.fix_missing_locations(tree), "<annotation>", "eval"), namespace, localns)  # ruff:ignore[suspicious-eval-usage]
    except TypeError:
        # X | Y means Union[X, Y], which also accepts operands that don't support |, such as the objects
        # autodoc_mock_imports puts in place of a missing module's
        code = compile(ast.fix_missing_locations(_PipeAsUnion().visit(tree)), "<annotation>", "eval")
        return eval(code, namespace | {_UNION: Union}, localns)  # ruff:ignore[suspicious-eval-usage]


def _subscript(value: Any, item: Any) -> Any:
    # a generic alias renders as the subscription written, and links the class
    return (
        types.GenericAlias(value, item)
        if (subscripted := value[item]) is value and isinstance(value, type)
        else subscripted
    )


class _KeepArguments(ast.NodeTransformer):
    def visit_Subscript(self, node: ast.Subscript) -> ast.expr:
        self.generic_visit(node)
        # a call takes no slice as an argument
        if any(isinstance(item, ast.Slice) for item in (node.slice, *getattr(node.slice, "elts", ()))):
            return node
        return ast.Call(func=ast.Name(id=_SUBSCRIPT, ctx=ast.Load()), args=[node.value, node.slice], keywords=[])


class _PipeAsUnion(ast.NodeTransformer):
    def visit_BinOp(self, node: ast.BinOp) -> ast.expr:
        self.generic_visit(node)
        if not isinstance(node.op, ast.BitOr):
            return node
        members = ast.Tuple(elts=[node.left, node.right], ctx=ast.Load())
        return ast.Subscript(value=ast.Name(id=_UNION, ctx=ast.Load()), slice=members, ctx=ast.Load())


def _hints_of_bases(
    cls: type,
    globalns: dict[str, Any] | None,
    localns: Mapping[str, Any] | None,
    evaluate: Callable[[type, dict[str, Any], Mapping[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate the annotations of each base as :func:`typing.get_type_hints` would, in the globals of its module."""
    hints: dict[str, Any] = {}
    for base in reversed(cls.__mro__):
        base_globals = annotation_globals(base) if globalns is None else globalns
        base_locals = dict(vars(base)) if localns is None else localns
        if localns is None and globalns is None:
            # as get_type_hints does, so the names of the module come before those of the class body
            base_globals, base_locals = base_locals, base_globals
        hints |= evaluate(base, dict(base_globals), base_locals)
    return hints


def _declared_hints(base: type, globalns: dict[str, Any], localns: Mapping[str, Any]) -> dict[str, Any]:
    # a class holding only what the base declares, as get_type_hints evaluates the annotations of every base it holds
    declared = type(
        base.__name__,
        (),
        {"__annotations__": inspect.get_annotations(base), "__type_params__": getattr(base, "__type_params__", ())},
    )
    return get_type_hints(declared, globalns, localns, include_extras=True)


def _reads_shadowed_name(obj: Any) -> bool:  # pragma: >=3.14 cover
    """
    Whether an annotation of ``obj`` evaluated at runtime names what the ``TYPE_CHECKING`` block of its module shadows.

    PEP 649 evaluates such an annotation in the globals it was compiled in, which hold the runtime binding of the name.
    """
    return any(
        (getattr(owner, "__annotate__", None) is not None or _holds_values(owner))
        and (shadowed := guarded_names(owner))
        and any(
            name in shadowed
            for source in _written(owner).values()
            if isinstance(source, str)
            for name in _names_read(source)
        )
        for owner in (obj.__mro__ if isinstance(obj, type) else (obj,))
    )


def _names_read(source: str) -> Iterator[str]:  # pragma: >=3.14 cover
    # as annotationlib compiles ``*Ts``, the starred annotation of ``*args``
    code = f"({source},)[0]" if source.lstrip().startswith("*") else source
    try:
        tree = ast.parse(code, mode="eval")
    except SyntaxError:
        # the source prints a value it holds no code for, such as a lambda in ``Annotated`` metadata, by its repr
        return
    yield from (node.id for node in ast.walk(tree) if isinstance(node, ast.Name))


def _hints_from_source(  # pragma: >=3.14 cover
    obj: Any, globalns: dict[str, Any] | None, localns: Mapping[str, Any] | None
) -> dict[str, Any]:
    """Evaluate the source of each annotation as :func:`typing.get_type_hints` would, in the guarded globals."""
    if not isinstance(obj, type):
        globalns = annotation_globals(obj) if globalns is None else globalns
        return _evaluate_written(
            obj, globalns, globalns if localns is None else localns, is_argument=not isinstance(obj, types.ModuleType)
        )
    return _hints_of_bases(obj, globalns, localns, partial(_evaluate_written, is_argument=False))


def _evaluate_written(  # pragma: >=3.14 cover
    owner: Any, globalns: dict[str, Any], localns: Mapping[str, Any], *, is_argument: bool
) -> dict[str, Any]:
    params = getattr(owner, "__type_params__", ())
    hints: dict[str, Any] = {}
    for name, source in _written(owner).items():
        if isinstance(source, str):
            ref = ForwardRef(source, is_argument=is_argument, is_class=isinstance(owner, type))
            try:
                value = evaluate_forward_ref(
                    ref,
                    owner=owner,
                    globals=globalns,
                    locals=localns,
                    # typeshed declares a 3-tuple of one TypeVar, ParamSpec and TypeVarTuple, not a tuple of any of them
                    type_params=params,  # ty: ignore[invalid-argument-type]
                )
            except Exception:
                # a value printed by its repr, as a lambda is, may not evaluate, so it reads as the runtime evaluated it
                if name not in (runtime := getattr(owner, "__annotations__", None) or {}):
                    raise
                value = runtime[name]
        else:
            value = source
        hints[name] = type(None) if value is None else value
    return hints


def _written(owner: Any) -> dict[str, Any]:  # pragma: >=3.14 cover
    """
    Return the source of each annotation of ``owner``, or its value where the source is gone.

    The values include what was added to the annotations after they were evaluated, as attrs fields are.
    """
    stored = dict(getattr(owner, "__annotations__", None) or {})
    if getattr(owner, "__annotate__", None) is not None:
        return stored | get_annotations(owner, format=Format.STRING)
    return stored | _annotated_assignments(owner) if _holds_values(owner) else stored


def _holds_values(owner: Any) -> bool:  # pragma: >=3.14 cover
    """
    Whether autodoc replaced the lazy annotations of a module or class with their values.

    It does so to add the types its comments give, which drops the code that would evaluate them again.
    """
    return isinstance(owner, type | types.ModuleType) and any(
        not isinstance(value, str) for value in (getattr(owner, "__annotations__", None) or {}).values()
    )


def _annotated_assignments(owner: type | types.ModuleType) -> dict[str, str]:  # pragma: >=3.14 cover
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(owner)))
    except (OSError, TypeError, SyntaxError):
        return {}
    body = cast("ast.ClassDef", tree.body[0]).body if isinstance(owner, type) else tree.body
    return {
        statement.target.id: ast.unparse(statement.annotation)
        for statement in body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }


def annotation_globals(obj: Any) -> dict[str, Any]:
    """
    Return the globals the annotations of ``obj`` evaluate in, read as a type checker reads them.

    Generated code such as an attrs ``__init__`` runs in a globals dict of its own, which misses the names the module
    binds afterwards, so the module's names fill the gaps.
    """
    if (module := defining_module(obj)) is None:
        return getattr(obj, "__globals__", {})
    own = getattr(obj, "__globals__", vars(module))
    names = own if own is vars(module) else {**vars(module), **own}
    return {**names, **shadowed} if (shadowed := guarded_names(obj)) else names


def guarded_names(obj: Any) -> dict[str, Any]:
    """Return what the ``TYPE_CHECKING`` block of the module of ``obj`` binds the names it rebinds at runtime to."""
    return SHADOWED_BY_GUARD.get(module.__name__, {}) if (module := defining_module(obj)) else {}


def defining_module(obj: Any) -> types.ModuleType | None:
    # re-exporting reassigns ``__module__``, while the globals stay those of the module defining the object
    return sys.modules.get(getattr(obj, "__globals__", {}).get("__name__", "")) or inspect.getmodule(obj)


def object_at(module: str | None, path: Iterable[str]) -> Any:
    """Return the object ``path`` names in the imported ``module``, ``None`` where a part of it is missing."""
    found: Any = sys.modules.get(module or "")
    for part in path:
        if found is None:
            return None
        found = getattr(found, part, None)
    return found


def type_alias_namespace(
    type_aliases: Mapping[str, str], obj: Any, module_prefix: str, env: BuildEnvironment | None
) -> tuple[dict[str, MyTypeAliasForwardRef], dict[str, WrittenTypeAlias]]:
    """Return the names the annotations of ``obj`` resolve to an alias, and the annotations written as an alias."""
    localns = {key: MyTypeAliasForwardRef(value, configured=True) for key, value in type_aliases.items()}
    if env is None:
        return localns, {}
    deferred, eager = collect_documented_type_aliases(obj, module_prefix, env)
    return localns | deferred, eager


def collect_documented_type_aliases(
    obj: Any, module_prefix: str, env: BuildEnvironment
) -> tuple[dict[str, MyTypeAliasForwardRef], dict[str, WrittenTypeAlias]]:
    py_objects = env.get_domain("py").objects  # ty: ignore[unresolved-attribute]
    deferred = _collect_module_type_aliases(module_prefix, py_objects)
    written_as: dict[str, WrittenTypeAlias] = {}

    # PEP 649 (Python 3.14+): annotation expressions only run on access and may fail at runtime
    # (TYPE_CHECKING-only names, subscripting a non-generic class)
    try:
        raw_annotations = getattr(obj, "__annotations__", {})
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        return deferred, written_as
    if not raw_annotations:
        return deferred, written_as

    obj_globals = annotation_globals(obj) if hasattr(obj, "__globals__") else {}
    # an alias evaluates to the object it names (``Count = int``), so only the annotation as written tells them apart;
    # a module or class holds no globals to find the alias in, so its source is not worth parsing
    written = written_annotations(obj) if obj_globals else {}
    for key, annotation in raw_annotations.items():
        if isinstance(annotation, str):
            if _is_documented_type(annotation, module_prefix, py_objects):
                ref = MyTypeAliasForwardRef(annotation)
                ref.crossref = True
                deferred[annotation] = ref
        elif (name := written.get(key)) and (alias := written_type_alias(name, annotation, obj_globals)):
            written_as[key] = alias

    return deferred, written_as


def written_type_alias(written: str, value: Any, namespace: Mapping[str, Any]) -> WrittenTypeAlias | None:
    """Return the module-level alias an annotation ``written`` as its bare name names, if it evaluated to ``value``."""
    if written.startswith("_") or written not in namespace or namespace[written] is not value:
        return None
    # whether the alias is documented is only known once every document is read, so rendering decides
    return WrittenTypeAlias(written, value)


def _collect_module_type_aliases(module_prefix: str, py_objects: dict[str, Any]) -> dict[str, MyTypeAliasForwardRef]:
    scopes = set(enclosing_scopes(module_prefix))
    result: dict[str, MyTypeAliasForwardRef] = {}
    for fqn, obj_info in py_objects.items():
        if obj_info.objtype == "type" and fqn.rpartition(".")[0] in scopes:
            short_name = fqn.rsplit(".", 1)[-1]
            ref = MyTypeAliasForwardRef(short_name)
            ref.crossref = True
            result[short_name] = ref
    return result


def written_annotations(obj: Any) -> dict[str, str]:
    try:
        node = ast.parse(textwrap.dedent(inspect.getsource(obj))).body[0]
    except (OSError, TypeError, SyntaxError):
        return {}
    if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return {}
    arguments = node.args
    params = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs, arguments.vararg, arguments.kwarg]
    written = {param.arg: ast.unparse(param.annotation) for param in params if param and param.annotation}
    return written | ({"return": ast.unparse(node.returns)} if node.returns else {})


def _is_documented_type(name: str, module_prefix: str, py_objects: dict[str, Any]) -> bool:
    return any(
        candidate in py_objects and py_objects[candidate].objtype == "type"
        for candidate in alias_lookup_names(module_prefix, name)
    )


__all__ = [
    "SHADOWED_BY_GUARD",
    "annotation_globals",
    "collect_documented_type_aliases",
    "defining_module",
    "evaluate_annotation",
    "get_obj_location",
    "guarded_names",
    "is_documented",
    "note_documented",
    "object_at",
    "type_alias_namespace",
    "type_hints",
    "written_annotations",
    "written_type_alias",
]
