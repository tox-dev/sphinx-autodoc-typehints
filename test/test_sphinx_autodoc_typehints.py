import pathlib
import pytest
import sys
import textwrap
from sphinx_testing import with_app
from typing import (
    Any, AnyStr, Callable, Dict, Generic, Mapping, Optional, Pattern, Tuple, TypeVar, Union)

from sphinx_autodoc_typehints import format_annotation, process_docstring


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


def test_sphinx_output():
    test_path = pathlib.Path(__file__).parent

    # Add test directory to sys.path to allow imports of dummy module.
    if str(test_path) not in sys.path:
        sys.path.insert(0, str(test_path))

    result = {}

    @with_app(
        buildername='text',
        srcdir=test_path,
        copy_srcdir_to_tmpdir=False,
        )
    def run_sphinx(app, status, warning):
        app.build()
        # The sphinx-testing with_app decorator does not return decorated
        # function's return value, so we stash the results into a dict
        result['app'] = app
        result['status'] = status.getvalue()
        result['warning'] = warning.getvalue()
        builddir = pathlib.Path(result['app'].builddir)
        text_path = builddir / 'text' / 'index.txt'
        with text_path.open('r') as f:
            result['text'] = f.read()

    run_sphinx()

    assert not result['warning'].strip()  # No warnings
    assert 'build succeeded' in result['status']
    assert result['text'] == textwrap.dedent('''\
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

        dummy_module.function(x, y, z=None)

           Function docstring.

           Parameters:
              * **x** ("bool") – foo

              * **y** ("int") – bar

              * **z** ("Optional"["str"]) – baz

           Return type:
              "str"
        ''')
