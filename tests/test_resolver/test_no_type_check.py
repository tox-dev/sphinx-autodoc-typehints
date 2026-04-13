from __future__ import annotations

import typing

from sphinx_autodoc_typehints._resolver._type_hints import _get_type_hint, get_all_type_hints


@typing.no_type_check
def _decorated_function(x: int, y: str) -> bool:
    return bool(x) and bool(y)


@typing.no_type_check
class _DecoratedClass:
    def method(self, value: int) -> str:  # noqa: PLR6301
        return str(value)


class _Target:
    pass


@typing.no_type_check
def _deferred_forward_ref(obj: _Target) -> _Target:
    return obj


def test_no_type_check_function_still_resolves_hints() -> None:
    result = get_all_type_hints([], _decorated_function, "_decorated_function", {})
    assert result == {"x": int, "y": str, "return": bool}


def test_no_type_check_method_still_resolves_hints() -> None:
    result = _get_type_hint([], "_DecoratedClass.method", _DecoratedClass.method, {})
    assert result == {"value": int, "return": str}


def test_no_type_check_resolves_future_string_annotations() -> None:
    result = _get_type_hint([], "_deferred_forward_ref", _deferred_forward_ref, {})
    assert result == {"obj": _Target, "return": _Target}
