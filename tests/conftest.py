import os
import sys
import pathlib
import shutil

import pytest
from sphinx.testing.path import path
from sphobjinv import Inventory

pytest_plugins = 'sphinx.testing.fixtures'
collect_ignore = ['roots']


@pytest.fixture(scope='session')
def inv(pytestconfig):
    inv_dict = pytestconfig.cache.get('python/objects.inv', None)
    if inv_dict is not None:
        return Inventory(inv_dict)
    print("Downloading objects.inv")
    url = 'https://docs.python.org/{v.major}.{v.minor}/objects.inv'.format(v=sys.version_info)
    inv = Inventory(url=url)
    pytestconfig.cache.set('python/objects.inv', inv.json_dict())
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
