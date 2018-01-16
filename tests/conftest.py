import os
import pytest
import pathlib
import shutil
from sphinx.testing.path import path


pytest_plugins = 'sphinx.testing.fixtures'

collect_ignore = ['roots']


@pytest.fixture(scope='session')
def remove_sphinx_projects(sphinx_test_tempdir):
    # Remove any directory which appears to be a Sphinx project from
    # the temporary directory area.
    # See https://github.com/sphinx-doc/sphinx/issues/4040
    roots_path = pathlib.Path(sphinx_test_tempdir)
    for entry in roots_path.iterdir():
        if entry.is_dir() and pathlib.Path(entry, '_build').exists():
            shutil.rmtree(str(entry))
    yield


@pytest.fixture()
def rootdir(remove_sphinx_projects):
    roots = path(os.path.dirname(__file__) or '.').abspath() / 'roots'
    yield roots
