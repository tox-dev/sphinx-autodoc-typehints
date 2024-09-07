# sphinx-autodoc-typehints

[![PyPI](https://img.shields.io/pypi/v/sphinx-autodoc-typehints?style=flat-square)](https://pypi.org/project/sphinx-autodoc-typehints/)
[![Supported Python
versions](https://img.shields.io/pypi/pyversions/sphinx-autodoc-typehints.svg)](https://pypi.org/project/sphinx-autodoc-typehints/)
[![Downloads](https://pepy.tech/badge/sphinx-autodoc-typehints/month)](https://pepy.tech/project/sphinx-autodoc-typehints)
[![check](https://github.com/tox-dev/sphinx-autodoc-typehints/actions/workflows/check.yml/badge.svg)](https://github.com/tox-dev/sphinx-autodoc-typehints/actions/workflows/check.yml)

This extension allows you to use Python 3 annotations for documenting acceptable argument types and return value types
of functions. See an example of the Sphinx render at the
[pyproject-api docs](https://pyproject-api.readthedocs.io/en/latest/).

This allows you to use type hints in a very natural fashion, allowing you to migrate from this:

```python
def format_unit(value, unit):
    """
    Formats the given value as a human readable string using the given units.

    :param float|int value: a numeric value
    :param str unit: the unit for the value (kg, m, etc.)
    :rtype: str
    """
    return f"{value} {unit}"
```

to this:

```python
from typing import Union


def format_unit(value: Union[float, int], unit: str) -> str:
    """
    Formats the given value as a human readable string using the given units.

    :param value: a numeric value
    :param unit: the unit for the value (kg, m, etc.)
    """
    return f"{value} {unit}"
```

## Installation and setup

First, use pip to download and install the extension:

```bash
pip install sphinx-autodoc-typehints
```

Then, add the extension to your `conf.py`:

```python
extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
```

## Options

The following configuration options are accepted:

- `typehints_fully_qualified` (default: `False`): if `True`, class names are always fully qualified (e.g.
  `module.for.Class`). If `False`, just the class name displays (e.g. `Class`)
- `always_document_param_types` (default: `False`): If `False`, do not add type info for undocumented parameters. If
  `True`, add stub documentation for undocumented parameters to be able to add type info.
- `always_use_bars_union ` (default: `False`): If `True`, display Union's using the | operator described in PEP 604.
  (e.g `X` | `Y` or `int` | `None`). If `False`, Unions will display with the typing in brackets. (e.g. `Union[X, Y]`
  or `Optional[int]`)
- `typehints_document_rtype` (default: `True`): If `False`, never add an `:rtype:` directive. If `True`, add the
  `:rtype:` directive if no existing `:rtype:` is found.
- `typehints_use_rtype` (default: `True`): Controls behavior when `typehints_document_rtype` is set to `True`. If
  `True`, document return type in the `:rtype:` directive. If `False`, document return type as part of the `:return:`
  directive, if present, otherwise fall back to using `:rtype:`. Use in conjunction with
  [napoleon_use_rtype](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html#confval-napoleon_use_rtype)
  to avoid generation of duplicate or redundant return type information.
- `typehints_defaults` (default: `None`): If `None`, defaults are not added. Otherwise, adds a default annotation:

  - `'comma'` adds it after the type, changing Sphinx’ default look to “**param** (_int_, default: `1`) -- text”.
  - `'braces'` adds `(default: ...)` after the type (useful for numpydoc like styles).
  - `'braces-after'` adds `(default: ...)` at the end of the parameter documentation text instead.

- `simplify_optional_unions` (default: `True`): If `True`, optional parameters of type \"Union\[\...\]\" are simplified
  as being of type Union\[\..., None\] in the resulting documentation (e.g. Optional\[Union\[A, B\]\] -\> Union\[A, B,
  None\]). If `False`, the \"Optional\"-type is kept. Note: If `False`, **any** Union containing `None` will be
  displayed as Optional! Note: If an optional parameter has only a single type (e.g Optional\[A\] or Union\[A, None\]),
  it will **always** be displayed as Optional!
- `typehints_formatter` (default: `None`): If set to a function, this function will be called with `annotation` as first
  argument and `sphinx.config.Config` argument second. The function is expected to return a string with reStructuredText
  code or `None` to fall back to the default formatter.
- `typehints_use_signature` (default: `False`): If `True`, typehints for parameters in the signature are shown.
- `typehints_use_signature_return` (default: `False`): If `True`, return annotations in the signature are shown.

## How it works

The extension listens to the `autodoc-process-signature` and `autodoc-process-docstring` Sphinx events. In the former,
it strips the annotations from the function signature. In the latter, it injects the appropriate `:type argname:` and
`:rtype:` directives into the docstring.

Only arguments that have an existing `:param:` directive in the docstring get their respective `:type:` directives
added. The `:rtype:` directive is added if and only if no existing `:rtype:` is found.

## Compatibility with sphinx.ext.napoleon

To use [sphinx.ext.napoleon](http://www.sphinx-doc.org/en/stable/ext/napoleon.html) with sphinx-autodoc-typehints, make
sure you load [sphinx.ext.napoleon](http://www.sphinx-doc.org/en/stable/ext/napoleon.html) first, **before**
sphinx-autodoc-typehints. See [Issue 15](https://github.com/tox-dev/sphinx-autodoc-typehints/issues/15) on the issue
tracker for more information.

## Dealing with circular imports

Sometimes functions or classes from two different modules need to reference each other in their type annotations. This
creates a circular import problem. The solution to this is the following:

1. Import only the module, not the classes/functions from it
2. Use forward references in the type annotations (e.g. `def methodname(self, param1: 'othermodule.OtherClass'):`)

On Python 3.7, you can even use `from __future__ import annotations` and remove the quotes.
