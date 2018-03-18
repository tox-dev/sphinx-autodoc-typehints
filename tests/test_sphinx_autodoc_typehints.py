import pathlib
import pytest
import sys
import textwrap
from typing import (
    Any, AnyStr, Callable, Dict, Generic, Mapping, Optional, Pattern, Tuple, TypeVar, Union, Type)

from sphinx_autodoc_typehints import format_annotation, process_docstring

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


@pytest.mark.sphinx('text', testroot='dummy')
def test_sphinx_output(app, status, warning):
    test_path = pathlib.Path(__file__).parent

    # Add test directory to sys.path to allow imports of dummy module.
    if str(test_path) not in sys.path:
        sys.path.insert(0, str(test_path))

    app.build()

    assert 'build succeeded' in status.getvalue()  # Build succeeded
    assert not warning.getvalue().strip()  # No warnings

    text_path = pathlib.Path(app.srcdir) / '_build' / 'text' / 'index.txt'
    with text_path.open('r') as f:
        text_contents = f.read().replace('–', '--')
        assert text_contents == textwrap.dedent('''\
        Dummy Module
        ************

        class dummy_module.Class(x, y, z=None)

           Initializer docstring.

           Parameters:
              * **x** ("bool") – foo

              * **y** ("int") – bar

              * **z** ("Optional"["str"]) – baz

           classmethod a_classmethod(x, y, z=None)

              Classmethod docstring.

              Parameters:
                 * **x** ("bool") – foo

                 * **y** ("int") – bar

                 * **z** ("Optional"["str"]) – baz

              Return type:
                 "str"

           a_method(x, y, z=None)

              Method docstring.

              Parameters:
                 * **x** ("bool") – foo

                 * **y** ("int") – bar

                 * **z** ("Optional"["str"]) – baz

              Return type:
                 "str"

           a_property

              Property docstring

              Return type:
                 "str"

           static a_staticmethod(x, y, z=None)

              Staticmethod docstring.

              Parameters:
                 * **x** ("bool") – foo

                 * **y** ("int") – bar

                 * **z** ("Optional"["str"]) – baz

              Return type:
                 "str"

        exception dummy_module.DummyException(message)

           Exception docstring

           Parameters:
              **message** ("str") – blah

        dummy_module.function(x, y, z=None)

           Function docstring.

           Parameters:
              * **x** ("bool") – foo

              * **y** ("int") – bar

              * **z** ("Optional"["str"]) – baz

           Returns:
              something

           Return type:
              bytes
        ''').replace('–', '--')
