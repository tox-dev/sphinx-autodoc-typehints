from __future__ import annotations

import re
import sys
from functools import cmp_to_key
from pathlib import Path
from textwrap import dedent, indent
from typing import TYPE_CHECKING, Any
from unittest.mock import create_autospec, patch

import pytest
import typing_extensions
from conftest import normalize_sphinx_text
from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.ext.autodoc import Options

from sphinx_autodoc_typehints import process_docstring, process_signature

if TYPE_CHECKING:
    from io import StringIO
    from types import FunctionType

    from sphinx.testing.util import SphinxTestApp


class Slotted:
    __slots__ = ()


class HintedMethods:
    @classmethod
    def from_magic(cls) -> typing_extensions.Self: ...

    def method(self) -> typing_extensions.Self: ...


def test_process_docstring_slot_wrapper() -> None:
    lines: list[str] = []
    config = create_autospec(
        Config,
        typehints_fully_qualified=False,
        simplify_optional_unions=False,
        typehints_formatter=None,
        autodoc_mock_imports=[],
    )
    app: Sphinx = create_autospec(Sphinx, config=config)
    process_docstring(app, "class", "SlotWrapper", Slotted, None, lines)
    assert not lines


def test_process_docstring_wrapper_loop() -> None:
    """Regression test for #405: inspect.unwrap raises ValueError on wrapper loops."""

    def func(x: int) -> str: ...

    func.__wrapped__ = func  # type: ignore[attr-defined]  # circular wrapper loop

    lines: list[str] = []
    config = create_autospec(
        Config,
        typehints_fully_qualified=False,
        simplify_optional_unions=False,
        typehints_formatter=None,
        autodoc_mock_imports=[],
    )
    app: Sphinx = create_autospec(Sphinx, config=config)
    process_docstring(app, "function", "func", func, None, lines)


def test_process_signature_wrapper_loop() -> None:
    """Regression test for #405: inspect.unwrap raises ValueError on wrapper loops."""

    def func(x: int) -> str: ...

    func.__wrapped__ = func  # type: ignore[attr-defined]  # circular wrapper loop

    config = create_autospec(
        Config,
        typehints_fully_qualified=False,
        simplify_optional_unions=False,
        typehints_formatter=None,
        typehints_use_signature=False,
        typehints_use_signature_return=False,
        autodoc_type_aliases={},
    )
    app: Sphinx = create_autospec(Sphinx, config=config)
    result = process_signature(
        app,
        "function",
        "func",
        func,
        Options(),
        "",
        "",
    )
    assert result is None


def set_python_path() -> None:
    test_path = Path(__file__).parent
    if str(test_path) not in sys.path:
        sys.path.insert(0, str(test_path))


@pytest.mark.parametrize("always_document_param_types", [True, False], ids=["doc_param_type", "no_doc_param_type"])
@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_always_document_param_types(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
    always_document_param_types: bool,
) -> None:
    set_python_path()

    app.config.always_document_param_types = always_document_param_types  # create flag
    app.config.autodoc_mock_imports = ["mailbox"]  # create flag

    for f in Path(app.srcdir).glob("*.rst"):
        f.unlink()
    (Path(app.srcdir) / "index.rst").write_text(
        dedent(
            """
            .. autofunction:: dummy_module.undocumented_function

            .. autoclass:: dummy_module.DataClass
                :undoc-members:
                :special-members: __init__
            """,
        ),
    )

    app.build()

    assert "build succeeded" in status.getvalue()
    assert not warning.getvalue().strip()

    format_args = {}
    for indentation_level in range(2):
        key = f"undoc_params_{indentation_level}"
        if always_document_param_types:
            format_args[key] = indent('\n\n   Parameters:\n      **x** ("int")', "   " * indentation_level)
        else:
            format_args[key] = ""

    contents = normalize_sphinx_text((Path(app.srcdir) / "_build/text/index.txt").read_text())
    expected_contents = """\
    dummy_module.undocumented_function(x)

       Hi{undoc_params_0}

       Return type:
          "str"

    class dummy_module.DataClass(x)

       Class docstring.{undoc_params_0}

       __init__(x){undoc_params_1}
    """
    expected_contents = normalize_sphinx_text(dedent(expected_contents).format(**format_args))
    assert contents == expected_contents


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_always_document_param_types_with_defaults_braces_after(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,  # noqa: ARG001
) -> None:
    """Regression test for #575: IndexError when combining always_document_param_types with braces-after."""
    set_python_path()

    app.config.always_document_param_types = True
    app.config.typehints_defaults = "braces-after"

    for rst_file in Path(app.srcdir).glob("*.rst"):
        rst_file.unlink()
    index_content = """\
        .. autofunction:: dummy_module.undocumented_function_with_defaults
    """
    (Path(app.srcdir) / "index.rst").write_text(dedent(index_content))

    app.build()

    assert "build succeeded" in status.getvalue()


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_namedtuple_new_no_warning(
    app: SphinxTestApp,
    status: StringIO,
    warning: StringIO,
) -> None:
    """Regression test for #601: NamedTuple __new__ causes 'NoneType' attribute error."""
    set_python_path()

    for rst_file in Path(app.srcdir).glob("*.rst"):
        rst_file.unlink()
    index_content = """\
        .. autoclass:: dummy_module.MyNamedTuple
            :special-members: __new__
    """
    (Path(app.srcdir) / "index.rst").write_text(dedent(index_content))

    app.build()

    assert "build succeeded" in status.getvalue()
    assert "NoneType" not in warning.getvalue()


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_future_annotations(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()

    app.config.master_doc = "future_annotations"  # create flag
    app.build()

    assert "build succeeded" in status.getvalue()

    contents = normalize_sphinx_text((Path(app.srcdir) / "_build/text/future_annotations.txt").read_text())
    expected_contents = """\
    Dummy Module
    ************

    dummy_module_future_annotations.function_with_py310_annotations(self, x, y, z=None)

       Method docstring.

       Parameters:
          * **x** ("bool" | "None") -- foo

          * **y** ("int" | "str" | "float") -- bar

          * **z** ("str" | "None") -- baz

       Return type:
          "str"
    """
    expected_contents = normalize_sphinx_text(dedent(expected_contents))
    assert contents == expected_contents


@pytest.mark.sphinx("pseudoxml", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_default_role(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()

    app.config.master_doc = "simple_default_role"  # create flag
    app.config.default_role = "literal"
    app.build()

    assert "build succeeded" in status.getvalue()

    contents_lines = (
        (Path(app.srcdir) / "_build/pseudoxml/simple_default_role.pseudoxml").read_text(encoding="utf-8").splitlines()
    )
    list_item_idxs = [i for i, line in enumerate(contents_lines) if line.strip() == "<list_item>"]
    foo_param = dedent("\n".join(contents_lines[list_item_idxs[0] : list_item_idxs[1]]))
    expected_foo_param = """\
    <list_item>
        <paragraph>
            <literal_strong>
                x
             (
            <inline classes="sphinx_autodoc_typehints-type">
                <literal classes="xref py py-class">
                    bool
            )
             \N{EN DASH}\N{SPACE}
            <literal>
                foo
    """.rstrip()
    expected_foo_param = dedent(expected_foo_param)
    assert foo_param == expected_foo_param


@pytest.mark.parametrize(
    ("defaults_config_val", "expected"),
    [
        (None, '("int") -- bar'),
        ("comma", '("int", default: "1") -- bar'),
        ("braces", '("int" (default: "1")) -- bar'),
        ("braces-after", '("int") -- bar (default: "1")'),
        ("comma-after", Exception("needs to be one of")),
    ],
)
@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_defaults(
    app: SphinxTestApp,
    status: StringIO,
    defaults_config_val: str,
    expected: str | Exception,
) -> None:
    set_python_path()

    app.config.master_doc = "simple"  # create flag
    app.config.typehints_defaults = defaults_config_val  # create flag
    if isinstance(expected, Exception):
        with pytest.raises(Exception, match=re.escape(str(expected))):
            app.build()
        return
    app.build()
    assert "build succeeded" in status.getvalue()

    contents = normalize_sphinx_text((Path(app.srcdir) / "_build/text/simple.txt").read_text())
    expected_contents = f"""\
    Simple Module
    *************

    dummy_module_simple.function(x, y=1)

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** {expected}

       Return type:
          "str"
    """
    assert contents == normalize_sphinx_text(dedent(expected_contents))


@pytest.mark.parametrize(
    ("formatter_config_val", "expected"),
    [
        (None, ['("bool") -- foo', '("int") -- bar', '"str"']),
        (lambda ann, conf: "Test", ["(Test) -- foo", "(Test) -- bar", "Test"]),  # noqa: ARG005
        ("some string", Exception("needs to be callable or `None`")),
    ],
)
@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_formatter(
    app: SphinxTestApp,
    status: StringIO,
    formatter_config_val: str,
    expected: tuple[str, ...] | Exception,
) -> None:
    set_python_path()

    app.config.master_doc = "simple"  # create flag
    app.config.typehints_formatter = formatter_config_val  # create flag
    if isinstance(expected, Exception):
        with pytest.raises(Exception, match=re.escape(str(expected))):
            app.build()
        return
    app.build()
    assert "build succeeded" in status.getvalue()

    contents = normalize_sphinx_text((Path(app.srcdir) / "_build/text/simple.txt").read_text())
    expected_contents = f"""\
    Simple Module
    *************

    dummy_module_simple.function(x, y=1)

       Function docstring.

       Parameters:
          * **x** {expected[0]}

          * **y** {expected[1]}

       Return type:
          {expected[2]}
    """
    assert contents == normalize_sphinx_text(dedent(expected_contents))


@pytest.mark.parametrize("obj", [cmp_to_key, 1])
def test_default_no_signature(obj: Any) -> None:
    config = create_autospec(
        Config,
        typehints_fully_qualified=False,
        simplify_optional_unions=False,
        typehints_formatter=None,
        autodoc_mock_imports=[],
    )
    app: Sphinx = create_autospec(Sphinx, config=config)
    lines: list[str] = []
    process_docstring(app, "what", "name", obj, None, lines)
    assert lines == []


@pytest.mark.parametrize("method", [HintedMethods.from_magic, HintedMethods().method])
def test_bound_class_method(method: FunctionType) -> None:
    config = create_autospec(
        Config,
        typehints_fully_qualified=False,
        simplify_optional_unions=False,
        typehints_document_rtype=False,
        always_document_param_types=True,
        typehints_defaults=True,
        typehints_formatter=None,
        autodoc_mock_imports=[],
    )
    app: Sphinx = create_autospec(Sphinx, config=config)
    process_docstring(app, "class", method.__qualname__, method, None, [])


@pytest.mark.sphinx("text", testroot="resolve-typing-guard")
def test_resolve_typing_guard_imports(app: SphinxTestApp, status: StringIO, warning: StringIO) -> None:
    set_python_path()
    app.config.autodoc_mock_imports = ["viktor"]  # create flag
    app.build()
    out = status.getvalue()
    assert "build succeeded" in out
    assert "Failed guarded type import" not in warning.getvalue()


@pytest.mark.sphinx("text", testroot="resolve-typing-guard-tmp")
def test_resolve_typing_guard_attrs_imports(app: SphinxTestApp, status: StringIO, warning: StringIO) -> None:
    set_python_path()
    app.build()
    assert "build succeeded" in status.getvalue()
    assert not warning.getvalue()


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_formatter_no_use_rtype(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()
    app.config.master_doc = "simple_no_use_rtype"  # create flag
    app.config.typehints_use_rtype = False
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = Path(app.srcdir) / "_build" / "text" / "simple_no_use_rtype.txt"
    text_contents = normalize_sphinx_text(text_path.read_text())
    expected_contents = """\
    Simple Module
    *************

    dummy_module_simple_no_use_rtype.function_no_returns(x, y=1)

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** ("int") -- bar

       Return type:
          "str"

    dummy_module_simple_no_use_rtype.function_returns_with_type(x, y=1)

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** ("int") -- bar

       Returns:
          *CustomType* -- A string

    dummy_module_simple_no_use_rtype.function_returns_with_compound_type(x, y=1)

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** ("int") -- bar

       Returns:
          Union[str, int] -- A string or int

    dummy_module_simple_no_use_rtype.function_returns_without_type(x, y=1)

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** ("int") -- bar

       Returns:
          "str" -- A string
    """
    assert text_contents == normalize_sphinx_text(dedent(expected_contents))


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_with_use_signature(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()
    app.config.master_doc = "simple"  # create flag
    app.config.typehints_use_signature = True
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = Path(app.srcdir) / "_build" / "text" / "simple.txt"
    text_contents = normalize_sphinx_text(text_path.read_text())
    expected_contents = """\
    Simple Module
    *************

    dummy_module_simple.function(x: bool, y: int = 1)

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** ("int") -- bar

       Return type:
          "str"
    """
    assert text_contents == normalize_sphinx_text(dedent(expected_contents))


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_with_use_signature_return(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()
    app.config.master_doc = "simple"  # create flag
    app.config.typehints_use_signature_return = True
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = Path(app.srcdir) / "_build" / "text" / "simple.txt"
    text_contents = normalize_sphinx_text(text_path.read_text())
    expected_contents = """\
    Simple Module
    *************

    dummy_module_simple.function(x, y=1) -> str

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** ("int") -- bar

       Return type:
          "str"
    """
    assert text_contents == normalize_sphinx_text(dedent(expected_contents))


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_sphinx_output_with_use_signature_and_return(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()
    app.config.master_doc = "simple"  # create flag
    app.config.typehints_use_signature = True
    app.config.typehints_use_signature_return = True
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = Path(app.srcdir) / "_build" / "text" / "simple.txt"
    text_contents = normalize_sphinx_text(text_path.read_text())
    expected_contents = """\
    Simple Module
    *************

    dummy_module_simple.function(x: bool, y: int = 1) -> str

       Function docstring.

       Parameters:
          * **x** ("bool") -- foo

          * **y** ("int") -- bar

       Return type:
          "str"
    """
    assert text_contents == normalize_sphinx_text(dedent(expected_contents))


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_default_annotation_without_typehints(app: SphinxTestApp, status: StringIO) -> None:
    set_python_path()
    app.config.master_doc = "without_complete_typehints"  # create flag
    app.config.typehints_defaults = "comma"
    app.build()
    assert "build succeeded" in status.getvalue()
    text_path = Path(app.srcdir) / "_build" / "text" / "without_complete_typehints.txt"
    text_contents = normalize_sphinx_text(text_path.read_text())
    expected_contents = """\
    Simple Module
    *************

    dummy_module_without_complete_typehints.function_with_some_defaults_and_without_typehints(x, y=None)

       Function docstring.

       Parameters:
          * **x** -- foo

          * **y** (default: "None") -- bar

    dummy_module_without_complete_typehints.function_with_some_defaults_and_some_typehints(x, y=None)

       Function docstring.

       Parameters:
          * **x** ("int") -- foo

          * **y** (default: "None") -- bar

    dummy_module_without_complete_typehints.function_with_some_defaults_and_more_typehints(x, y=None)

       Function docstring.

       Parameters:
          * **x** ("int") -- foo

          * **y** (default: "None") -- bar

       Return type:
          "str"

    dummy_module_without_complete_typehints.function_with_defaults_and_some_typehints(x=0, y=None)

       Function docstring.

       Parameters:
          * **x** ("int", default: "0") -- foo

          * **y** (default: "None") -- bar

       Return type:
          "str"

    dummy_module_without_complete_typehints.function_with_defaults_and_type_information_in_docstring(x, y=0)

       Function docstring.

       Parameters:
          * **x** ("int") -- foo

          * **y** (int, default: "0") -- bar

       Return type:
          "str"
    """
    assert text_contents == normalize_sphinx_text(dedent(expected_contents))


@pytest.mark.sphinx("text", testroot="dummy")
@patch("sphinx.writers.text.MAXWIDTH", 2000)
def test_wrong_module_path(app: SphinxTestApp, status: StringIO, warning: StringIO) -> None:
    set_python_path()

    app.config.master_doc = "wrong_module_path"  # create flag
    app.config.default_role = "literal"
    app.config.nitpicky = True
    app.config.nitpick_ignore = {("py:data", "typing.Optional")}

    def fixup_module_name(mod: str) -> str:
        if not mod.startswith("wrong_module_path"):
            return mod
        return "export_module" + mod.removeprefix("wrong_module_path")

    app.config.suppress_warnings = ["config.cache"]
    app.config.typehints_fixup_module_name = fixup_module_name
    app.build()

    assert "build succeeded" in status.getvalue()
    assert not warning.getvalue().strip()
