import os
import pytest
from sphinx.testing.path import path


pytest_plugins = 'sphinx.testing.fixtures'

collect_ignore = ['roots']


@pytest.fixture()
def rootdir():
    roots = path(os.path.dirname(__file__) or '.').abspath() / 'roots'
    yield roots
