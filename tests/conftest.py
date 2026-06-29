from __future__ import annotations

import re
import shutil
import sys
from contextlib import suppress
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING
from unittest.mock import create_autospec, patch

import pytest
from sphinx.application import Sphinx
from sphinx.config import Config
from sphobjinv import Inventory

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from sphinx.testing.util import SphinxTestApp

pytest_plugins = "sphinx.testing.fixtures"
collect_ignore = ["roots"]

_SPHINX_EMPHASIS_RE = re.compile(
    r"""
    (?<!\*\*)   # not preceded by ** (bold markup)
    (?<!\*)     # not preceded by * (avoids partial match inside **)
    \*          # opening *
    ([^*\s]     # first char: not * or whitespace
    [^*]*?)     # rest: non-greedy, no * chars
    \*          # closing *
    (?!\*)      # not followed by *
    """,
    re.VERBOSE,
)


def normalize_sphinx_text(text: str) -> str:
    text = text.replace("\u2013", "--")
    return _SPHINX_EMPHASIS_RE.sub(r'"\1"', text)


def make_sig_app(**overrides: object) -> Sphinx:
    defaults: dict[str, object] = {
        "typehints_fully_qualified": False,
        "simplify_optional_unions": False,
        "typehints_formatter": None,
        "typehints_use_signature": False,
        "typehints_use_signature_return": False,
        "autodoc_type_aliases": {},
    }
    defaults.update(overrides)
    config = create_autospec(Config, **defaults)  # ty: ignore[invalid-argument-type]
    return create_autospec(Sphinx, config=config)


def make_docstring_app(**overrides: object) -> Sphinx:
    defaults: dict[str, object] = {
        "autodoc_type_aliases": {},
        "autodoc_mock_imports": [],
        "typehints_fully_qualified": False,
        "simplify_optional_unions": False,
        "typehints_formatter": None,
        "typehints_document_rtype": True,
        "typehints_document_rtype_none": True,
        "typehints_use_rtype": True,
        "typehints_defaults": None,
        "always_document_param_types": False,
        "python_display_short_literal_types": False,
        "typehints_document_overloads": True,
    }
    defaults.update(overrides)
    config = create_autospec(Config, **defaults)  # ty: ignore[invalid-argument-type]
    config.__getitem__.side_effect = lambda key: getattr(config, key)
    app = create_autospec(Sphinx, config=config)
    app.env = None
    return app


@pytest.fixture(autouse=True, scope="session")
def _test_python_path() -> Iterator[None]:
    test_path = str(Path(__file__).parent)
    sys.path.insert(0, test_path)
    yield
    sys.path.remove(test_path)


@pytest.fixture(scope="session")
def wide_text_output() -> Iterator[None]:
    with patch("sphinx.writers.text.MAXWIDTH", 2000):
        yield


@pytest.fixture(scope="session")
def inv(pytestconfig: pytest.Config) -> Inventory:
    cache_path = f"python{sys.version_info.major}.{sys.version_info.minor}/objects.inv"
    assert pytestconfig.cache is not None
    if (
        inv_dict := pytestconfig.cache.get(cache_path, None)
    ) is None:  # pragma: no cover -- network fetch, CI has cache
        url = f"https://docs.python.org/{sys.version_info.major}.{sys.version_info.minor}/objects.inv"
        inv_dict = Inventory(url=url).json_dict()  # ty: ignore[unknown-argument]
        pytestconfig.cache.set(cache_path, inv_dict)
    return Inventory(inv_dict)  # ty: ignore[too-many-positional-arguments]


@pytest.fixture(autouse=True)
def _remove_sphinx_projects(request: pytest.FixtureRequest, sphinx_test_tempdir: Path) -> None:
    if not request.node.get_closest_marker("sphinx"):
        return
    for entry in sphinx_test_tempdir.iterdir():
        with suppress(PermissionError):
            if entry.is_dir() and Path(entry, "_build").exists():
                shutil.rmtree(str(entry))


@pytest.fixture
def rootdir() -> Path:
    return Path(str(Path(__file__).parent) or ".").absolute() / "roots"


@pytest.fixture
def write_rst(app: SphinxTestApp) -> Callable[[str], None]:
    def _write(content: str) -> None:
        for rst_file in Path(app.srcdir).glob("*.rst"):
            rst_file.unlink()
        (Path(app.srcdir) / "index.rst").write_text(dedent(content))

    return _write


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool | None:  # noqa: ARG001
    version_re = re.compile(r"_py(\d)(\d)\.py$")
    if match := version_re.search(collection_path.name):
        version = tuple(int(x) for x in match.groups())
        if sys.version_info < version:  # ty: ignore[unsupported-operator]
            return True
    return None
