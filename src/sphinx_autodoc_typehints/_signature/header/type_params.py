"""Writes the type parameters of a generic class, function or alias after its name, as in `Stack[T: int]`."""

from __future__ import annotations

from functools import partial
from sys import version_info
from typing import TYPE_CHECKING, Literal

from docutils import nodes
from sphinx import addnodes
from sphinx.util.typing import stringify_annotation

from sphinx_autodoc_typehints._objects import object_at
from sphinx_autodoc_typehints._private_imports import parse_annotation, parse_type_list
from sphinx_autodoc_typehints._render import type_param_fields, unstar
from sphinx_autodoc_typehints._resolve import TYPE_PARAM_KINDS, guard_bound, type_params_of
from sphinx_autodoc_typehints._types import sentinel

from .lookup import documented_signatures

if version_info >= (3, 14):  # pragma: >=3.14 cover
    from annotationlib import Format, call_evaluate_function

if TYPE_CHECKING:
    from docutils.nodes import Node
    from sphinx.application import Sphinx

    from sphinx_autodoc_typehints._types import Hint, TypeParam


type _Mode = Literal["fully-qualified-except-typing", "smart"]


def add_type_params(app: Sphinx, domain: str, objtype: str, contentnode: addnodes.desc_content) -> None:
    """
    Show the type parameters of a generic object after its name, as in `class Stack[T: int]`.

    autodoc writes no type parameters into the directive it generates, and it leaves no hook to add them for a type
    alias, so they go into the signature the Python domain built from that directive.
    """
    if domain != "py":
        return
    # data or an attribute holding a generic instance reads the class's type parameters off it, which it doesn't declare
    if objtype not in {"class", "exception", "function", "method", "classmethod", "staticmethod", "type"}:
        return
    mode: _Mode = "fully-qualified-except-typing" if app.config.typehints_fully_qualified else "smart"
    for signode, module, fullname in documented_signatures(app.env, contentnode):
        if (
            not any(isinstance(node, addnodes.desc_type_parameter_list) for node in signode)
            and (name := next((node for node in signode if isinstance(node, addnodes.desc_name)), None)) is not None
            and (params := type_params_of(documented := object_at(module, fullname.split(".")), legacy=True))
        ):
            declarations = []
            # PEP 695 evaluates a bound, constraints or default on first access, in the globals of the module
            with guard_bound(app.config.autodoc_mock_imports, documented):
                for param in params:
                    # typeshed types __name__ as the property naming an instance, so read the class's through its MRO
                    declaration = f"{TYPE_PARAM_KINDS[type(param).__mro__[0].__name__]}{param.__name__}"
                    fields = type_param_fields(param, partial(_lazy, param))
                    if isinstance(constraints := _lazy(param, "constraints"), tuple) and constraints:
                        declaration += f": ({', '.join(_stringify(constraint, mode) for constraint in constraints)})"
                    elif (bound := fields.get("bound", _UNKNOWN)) is not _UNKNOWN:
                        declaration += f": {_stringify(bound, mode)}"
                    if (default := fields.get("default", _UNKNOWN)) is not _UNKNOWN:
                        declaration += f" = {_stringify(default, mode)}"
                    declarations.append(declaration)
                type_params = parse_type_list(", ".join(declarations), app.env)
            # Sphinx keeps the source text of a default, so a `~` would show and no name would link
            for default in list(type_params.findall(_is_default)):
                # the default of a TypeVarTuple unpacks a tuple, which does not parse as an annotation on its own
                star = [addnodes.desc_sig_operator("", "*")] if (text := default.astext()).startswith("*") else []
                default[:] = [*star, *parse_annotation(text.removeprefix("*"), app.env)]
            signode.insert(signode.index(name) + 1, type_params)


# PEP 695 evaluates these on access; where that fails, a forward reference stands in, or an unknown value before 3.14
def _lazy(param: TypeParam, kind: str) -> Hint | _UNKNOWN | None:
    try:
        value = getattr(param, f"__{kind}__", None)
    except Exception:  # ruff:ignore[blind-except]  # an annotation runs user code, which may raise anything
        if version_info >= (3, 14):  # pragma: >=3.14 cover
            value = call_evaluate_function(getattr(param, f"evaluate_{kind}"), Format.FORWARDREF)
        else:  # pragma: <3.14 cover
            value = _UNKNOWN
    return value


def _stringify(value: Hint | list[Hint] | None, mode: _Mode) -> str:
    if isinstance(value, list):
        return f"[{', '.join(_stringify(item, mode) for item in value)}]"
    if (alias := unstar(value)) is not None:
        return f"*{stringify_annotation(alias, mode)}"
    return stringify_annotation(value, mode)


# no `Final`: ty stops reading an annotated sentinel as a type https://github.com/astral-sh/ty/issues/4737
_UNKNOWN = sentinel("_UNKNOWN")


def _is_default(node: Node) -> bool:
    return isinstance(node, nodes.inline) and "default_value" in node["classes"]


__all__ = [
    "add_type_params",
]
