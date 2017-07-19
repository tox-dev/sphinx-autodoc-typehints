# coding=utf-8
import unittest

from sphinx_testing import with_app


class TestSphinxTypeHint(unittest.TestCase):
    @with_app(buildername='html', srcdir='tests/docs/annotation/')
    def test_annotation(self, app, status, warning):
        app.builder.build_all()
        html = (app.outdir / 'index.html').read_text()
        html
