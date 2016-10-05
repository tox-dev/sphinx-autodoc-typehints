from typing import (Any, Callable, Dict, Generic, Mapping, Optional, Pattern,
                    Tuple, Type, TypeVar, Union)

import pytest
from sphinx_autodoc_typehints import format_annotation

T = TypeVar('T')
U = TypeVar('U', covariant=True)
V = TypeVar('V', contravariant=True)


class A:
    def get_type(self) -> Type['A']:
        return type(self)


class B(Generic[T]):
    pass


class C(Dict[T, int]):
    pass


@pytest.mark.parametrize('annotation, expected_result', [
    (str,                           ':class:`str`'),
    (int,                           ':class:`int`'),
    (type(None),                    '``None``'),
    (Any,                           ':class:`~typing.Any`'),
    (Generic[T],                    ':class:`~typing.Generic`\\[\\~T]'),
    (Mapping,                       ':class:`~typing.Mapping`\\[\\~KT, \\+VT_co]'),
    (Mapping[T, int],               ':class:`~typing.Mapping`\\[\\~T, :class:`int`]'),
    (Mapping[str, V],               ':class:`~typing.Mapping`\\[:class:`str`, \\-V]'),
    (Mapping[T, U],                 ':class:`~typing.Mapping`\\[\\~T, \\+U]'),
    (Mapping[str, bool],            ':class:`~typing.Mapping`\\[:class:`str`, :class:`bool`]'),
    (Dict,                          ':class:`~typing.Dict`\\[\\~KT, \\~VT]'),
    (Dict[T, int],                  ':class:`~typing.Dict`\\[\\~T, :class:`int`]'),
    (Dict[str, V],                  ':class:`~typing.Dict`\\[:class:`str`, \\-V]'),
    (Dict[T, U],                    ':class:`~typing.Dict`\\[\\~T, \\+U]'),
    (Dict[str, bool],               ':class:`~typing.Dict`\\[:class:`str`, :class:`bool`]'),
    (Tuple,                         ':class:`~typing.Tuple`'),
    (Tuple[str, bool],              ':class:`~typing.Tuple`\\[:class:`str`, :class:`bool`]'),
    (Tuple[int, int, int],          ':class:`~typing.Tuple`\\[:class:`int`, :class:`int`, '
                                    ':class:`int`]'),
    (Tuple[str, ...],               ':class:`~typing.Tuple`\\[:class:`str`, ...]'),
    (Union,                         ':class:`~typing.Union`'),
    (Union[str, bool],              ':class:`~typing.Union`\\[:class:`str`, :class:`bool`]'),
    (Optional[str],                 ':class:`~typing.Optional`\\[:class:`str`]'),
    (Optional[Union[int, str]],     ':class:`~typing.Optional`\\[:class:`~typing.Union`'
                                    '\\[:class:`int`, :class:`str`]]'),
    (Union[Optional[int], str],     ':class:`~typing.Optional`\\[:class:`~typing.Union`'
                                    '\\[:class:`int`, :class:`str`]]'),
    (Union[int, Optional[str]],     ':class:`~typing.Optional`\\[:class:`~typing.Union`'
                                    '\\[:class:`int`, :class:`str`]]'),
    (Callable,                      ':class:`~typing.Callable`'),
    (Callable[..., int],            ':class:`~typing.Callable`\\[..., :class:`int`]'),
    (Callable[[int], int],          ':class:`~typing.Callable`\\[\\[:class:`int`], :class:`int`]'),
    (Callable[[int, str], bool],    ':class:`~typing.Callable`\\[\\[:class:`int`, :class:`str`], '
                                    ':class:`bool`]'),
    (Callable[[int, str], None],    ':class:`~typing.Callable`\\[\\[:class:`int`, :class:`str`], '
                                    '``None``]'),
    (Callable[[T], T],              ':class:`~typing.Callable`\\[\\[\\~T], \\~T]'),
    (Pattern,                       ':class:`~typing.Pattern`\\[\\~AnyStr]'),
    (Pattern[str],                  ':class:`~typing.Pattern`\\[:class:`str`]'),
    (A,                             ':class:`~%s.A`' % __name__),
    (B,                             ':class:`~%s.B`\\[\\~T]' % __name__),
    (C,                             ':class:`~%s.C`\\[\\~T]' % __name__),
    (Type,                          ':class:`~typing.Type`\\[\\+CT]'),
    (Type[A],                       ':class:`~typing.Type`\\[:class:`~%s.A`]' % __name__),
    (Type['A'],                     ':class:`~typing.Type`\\[A]'),
    (Type['str'],                   ':class:`~typing.Type`\\[:class:`str`]'),
])
def test_format_annotation(annotation, expected_result):
    result = format_annotation(annotation, None)
    assert result == expected_result


def test_format_annotation_with_obj():
    result = format_annotation(Type['A'], A.get_type)
    assert result == ':class:`~typing.Type`\\[:class:`~%s.A`]' % __name__

    result = format_annotation(Type['A'], A)
    assert result == ':class:`~typing.Type`\\[A]'

test_format_annotation_with_obj()
