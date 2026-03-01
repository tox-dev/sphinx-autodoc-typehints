# sphinx-autodoc-typehints

[![PyPI](https://img.shields.io/pypi/v/sphinx-autodoc-typehints?style=flat-square)](https://pypi.org/project/sphinx-autodoc-typehints/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/sphinx-autodoc-typehints.svg)](https://pypi.org/project/sphinx-autodoc-typehints/)
[![Downloads](https://pepy.tech/badge/sphinx-autodoc-typehints/month)](https://pepy.tech/project/sphinx-autodoc-typehints)
[![check](https://github.com/tox-dev/sphinx-autodoc-typehints/actions/workflows/check.yaml/badge.svg)](https://github.com/tox-dev/sphinx-autodoc-typehints/actions/workflows/check.yaml)

This [Sphinx](https://www.sphinx-doc.org/) extension reads your Python
[type hints](https://docs.python.org/3/library/typing.html) and automatically adds type information to your generated
documentation -- so you write types once in code and they appear in your docs without duplication.

**Features:**

- Adds parameter and return types from annotations into docstrings
- Resolves types from [`TYPE_CHECKING`](https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING) blocks and
  [`.pyi` stub files](https://typing.python.org/en/latest/spec/distributing.html#stub-files)
- Renders [`@overload`](https://docs.python.org/3/library/typing.html#typing.overload) signatures in docstrings
- Extracts types from [attrs](https://www.attrs.org/) and
  [dataclass](https://docs.python.org/3/library/dataclasses.html) classes
- Shows default parameter values alongside types
- Controls union display style (`Union[X, Y]` vs `X | Y`)
- Supports custom type formatters and module name rewriting
- Extracts descriptions from [`Annotated[T, Doc(...)]`](https://typing-extensions.readthedocs.io/en/latest/#Doc)
  metadata
- Works with [Google and NumPy](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html) docstring styles

Sphinx has a built-in
[`autodoc_typehints`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_typehints)
setting (since v2.1) that can move type hints between signatures and descriptions. This extension replaces that with the
features above. See [Avoid duplicate types with built-in Sphinx](#avoid-duplicate-types-with-built-in-sphinx).

<!-- mdformat-toc start --slug=github --no-anchors --maxlevel=6 --minlevel=2 -->

- [Installation](#installation)
- [Quick start](#quick-start)
- [How-to guides](#how-to-guides)
  - [Avoid duplicate types with built-in Sphinx](#avoid-duplicate-types-with-built-in-sphinx)
  - [Use with Google or NumPy docstring style](#use-with-google-or-numpy-docstring-style)
  - [Control return type display](#control-return-type-display)
  - [Change how union types look](#change-how-union-types-look)
  - [Show default parameter values](#show-default-parameter-values)
  - [Control overload signature display](#control-overload-signature-display)
  - [Keep type hints in function signatures](#keep-type-hints-in-function-signatures)
  - [Handle circular imports](#handle-circular-imports)
  - [Resolve types from `TYPE_CHECKING` blocks](#resolve-types-from-type_checking-blocks)
  - [Show types for `attrs` or `dataclass` fields](#show-types-for-attrs-or-dataclass-fields)
  - [Write a custom type formatter](#write-a-custom-type-formatter)
  - [Document a `NewType` or `type` alias without expanding it](#document-a-newtype-or-type-alias-without-expanding-it)
  - [Add types for C extensions or packages without annotations](#add-types-for-c-extensions-or-packages-without-annotations)
  - [Fix cross-reference links for renamed modules](#fix-cross-reference-links-for-renamed-modules)
  - [Suppress warnings](#suppress-warnings)
- [Reference](#reference)
  - [Configuration options](#configuration-options)
  - [Warning categories](#warning-categories)
- [Explanation](#explanation)
  - [How it works](#how-it-works)
  - [How return type options interact](#how-return-type-options-interact)

<!-- mdformat-toc end -->

## Installation

```bash
pip install sphinx-autodoc-typehints
```

Then add the extension to your [`conf.py`](https://www.sphinx-doc.org/en/master/usage/configuration.html):

```python
extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
```

## Quick start

Instead of writing types in your docstrings, write them as Python type hints. The extension picks them up and adds them
to your Sphinx output:

```python
# Before: types repeated in docstrings
def format_unit(value, unit):
    """
    Format a value with its unit.

    :param float value: a numeric value
    :param str unit: the unit (kg, m, etc.)
    :rtype: str
    """
    return f"{value} {unit}"


# After: types only in annotations, docs generated automatically
def format_unit(value: float, unit: str) -> str:
    """
    Format a value with its unit.

    :param value: a numeric value
    :param unit: the unit (kg, m, etc.)
    """
    return f"{value} {unit}"
```

The extension adds the type information to your docs during the Sphinx build. See an example at the
[pyproject-api docs](https://pyproject-api.readthedocs.io/latest/api.html).

## How-to guides

### Avoid duplicate types with built-in Sphinx

If types appear twice in your docs, you're likely running both this extension and Sphinx's built-in type hint
processing. Set
[`autodoc_typehints = "none"`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_typehints)
in your `conf.py` to let this extension handle everything:

```python
autodoc_typehints = "none"
```

### Use with Google or NumPy docstring style

If you use [`sphinx.ext.napoleon`](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html) for Google-style
or NumPy-style docstrings, load it **before** this extension:

```python
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]
```

To avoid duplicate return type entries, disable the return type block in both extensions:

```python
napoleon_use_rtype = False  # sphinx.ext.napoleon setting
typehints_use_rtype = False
```

See
[`napoleon_use_rtype`](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html#confval-napoleon_use_rtype)
in the Sphinx docs.

### Control return type display

By default, return types appear as a separate block in your docs. You can change this:

```python
# Don't show return types at all
typehints_document_rtype = False

# Don't show "None" return types, but show all others
typehints_document_rtype_none = False

# Show the return type inline with the return description
# instead of as a separate block
typehints_use_rtype = False
```

### Change how union types look

By default, union types display as `Union[str, int]` and `Optional[str]`. To use the shorter pipe syntax (`str | int`,
`str | None`):

```python
always_use_bars_union = True
```

On Python 3.14+, the [pipe syntax](https://docs.python.org/3/library/stdtypes.html#types-union) is always used
regardless of this setting.

By default, `Optional[Union[A, B]]` is simplified to `Union[A, B, None]`. To keep the `Optional` wrapper:

```python
simplify_optional_unions = False
```

Note: with this set to `False`, any union containing `None` will display as `Optional`.

### Show default parameter values

To include default values in your docs, set `typehints_defaults` to one of three styles:

```python
# "param (int, default: 1) -- description"
typehints_defaults = "comma"

# "param (int) -- description (default: 1)"
typehints_defaults = "braces"

# "param (int) -- description (default: 1)"  (at end of text)
typehints_defaults = "braces-after"
```

### Control overload signature display

When a function has [`@overload`](https://docs.python.org/3/library/typing.html#typing.overload) signatures, they are
rendered automatically in the docstring. To disable this globally:

```python
typehints_document_overloads = False
```

To disable overloads for a single function while keeping them everywhere else, add `:no-overloads:` to the docstring:

```python
@overload
def f(x: int) -> str: ...
@overload
def f(x: str) -> bool: ...
def f(x):
    """:no-overloads:

    f accepts int or str, see docs for details.
    """
```

The `:no-overloads:` directive is stripped from the rendered output.

### Keep type hints in function signatures

By default, type hints are removed from function signatures and shown in the parameter list below. To keep them visible
in the signature line:

```python
typehints_use_signature = True  # show parameter types in signature
typehints_use_signature_return = True  # show return type in signature
```

### Handle circular imports

When two modules need to reference each other's types, you'll get circular import errors. Fix this by using
[`from __future__ import annotations`](https://docs.python.org/3/library/__future__.html#module-__future__), which makes
all type hints strings that are resolved later:

```python
from __future__ import annotations

import othermodule


def process(item: othermodule.OtherClass) -> None: ...
```

### Resolve types from `TYPE_CHECKING` blocks

This extension automatically imports types from
[`TYPE_CHECKING`](https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING) blocks at doc-build time. If a
type still fails to resolve, the dependency is likely not installed in your docs environment. Either install it, or
suppress the warning:

```python
suppress_warnings = ["sphinx_autodoc_typehints.guarded_import"]
```

### Show types for `attrs` or `dataclass` fields

The extension backfills annotations from [attrs](https://www.attrs.org/) field metadata automatically. For
[dataclasses](https://docs.python.org/3/library/dataclasses.html), annotations are read from the class body. Make sure
the class is documented with `.. autoclass::` and `:members:` or `:undoc-members:`.

### Write a custom type formatter

To control exactly how a type appears in your docs, provide a formatter function. It receives the type annotation and
the Sphinx config, and returns [RST](https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html) markup (or
`None` to use the default rendering):

```python
def my_formatter(annotation, config):
    if annotation is bool:
        return ":class:`bool`"
    return None


typehints_formatter = my_formatter
```

To always show the full module path for types (e.g., `collections.OrderedDict` instead of `OrderedDict`):

```python
typehints_fully_qualified = True
```

### Document a `NewType` or `type` alias without expanding it

The extension preserves alias names only when they have a `.. py:type::` directive in your docs. Without that entry, the
alias is expanded to its underlying type. Add a documentation entry for the alias, and it will render as a clickable
link instead.

### Add types for C extensions or packages without annotations

The extension reads [`.pyi` stub files](https://typing.python.org/en/latest/spec/distributing.html#stub-files)
automatically. Place a `.pyi` file next to the `.so`/`.pyd` file (or as `__init__.pyi` in the package directory) with
the type annotations, and they'll be picked up.

### Fix cross-reference links for renamed modules

Some libraries expose types under a different module path than where they're documented. For example, GTK types live at
`gi.repository.Gtk.Window` in Python, but their docs list them as `Gtk.Window`. This causes broken
[intersphinx](https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html) links.

Use `typehints_fixup_module_name` to rewrite the module path before links are generated:

```python
def fixup_module_name(module: str) -> str:
    if module.startswith("gi.repository."):
        return module.removeprefix("gi.repository.")
    return module


typehints_fixup_module_name = fixup_module_name
```

### Suppress warnings

To silence all warnings from this extension:

```python
suppress_warnings = ["sphinx_autodoc_typehints"]
```

To suppress only specific warning types, see [Warning categories](#warning-categories) for the full list.

## Reference

### Configuration options

| Option                           | Default | Description                                                                                        |
| -------------------------------- | ------- | -------------------------------------------------------------------------------------------------- |
| `typehints_document_rtype`       | `True`  | Show the return type in docs.                                                                      |
| `typehints_document_rtype_none`  | `True`  | Show return type when it's `None`.                                                                 |
| `typehints_document_overloads`   | `True`  | Show `@overload` signatures in docs. Use `:no-overloads:` in a docstring for per-function control. |
| `typehints_use_rtype`            | `True`  | Show return type as a separate block. When `False`, it's inlined with the return description.      |
| `always_use_bars_union`          | `False` | Use `X \| Y` instead of `Union[X, Y]`. Always on for Python 3.14+.                                 |
| `simplify_optional_unions`       | `True`  | Flatten `Optional[Union[A, B]]` to `Union[A, B, None]`.                                            |
| `typehints_defaults`             | `None`  | Show default values: `"comma"`, `"braces"`, or `"braces-after"`.                                   |
| `typehints_use_signature`        | `False` | Keep parameter types in the function signature.                                                    |
| `typehints_use_signature_return` | `False` | Keep the return type in the function signature.                                                    |
| `typehints_fully_qualified`      | `False` | Show full module path for types (e.g., `module.Class` not `Class`).                                |
| `always_document_param_types`    | `False` | Add types even for parameters that don't have a `:param:` entry in the docstring.                  |
| `typehints_formatter`            | `None`  | A function `(annotation, Config) -> str \| None` for custom type rendering.                        |
| `typehints_fixup_module_name`    | `None`  | A function `(str) -> str` to rewrite module paths before generating cross-reference links.         |

### Warning categories

All warnings can be suppressed via Sphinx's
[`suppress_warnings`](https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-suppress_warnings) in
`conf.py`:

| Category                                      | When it's raised                                                            |
| --------------------------------------------- | --------------------------------------------------------------------------- |
| `sphinx_autodoc_typehints`                    | Catch-all for every warning from this extension.                            |
| `sphinx_autodoc_typehints.comment`            | A type comment (`# type: ...`) couldn't be parsed.                          |
| `sphinx_autodoc_typehints.forward_reference`  | A forward reference (string annotation) couldn't be resolved.               |
| `sphinx_autodoc_typehints.guarded_import`     | A type from a `TYPE_CHECKING` block couldn't be imported at runtime.        |
| `sphinx_autodoc_typehints.local_function`     | A type annotation references a function defined inside another function.    |
| `sphinx_autodoc_typehints.multiple_ast_nodes` | A type comment matched multiple definitions and the right one is ambiguous. |

## Explanation

### How it works

During the Sphinx build, this extension hooks into two
[autodoc events](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#event-autodoc-process-signature).
First, it strips type annotations from function signatures (so they don't appear twice). Then, it reads the annotations
and adds type information into the docstring -- parameter types go next to each `:param:` entry, and the return type
becomes an `:rtype:` entry.

Only parameters that already have a `:param:` line in the docstring get type information added. Set
`always_document_param_types = True` to add types for all parameters, even undocumented ones.

### How return type options interact

The return type options combine as follows:

- **Both defaults** (`typehints_document_rtype = True`, `typehints_use_rtype = True`) -- return type appears as a
  separate `:rtype:` block below the description.
- **Inline mode** (`typehints_document_rtype = True`, `typehints_use_rtype = False`) -- return type is appended to the
  `:return:` text. If there's no `:return:` entry, it falls back to a separate block.
- **Disabled** (`typehints_document_rtype = False`) -- no return type shown, regardless of other settings.
- **Skip None** (`typehints_document_rtype_none = False`) -- hides `None` return types specifically, other return types
  still appear.
