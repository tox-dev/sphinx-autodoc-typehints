import os
import pathlib
import shutil

import pytest
from sphinx.testing.path import path
from sphobjinv import Inventory

pytest_plugins = 'sphinx.testing.fixtures'
collect_ignore = ['roots']
inv_cache = {}


@pytest.fixture(params=["3.5", "3.6", "3.7"])
def inv(request):
    pyver = request.param
    inv = inv_cache.get(pyver)
    if not inv:
        inv = inv_cache[pyver] = Inventory(url=f"https://docs.python.org/{pyver}/objects.inv")
    return inv


@pytest.fixture(autouse=True)
def remove_sphinx_projects(sphinx_test_tempdir):
    # Remove any directory which appears to be a Sphinx project from
    # the temporary directory area.
    # See https://github.com/sphinx-doc/sphinx/issues/4040
    roots_path = pathlib.Path(sphinx_test_tempdir)
    for entry in roots_path.iterdir():
        try:
            if entry.is_dir() and pathlib.Path(entry, '_build').exists():
                shutil.rmtree(str(entry))
        except PermissionError:
            pass


@pytest.fixture
def rootdir():
    return path(os.path.dirname(__file__) or '.').abspath() / 'roots'
