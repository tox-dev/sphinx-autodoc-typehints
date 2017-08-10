import pytest
import sys

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
    (str,                           ':py:class:`str`'),
    (int,                           ':py:class:`int`'),
    (type(None),                    '``None``'),
    (Any,                           ':py:data:`~typing.Any`'),
    (AnyStr,                        ':py:data:`~typing.AnyStr`'),
    (Generic[T],                    ':py:class:`~typing.Generic`\\[\\~T]'),
    (Mapping,                       ':py:class:`~typing.Mapping`\\[\\~KT, \\+VT_co]'),
    (Mapping[T, int],               ':py:class:`~typing.Mapping`\\[\\~T, :py:class:`int`]'),
    (Mapping[str, V],               ':py:class:`~typing.Mapping`\\[:py:class:`str`, \\-V]'),
    (Mapping[T, U],                 ':py:class:`~typing.Mapping`\\[\\~T, \\+U]'),
    (Mapping[str, bool],            ':py:class:`~typing.Mapping`\\[:py:class:`str`, '
                                    ':py:class:`bool`]'),
    (Dict,                          ':py:class:`~typing.Dict`\\[\\~KT, \\~VT]'),
    (Dict[T, int],                  ':py:class:`~typing.Dict`\\[\\~T, :py:class:`int`]'),
    (Dict[str, V],                  ':py:class:`~typing.Dict`\\[:py:class:`str`, \\-V]'),
    (Dict[T, U],                    ':py:class:`~typing.Dict`\\[\\~T, \\+U]'),
    (Dict[str, bool],               ':py:class:`~typing.Dict`\\[:py:class:`str`, '
                                    ':py:class:`bool`]'),
    (Tuple,                         ':py:class:`~typing.Tuple`'),
    (Tuple[str, bool],              ':py:class:`~typing.Tuple`\\[:py:class:`str`, '
                                    ':py:class:`bool`]'),
    (Tuple[int, int, int],          ':py:class:`~typing.Tuple`\\[:py:class:`int`, '
                                    ':py:class:`int`, :py:class:`int`]'),
    (Tuple[str, ...],               ':py:class:`~typing.Tuple`\\[:py:class:`str`, ...]'),
    (Union,                         ':py:data:`~typing.Union`'),
    (Union[str, bool],              ':py:data:`~typing.Union`\\[:py:class:`str`, '
                                    ':py:class:`bool`]'),
    pytest.param(Union[str, Any],   ':py:data:`~typing.Union`\\[:py:class:`str`, '
                                    ':py:data:`~typing.Any`]',
                 marks=pytest.mark.skipif((3, 5, 0) <= sys.version_info[:3] <= (3, 5, 2),
                                          reason='Union erases the str on 3.5.0 -> 3.5.2')),
    (Optional[str],                 ':py:data:`~typing.Optional`\\[:py:class:`str`]'),
    (Callable,                      ':py:data:`~typing.Callable`'),
    (Callable[..., int],            ':py:data:`~typing.Callable`\\[..., :py:class:`int`]'),
    (Callable[[int], int],          ':py:data:`~typing.Callable`\\[\\[:py:class:`int`], '
                                    ':py:class:`int`]'),
    (Callable[[int, str], bool],    ':py:data:`~typing.Callable`\\[\\[:py:class:`int`, '
                                    ':py:class:`str`], :py:class:`bool`]'),
    (Callable[[int, str], None],    ':py:data:`~typing.Callable`\\[\\[:py:class:`int`, '
                                    ':py:class:`str`], ``None``]'),
    (Callable[[T], T],              ':py:data:`~typing.Callable`\\[\\[\\~T], \\~T]'),
    (Pattern,                       ':py:class:`~typing.Pattern`\\[:py:data:`~typing.AnyStr`]'),
    (Pattern[str],                  ':py:class:`~typing.Pattern`\\[:py:class:`str`]'),
    (A,                             ':py:class:`~%s.A`' % __name__),
    (B,                             ':py:class:`~%s.B`\\[\\~T]' % __name__)
])
def test_format_annotation(annotation, expected_result):
    result = format_annotation(annotation)
    assert result == expected_result


@pytest.mark.skipif(Type is None, reason='Type does not exist in the typing module')
@pytest.mark.parametrize('type_param, expected_result', [
    (None, ':py:class:`~typing.Type`\\[\\+CT'),
    (A, ':py:class:`~typing.Type`\\[:py:class:`~%s.A`]' % __name__)
])
def test_format_annotation_type(type_param, expected_result):
    annotation = Type[type_param] if type_param else Type
    result = format_annotation(annotation)
    assert result.startswith(expected_result)


def test_process_docstring_slot_wrapper():
    lines = []
    process_docstring(None, 'class', 'SlotWrapper', Slotted, None, lines)
    assert not lines
