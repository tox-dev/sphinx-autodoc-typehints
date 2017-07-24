from collections import namedtuple
from typing import Any, AnyStr, Callable, Dict, Generic, Mapping, Optional, Pattern, Tuple, Type, TypeVar, Union

import pytest

from sphinx_autodoc_typehints import format_annotation, process_docstring

T = TypeVar('T')
U = TypeVar('U', covariant=True)
V = TypeVar('V', contravariant=True)


class ExampleA:
    def get_type(self):
        return type(self)


class ExampleB(Generic[T]):
    pass


class Slotted:
    __slots__ = ()


@pytest.mark.parametrize('annotation, expected_result', [
    (str, ':class:`str`'),
    (int, ':class:`int`'),
    (type(None), '``None``'),
    (Any, ':data:`~typing.Any`'),
    (AnyStr, ':data:`~typing.AnyStr`'),
    (Generic[T], ':class:`~typing.Generic`\\[\\~T]'),
    (Generic[T], ':class:`~typing.Generic`\\[\\~T]'),
    (Mapping[T, int], ':class:`~typing.Mapping`\\[\\~T, :class:`int`]'),
    (Mapping[str, V], ':class:`~typing.Mapping`\\[:class:`str`, \\-V]'),
    (Mapping[T, U], ':class:`~typing.Mapping`\\[\\~T, \\+U]'),
    (Mapping[str, bool], ':class:`~typing.Mapping`\\[:class:`str`, :class:`bool`]'),
    (Dict, ':class:`~typing.Dict`\\[\\~KT, \\~VT]'),
    (Dict[T, int], ':class:`~typing.Dict`\\[\\~T, :class:`int`]'),
    (Dict[str, V], ':class:`~typing.Dict`\\[:class:`str`, \\-V]'),
    (Dict[T, U], ':class:`~typing.Dict`\\[\\~T, \\+U]'),
    (Dict[str, bool], ':class:`~typing.Dict`\\[:class:`str`, :class:`bool`]'),
    (Tuple, ':class:`~typing.Tuple`'),
    (Tuple[str, bool], ':class:`~typing.Tuple`\\[:class:`str`, :class:`bool`]'),
    (Tuple[int, int, int], ':class:`~typing.Tuple`\\[:class:`int`, :class:`int`, '
                           ':class:`int`]'),
    (Tuple[str, ...], ':class:`~typing.Tuple`\\[:class:`str`, ...]'),
    (Union, ':data:`~typing.Union`'),
    (Union[str, bool], ':data:`~typing.Union`\\[:class:`str`, :class:`bool`]'),
    (Optional[str], ':data:`~typing.Optional`\\[:class:`str`]'),
    (Callable, ':data:`~typing.Callable`'),
    (Callable[..., int], ':data:`~typing.Callable`\\[..., :class:`int`]'),
    (Callable[[int], int], ':data:`~typing.Callable`\\[\\[:class:`int`], :class:`int`]'),
    (Callable[[int, str], bool], ':data:`~typing.Callable`\\[\\[:class:`int`, :class:`str`], '
                                 ':class:`bool`]'),
    (Callable[[int, str], None], ':data:`~typing.Callable`\\[\\[:class:`int`, :class:`str`], '
                                 '``None``]'),
    (Callable[[T], T], ':data:`~typing.Callable`\\[\\[\\~T], \\~T]'),
    (Pattern, ':class:`~typing.Pattern`\\[:data:`~typing.AnyStr`]'),
    (Pattern[str], ':class:`~typing.Pattern`\\[:class:`str`]'),
    (ExampleA, ':class:`~%s.ExampleA`' % __name__),
    (ExampleB, ':class:`~%s.ExampleB`\\[\\~T]' % __name__)
])
def test_format_annotation(annotation, expected_result):
    result = format_annotation(annotation, {})
    assert result == expected_result


def test_format_annotation_test():
    result = format_annotation(Tuple[str, ...], {})
    assert result


@pytest.mark.skipif(Type is None, reason='Type does not exist in the typing module')
@pytest.mark.parametrize('type_param, expected_result', [
    (None, ':class:`~typing.Type`\\[\\+CT'),
    (ExampleA, ':class:`~typing.Type`\\[:class:`~%s.ExampleA`]' % __name__)
])
def test_format_annotation_type(type_param, expected_result):
    annotation = Type[type_param] if type_param else Type
    result = format_annotation(annotation, {})
    assert result.startswith(expected_result)


def test_process_docstring_slotted():
    A = namedtuple('A', ['config'])
    B = namedtuple('B', ['sphinx_autodoc_alias'])

    lines = []
    process_docstring(A(config=B(sphinx_autodoc_alias={})), 'class', 'SlotWrapper', Slotted, None, lines)
    assert not lines


@pytest.mark.parametrize('annotation, expected_result, alias', [
    (ExampleA, ':class:`~K.ExampleA`', {(__name__, 'ExampleA'): ('K', 'ExampleA')}),
    (Union[ExampleA, ExampleB],
     ':data:`~typing.Union`\\[:class:`~%s.ExampleA`, :class:`~K.Example`\\[\\~T]]' % __name__,
     {(__name__, 'ExampleB'): ('K', 'Example')}),
])
def test_format_annotation_alias(annotation, expected_result, alias):
    result = format_annotation(annotation, alias)
    assert expected_result == result
