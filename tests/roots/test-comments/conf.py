# coding=utf-8
""" Configuration for Sphinx."""
import os
import sys

company = u'Bloomberg LP'
name = u'typehint'
extensions = ['sphinx.ext.autodoc',
              'sphinx_autodoc_typehints']
source_suffix = '.rst'
master_doc = 'index'
project = u'typehint'
sys.path.append(os.path.dirname(__file__))
