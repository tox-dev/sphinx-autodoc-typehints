import os

import pytest
from sphinx.testing.path import path

pytest_plugins = 'sphinx.testing.fixtures'  # pylint: disable=invalid-name


@pytest.fixture(scope='session')
def rootdir():
    return path(os.path.dirname(__file__) or '.').abspath() / 'roots'
