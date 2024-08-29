from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from sphinx.testing.path import path
from sphobjinv import Inventory

if TYPE_CHECKING:
    from _pytest.config import Config

pytest_plugins = "sphinx.testing.fixtures"
collect_ignore = ["roots"]


@pytest.fixture(scope="session")
def inv(pytestconfig: Config) -> Inventory:
    cache_path = f"python{sys.version_info.major}.{sys.version_info.minor}/objects.inv"
    assert pytestconfig.cache is not None
    inv_dict = pytestconfig.cache.get(cache_path, None)
    if inv_dict is not None:
        return Inventory(inv_dict)

    url = f"https://docs.python.org/{sys.version_info.major}.{sys.version_info.minor}/objects.inv"
    inv = Inventory(url=url)
    pytestconfig.cache.set(cache_path, inv.json_dict())
    return inv


@pytest.fixture(autouse=True)
def _remove_sphinx_projects(sphinx_test_tempdir: path) -> None:
    # Remove any directory which appears to be a Sphinx project from
    # the temporary directory area.
    # See https://github.com/sphinx-doc/sphinx/issues/4040
    roots_path = Path(sphinx_test_tempdir)
    for entry in roots_path.iterdir():
        try:
            if entry.is_dir() and Path(entry, "_build").exists():
                shutil.rmtree(str(entry))
        except PermissionError:  # noqa: PERF203
            pass


@pytest.fixture
def rootdir() -> path:
    return path(str(Path(__file__).parent) or ".").abspath() / "roots"


def pytest_ignore_collect(path: Any, config: Config) -> bool | None:  # noqa: ARG001
    version_re = re.compile(r"_py(\d)(\d)\.py$")
    match = version_re.search(path.basename)
    if match:
        version = tuple(int(x) for x in match.groups())
        if sys.version_info < version:
            return True
    return None
