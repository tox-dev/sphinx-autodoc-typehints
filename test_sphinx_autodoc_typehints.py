import pytest

from sphinx_autodoc_typehints import format_annotation, process_docstring

try:
    from backports.typing import (Any, AnyStr, Callable, Dict, Generic, Mapping, Optional, Pattern,
                                  Tuple, TypeVar, Union)
except ImportError:
    from typing import (Any, AnyStr, Callable, Dict, Generic, Mapping, Optional, Pattern,
                        Tuple, TypeVar, Union)

try:
    from backports.typing import Type
except ImportError:
    try:
        from typing import Type
    except ImportError:
        Type = None


T = TypeVar('T')
U = TypeVar('U', covariant=True)
V = TypeVar('V', contravariant=True)


class A:
    def get_type(self):
        return type(self)


class B(Generic[T]):
    pass


class Slotted:
    __slots__ = ()


@pytest.mark.parametrize('annotation, expected_result', [
    (str,                           ':class:`str`'),
    (int,                           ':class:`int`'),
    (type(None),                    '``None``'),
    (Any,                           ':data:`~typing.Any`'),
    (AnyStr,                        ':data:`~typing.AnyStr`'),
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
    (Union,                         ':data:`~typing.Union`'),
    (Union[str, bool],              ':data:`~typing.Union`\\[:class:`str`, :class:`bool`]'),
    (Union[str, Any],               ':data:`~typing.Union`\\[:class:`str`, :data:`~typing.Any`]'),
    (Optional[str],                 ':data:`~typing.Optional`\\[:class:`str`]'),
    (Callable,                      ':data:`~typing.Callable`'),
    (Callable[..., int],            ':data:`~typing.Callable`\\[..., :class:`int`]'),
    (Callable[[int], int],          ':data:`~typing.Callable`\\[\\[:class:`int`], :class:`int`]'),
    (Callable[[int, str], bool],    ':data:`~typing.Callable`\\[\\[:class:`int`, :class:`str`], '
                                    ':class:`bool`]'),
    (Callable[[int, str], None],    ':data:`~typing.Callable`\\[\\[:class:`int`, :class:`str`], '
                                    '``None``]'),
    (Callable[[T], T],              ':data:`~typing.Callable`\\[\\[\\~T], \\~T]'),
    (Pattern,                       ':class:`~typing.Pattern`\\[:data:`~typing.AnyStr`]'),
    (Pattern[str],                  ':class:`~typing.Pattern`\\[:class:`str`]'),
    (A,                             ':class:`~%s.A`' % __name__),
    (B,                             ':class:`~%s.B`\\[\\~T]' % __name__)
])
def test_format_annotation(annotation, expected_result):
    result = format_annotation(annotation)
    assert result == expected_result


@pytest.mark.skipif(Type is None, reason='Type does not exist in the typing module')
@pytest.mark.parametrize('type_param, expected_result', [
    (None, ':class:`~typing.Type`\\[\\+CT'),
    (A, ':class:`~typing.Type`\\[:class:`~%s.A`]' % __name__)
])
def test_format_annotation_type(type_param, expected_result):
    annotation = Type[type_param] if type_param else Type
    result = format_annotation(annotation)
    assert result.startswith(expected_result)


def test_process_docstring_slot_wrapper():
    lines = []
    process_docstring(None, 'class', 'SlotWrapper', Slotted, None, lines)
    assert not lines
