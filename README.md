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
- Types the keys of `**kwargs: Unpack[SomeTypedDict]` as keyword arguments
- Shows the type parameters of generic classes, functions and type aliases in their signatures
- Shows the message of [`@deprecated`](https://peps.python.org/pep-0702/) objects as a deprecation notice
- Links the base class member an [`@override`](https://peps.python.org/pep-0698/) method replaces
- Controls union display style (`Union[X, Y]` vs `X | Y`)
- Automatically fixes cross-references for stdlib types whose runtime module differs from their documented path
- Supports custom type formatters and module name rewriting
- Extracts descriptions from [`Annotated[T, Doc(...)]`](https://typing-extensions.readthedocs.io/en/latest/#Doc)
  metadata
- Works with [Google and NumPy](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html) docstring styles
  and with [numpydoc](https://numpydoc.readthedocs.io/)
- Reads [PEP 484 type comments](https://peps.python.org/pep-0484/#type-comments) when a function has no annotations
- Types instance attributes annotated in `__init__` for their `:ivar:` fields

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
  - [Use with numpydoc](#use-with-numpydoc)
  - [Control return type display](#control-return-type-display)
  - [Change how union types look](#change-how-union-types-look)
  - [Show default parameter values](#show-default-parameter-values)
  - [Document `**kwargs` typed with a `TypedDict`](#document-kwargs-typed-with-a-typeddict)
  - [Document `TypedDict` classes](#document-typeddict-classes)
  - [Control overload signature display](#control-overload-signature-display)
  - [Show deprecations from `@deprecated`](#show-deprecations-from-deprecated)
  - [Link what an `@override` method overrides](#link-what-an-override-method-overrides)
  - [Keep type hints in function signatures](#keep-type-hints-in-function-signatures)
  - [Handle circular imports](#handle-circular-imports)
  - [Resolve types from `TYPE_CHECKING` blocks](#resolve-types-from-type_checking-blocks)
  - [Show types for `attrs` or `dataclass` fields](#show-types-for-attrs-or-dataclass-fields)
  - [Type instance attributes documented with `:ivar:`](#type-instance-attributes-documented-with-ivar)
  - [Write a custom type formatter](#write-a-custom-type-formatter)
  - [Document a `type` alias without expanding it](#document-a-type-alias-without-expanding-it)
  - [Add types for C extensions or packages without annotations](#add-types-for-c-extensions-or-packages-without-annotations)
  - [Use type comments](#use-type-comments)
  - [Document generators](#document-generators)
  - [List parameters once with `autoclass_content = "both"`](#list-parameters-once-with-autoclass_content--both)
  - [Style the injected types](#style-the-injected-types)
  - [Fix cross-reference links for stdlib types](#fix-cross-reference-links-for-stdlib-types)
  - [Fix cross-reference links for renamed modules](#fix-cross-reference-links-for-renamed-modules)
  - [Suppress warnings](#suppress-warnings)
- [Reference](#reference)
  - [Configuration options](#configuration-options)
  - [Typing constructs](#typing-constructs)
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

It needs Python 3.12 or later and Sphinx 9.1 or later, and it is safe for parallel builds (`sphinx-build -j`).

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

With
[`napoleon_use_param`](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html#confval-napoleon_use_param)
or `napoleon_use_keyword` set to `False`, napoleon lists all parameters in one field, and the types go in parentheses
after each name, where napoleon puts a type written in the docstring. A type written in the docstring is kept. With
[numpydoc](https://numpydoc.readthedocs.io/), an `Other Parameters` section renders this way too, under its own heading.

The extension supplies the types napoleon would otherwise read from the annotations for parameters, while napoleon's
`Attributes` sections keep its own lookup. A keyword argument napoleon writes as a `:keyword:` field gets a
`:paramtype:` next to it, and a `:kwtype:` napoleon wrote from the docstring counts as an existing type.

### Use with numpydoc

The [numpydoc](https://numpydoc.readthedocs.io/) extension works too; load it before this extension:

```python
extensions = [
    "sphinx.ext.autodoc",
    "numpydoc",
    "sphinx_autodoc_typehints",
]
```

The `Parameters`, `Other Parameters`, `Returns`, `Yields` and `Raises` sections numpydoc produces are turned into field
lists first, so the types from the annotations go in as they do for Sphinx-style docstrings. An entry naming several
parameters, `a, b : int`, is split into one per name, and a type written in the docstring is kept for a parameter
without an annotation.

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

A union written with the pipe syntax, `str | int`, renders that way. Before Python 3.14, a pipe next to a typing
construct, as in `Literal["a"] | None` or `Self | None`, builds the same object `Optional[...]` does, so it renders like
one unless `always_use_bars_union` is set. One written as `Union[str, int]` or `Optional[str]` renders as written by
default; to show those with pipes too:

```python
always_use_bars_union = True
```

On Python 3.14+, the [pipe syntax](https://docs.python.org/3/library/stdtypes.html#types-union) is always used
regardless of this setting.

By default, `Optional[Union[A, B]]` is simplified to `Union[A, B, None]`. To keep the `Optional` wrapper:

```python
simplify_optional_unions = False
```

With this set to `False`, a `Union[...]` or `Optional[...]` containing `None` displays as `Optional`. A union written
with pipes, such as `int | str | None`, keeps them.

### Show default parameter values

To include default values in your docs, set `typehints_defaults` to one of three styles:

```python
# "param (int, default: 1) -- description"
typehints_defaults = "comma"

# "param (int (default: 1)) -- description"
typehints_defaults = "braces"

# "param (int) -- description (default: 1)"  (at end of text)
typehints_defaults = "braces-after"
```

`None` and `False` leave defaults out, and any other value stops the build with a configuration error. A parameter typed
only in its docstring, by a `:type:` field, as `:param int x:` or in napoleon's combined `Parameters` field, gets the
default next to that type the same way. With `"braces-after"`, the default closes the last plain paragraph of the
description. A list, a directive such as `.. note::`, or a literal block at the end of the description stays as written,
and a paragraph introducing a literal block keeps its `::` last.

### Document `**kwargs` typed with a `TypedDict`

[PEP 692](https://peps.python.org/pep-0692/) types `**kwargs` key by key through a
[`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict). The extension types each key documented
as a keyword argument, the way it types a parameter:

```python
class Options(TypedDict, total=False):
    verbose: Required[bool]
    level: int


def configure(**kwargs: Unpack[Options]) -> None:
    """
    Configure the run.

    :param kwargs: the options
    :keyword verbose: print every step
    :keyword level: how much to print
    """
```

renders `verbose` as `bool` and `level` as `NotRequired[int]`, since a caller may leave it out. A key described through
`Annotated[..., Doc(...)]`, or every key with `always_document_param_types = True`, gets a keyword entry of its own.

### Document `TypedDict` classes

A `TypedDict` documented with `:members:` lists its keys as attributes. A key that may be left out shows as
`NotRequired[...]`, also when the class's `total=False` makes it so rather than its annotation. The items a
[PEP 728](https://peps.python.org/pep-0728/) `TypedDict` accepts beyond its keys show as an `Extra items` field:

```python
class Counts(TypedDict, extra_items=int):
    total: int
```

shows `Extra items: int`, and a `closed=True` class, or one inheriting from it, shows `Extra items: Never`, its
equivalent. A docstring with its own `:Extra items:` field keeps it.

### Control overload signature display

When a function has [`@overload`](https://docs.python.org/3/library/typing.html#typing.overload) signatures, they are
rendered automatically in the docstring, with their types cross-referenced like parameter types and without the `self`
or `cls` parameter of a method. A class lists the overloads of its `__init__` or `__new__`. To disable this globally:

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

The `:no-overloads:` directive is stripped from the rendered output, also when `typehints_document_overloads` is off.

The overloads go right after the summary paragraph, so
[autosummary](https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html) still picks the summary up. A
function documented through its overloads gets no separate return type, since each overload states its own. An exception
class lists its constructor overloads like any other class, and a static method keeps its first parameter.

### Show deprecations from `@deprecated`

A function, method or class decorated with
[`@warnings.deprecated`](https://docs.python.org/3/library/warnings.html#warnings.deprecated) (or the
`typing_extensions` backport) gets a deprecation notice below its summary, styled like Sphinx's
[`deprecated`](https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-deprecated)
directive:

```python
@deprecated("Use fresh() instead.")
def stale(value: int) -> int:
    """Do the stale thing."""
```

renders `Deprecated: Use fresh() instead.` The message shows as written, without markup, as it is the text the object
warns with at runtime. A docstring with a `.. deprecated::` directive of its own, which can name the version, gets no
second notice, and a subclass of a deprecated class is not marked.

### Link what an `@override` method overrides

A method or property marked with [`@typing.override`](https://docs.python.org/3/library/typing.html#typing.override)
gets an `Overrides` field that links the member it replaces, found in the nearest base class that defines it:

```python
class Child(Base):
    @override
    def run(self, count: int) -> str:
        """Run again."""
```

shows `Overrides: Base.run`. A method marked `@override` that no base class defines gets no field.

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
[`TYPE_CHECKING`](https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING) blocks at doc-build time. Any
module-level guard counts, whether it names `TYPE_CHECKING` directly or through a module alias such as
`t.TYPE_CHECKING`, including the `else` branch of `if not TYPE_CHECKING:` and tests that combine it with `and` or `or`.
When the block imports a dependency your docs environment lacks, the extension mocks it the way
[`autodoc_mock_imports`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_mock_imports)
would, so its types still render as cross-references; install it when you want those references to resolve. That
includes a relative import of a sibling module that is absent. An import statement raises a warning when it fails for
another reason, such as a dependency you have installed but that fails to import. A guarded statement that only a type
checker accepts, and that imports nothing, is skipped silently, and the names it would define still work in annotations.
Fix the environment, or suppress the warning:

```python
suppress_warnings = ["sphinx_autodoc_typehints.guarded_import"]
```

### Show types for `attrs` or `dataclass` fields

The extension backfills annotations from [attrs](https://www.attrs.org/) field metadata automatically. For
[dataclasses](https://docs.python.org/3/library/dataclasses.html), annotations are read from the class body. Make sure
the class is documented with `.. autoclass::` and `:members:` or `:undoc-members:`.

### Type instance attributes documented with `:ivar:`

An attribute annotated where `__init__` assigns it gets a `:vartype:` for its `:ivar:` field:

```python
class Job:
    """
    A job.

    :ivar retries: how often it ran again
    """

    def __init__(self) -> None:
        self.retries: int = 0
```

renders `retries` as `int`. Assignments inside `if`, `try` and `with` blocks count, ones in nested functions do not, and
an `:ivar int retries:` or an existing `:vartype retries:` stays as written.

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

With `typehints_use_signature` or `typehints_use_signature_return`, the formatter also decides the types kept in the
signature. A value that is not callable stops the build with a configuration error.

To always show the full module path for types (e.g., `collections.OrderedDict` instead of `OrderedDict`):

```python
typehints_fully_qualified = True
```

It follows Sphinx's
[`autodoc_typehints_format`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_typehints_format)
unless set, so `autodoc_typehints_format = "fully-qualified"` turns it on.

### Document a `type` alias without expanding it

The extension preserves alias names only when they have a `.. py:type::` directive in your docs. Without that entry, the
alias is expanded to its underlying type. A [`NewType`](https://docs.python.org/3/library/typing.html#typing.NewType) is
never expanded: it renders as its name followed by its supertype, `UserId (int)`. Add a documentation entry for the
alias, and it will render as a clickable link instead. The entry has to name the alias where the annotation looks it up:
`.. py:type:: pkg.Vector` serves the functions and methods of `pkg`, while an alias documented in a submodule such as
`pkg.compat` does not.

A plain assignment such as `Count = int` evaluates to the very type it names, so without
`from __future__ import annotations` the extension reads the function's source to tell `limit: Count` from `limit: int`.
Only the parameters written with the alias name render as the alias, and functions without source, such as generated
ones, show the underlying type.

An alias set in
[`autodoc_type_aliases`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_type_aliases)
renders by its name. It links to the target it names when the docs document that target, as a type, class or data entry;
otherwise the name shows as plain text, so the value may also be a display string. The extension decides once every
document is read, so the result does not depend on the order documents are read in or on `-j`.

A recursive alias such as `type Json = dict[str, Json] | list[Json] | str` renders its self-reference as a link to the
alias name. A generic alias used with arguments, `Pairs[int]`, expands with the arguments put in, or shows by name when
the arguments do not fit its parameters.

### Add types for C extensions or packages without annotations

The extension reads [`.pyi` stub files](https://typing.python.org/en/latest/spec/distributing.html#stub-files)
automatically. Place a `.pyi` file next to the `.so`/`.pyd` file (or as `__init__.pyi` in the package directory) with
the type annotations, and they'll be picked up. Beyond that:

- A function a package re-exports from a native submodule, such as `pkg._native.parse` exposed as `pkg.parse`, takes its
  types from the package's `__init__.pyi`, and a native submodule without a `__file__`, as PyO3 builds them, finds its
  stub too.
- The `@overload` variants of a stub combine into a union, unless the stub also gives the implementation's signature.
- `if sys.version_info` and `if sys.platform` branches are followed for the running interpreter.
- A name that exists only in the stub, including a stub `TypeAlias` or `type` alias, renders as a cross-reference.
- A C attribute (a getset or member descriptor) gets its type from the stub's `@property` or class annotation.

### Use type comments

A function without annotations can carry its types in a
[PEP 484 type comment](https://peps.python.org/pep-0484/#type-comments), which the extension reads:

```python
def scale(value, factor):
    # type: (float, int) -> float
    """
    Scale a value.

    :param value: the value
    :param factor: the factor
    """
```

The per-argument form, a `# type:` comment after each parameter, works too, and `self` or `cls` may be left out of the
comment. A comment that does not parse raises a `sphinx_autodoc_typehints.comment` warning.

### Document generators

A function annotated to return a `Generator`, `Iterator`, `AsyncGenerator` or `AsyncIterator` whose docstring has a
`Yields` section (`:Yields:`, `:yields:` or `:yield:`, as napoleon and numpydoc write it) gets no return type, since the
`Yields` section already describes what it produces.

A generator that also hands back a value with `return`, `Generator[int, None, bool]`, and documents it in a `Returns`
section gets that value's type, `bool`, as its return type:

```python
def count() -> Generator[int, None, bool]:
    """
    Yields:
        the numbers

    Returns:
        whether it finished
    """
```

### List parameters once with `autoclass_content = "both"`

With
[`autoclass_content = "both"`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autoclass_content),
Sphinx shows the class and the constructor docstrings together. A parameter either of them documents gets its type
there, and `always_document_param_types` adds the remaining ones only once, under the constructor docstring.

### Style the injected types

Every type the extension adds is wrapped in an inline element with the CSS class `sphinx_autodoc_typehints-type`, which
a theme or a custom stylesheet can target.

### Fix cross-reference links for stdlib types

Many Python stdlib classes have a `__module__` that points to an internal module rather than their public documented
path. For example, `threading.local` reports its module as `_thread._local`, and `concurrent.futures.Executor` as
`concurrent.futures._base.Executor`. This produces broken cross-reference links because the extension builds links from
`__module__.__qualname__`.

When [intersphinx](https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html) is enabled, the extension
automatically fixes this. After intersphinx loads its inventories, it builds a reverse mapping from runtime paths to
documented paths and applies it during annotation formatting. No configuration is needed — just make sure intersphinx is
loaded:

```python
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
```

With this, a type hint like `threading.local` correctly links to `threading.local` in the Python docs instead of
producing a broken `_thread._local` reference.

### Fix cross-reference links for renamed modules

Some third-party libraries expose types under a different module path than where they're documented. For example, GTK
types live at `gi.repository.Gtk.Window` in Python, but their docs list them as `Gtk.Window`. This causes broken
[intersphinx](https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html) links.

Use `typehints_fixup_module_name` to rewrite the module path before links are generated:

```python
def fixup_module_name(module: str) -> str:
    if module.startswith("gi.repository."):
        return module.removeprefix("gi.repository.")
    return module


typehints_fixup_module_name = fixup_module_name
```

Sphinx can't store a function in its cached environment, so, as with `typehints_formatter`, editing the function doesn't
rebuild the pages that use it; run `sphinx-build -E` after changing it.

### Suppress warnings

To silence all warnings from this extension:

```python
suppress_warnings = ["sphinx_autodoc_typehints"]
```

To suppress only specific warning types, see [Warning categories](#warning-categories) for the full list.

## Reference

### Configuration options

| Option                           | Default | Description                                                                                               |
| -------------------------------- | ------- | --------------------------------------------------------------------------------------------------------- |
| `typehints_document_rtype`       | `True`  | Show the return type in docs.                                                                             |
| `typehints_document_rtype_none`  | `True`  | Show return type when it's `None`.                                                                        |
| `typehints_document_overloads`   | `True`  | Show `@overload` signatures in docs. Use `:no-overloads:` in a docstring for per-function control.        |
| `typehints_use_rtype`            | `True`  | Show return type as a separate block. When `False`, it's inlined with the return description.             |
| `always_use_bars_union`          | `False` | Show `Union[X, Y]` and `Optional[X]` with bars too; `X \| Y` always has them. Always on for Python 3.14+. |
| `simplify_optional_unions`       | `True`  | Flatten `Optional[Union[A, B]]` to `Union[A, B, None]`.                                                   |
| `typehints_defaults`             | `None`  | Show default values: `"comma"`, `"braces"`, or `"braces-after"`.                                          |
| `typehints_use_signature`        | `False` | Keep parameter types in the function signature.                                                           |
| `typehints_use_signature_return` | `False` | Keep the return type in the function signature.                                                           |
| `typehints_fully_qualified`      | `False` | Show full module path for types (e.g., `module.Class` not `Class`), in signatures too.                    |
| `always_document_param_types`    | `False` | Add types even for parameters that don't have a `:param:` entry in the docstring.                         |
| `typehints_formatter`            | `None`  | A function `(annotation, Config) -> str \| None` for custom type rendering.                               |
| `typehints_fixup_module_name`    | `None`  | A function `(str) -> str` to rewrite module paths before generating cross-reference links.                |

### Typing constructs

Some annotations render differently from how they are written:

| Written                                                  | Rendered                                                                               |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `*args: *Ts`, `tuple[*Ts]`                               | `Unpack[TypeVarTuple(Ts)]`, `tuple[Unpack[TypeVarTuple(Ts)]]`                          |
| `*args: *tuple[int, ...]`                                | `Unpack[tuple[int, ...]]`                                                              |
| `def f[T: int](value: T)`, `class Box(Generic[T])`       | `T`, with the bound in the signature                                                   |
| `T = TypeVar("T", bound=int)` in a non-generic signature | `TypeVar(T, bound=int)`                                                                |
| `P.args`, `P.kwargs` for `P = ParamSpec("P")`            | `ParamSpecArgs(P)`, `ParamSpecKwargs(P)`, as written when the signature declares `**P` |
| `UserId = NewType("UserId", int)`                        | `UserId (int)`                                                                         |
| `Annotated[int, ...]`                                    | `int`, with a `Doc(...)` in the metadata becoming the description                      |
| `Literal[Color.RED]`                                     | `Literal[Color.RED]`, linking the enum member                                          |
| `tuple[()]`                                              | `tuple[()]`, the empty tuple                                                           |
| `typing_extensions.Self`                                 | `Self`, linking to `typing.Self` where `typing` has it                                 |

With Sphinx's
[`python_display_short_literal_types`](https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-python_display_short_literal_types)
on, `Literal["a", "b"]` renders as `'a' | 'b'`.

The table covers the types the extension writes into fields and signatures. Autodoc writes the header of an attribute or
property itself, so `count: Annotated[int, ...]` keeps its `Annotated` there.

### Warning categories

All warnings can be suppressed via Sphinx's
[`suppress_warnings`](https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-suppress_warnings) in
`conf.py`:

| Category                                      | When it's raised                                                                                          |
| --------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `sphinx_autodoc_typehints`                    | Catch-all for every warning from this extension.                                                          |
| `sphinx_autodoc_typehints.comment`            | A type comment (`# type: ...`) couldn't be parsed, or lists fewer types than the function has parameters. |
| `sphinx_autodoc_typehints.forward_reference`  | An annotation names something undefined or isn't valid Python, on 3.14 unevaluated too; shown as written. |
| `sphinx_autodoc_typehints.guarded_import`     | An import in a `TYPE_CHECKING` block failed for a reason other than an absent dependency.                 |
| `sphinx_autodoc_typehints.local_function`     | A method of a class defined inside a function can't be processed; wrap wrappers with `functools.wraps`.   |
| `sphinx_autodoc_typehints.multiple_ast_nodes` | The source of an unannotated function didn't parse to one definition, so its type comment can't be read.  |

## Explanation

### How it works

During the Sphinx build, this extension hooks into two
[autodoc events](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#event-autodoc-process-signature).
First, it strips type annotations from function signatures (so they don't appear twice). Then, it reads the annotations
and adds type information into the docstring -- parameter types go next to each `:param:` entry, and the return type
becomes an `:rtype:` entry.

Autodoc leaves the type parameters of a generic object out of its signature. The extension adds them after the name,
with bounds, constraints and defaults, the way [PEP 695](https://peps.python.org/pep-0695/) writes them:
`def first[T: Sized](items: T)`, `class Stack[T]` and `type Pairs[K] = dict[K, K]`. A class made generic by subclassing
`Generic[T]` shows its parameters the same way. A type parameter a signature declares this way renders by name where it
is used, as `items (T)` or `args (P.args)`, while a type variable no signature declares keeps its full
`TypeVar(T, bound=int)` form.

Only parameters that already have a `:param:` line in the docstring get type information added, with two exceptions: a
parameter whose annotation carries a `Doc(...)` description gets a `:param:` line of its own, and the entries of
napoleon's combined parameter field get their types in place. Set `always_document_param_types = True` to add types for
all parameters, even undocumented ones; the added lines follow the signature's order, next to the documented parameters,
and go into napoleon's combined `Parameters` or `Keyword Arguments` field when the docstring lists the others there.

Parameters are recognized under `:param`, `:parameter`, `:arg`, `:argument`, `:keyword`, `:kwarg` and `:kwparam`, naming
`*args` and `**kwargs` bare or with escaped stars, `args` or `\*args`. Only fields that start a line count: one indented
into a literal block, a code block or a directive such as a note is left as written. A type written in the field,
`:param int x:`, and a `:type x:` field give way to the annotation, and a parameter without one keeps its docstring
type. A `@typing.no_type_check` function still gets its types, decorated functions are documented through `__wrapped__`,
a class or function stating its signature in `__signature__`, as a pydantic model does, through that signature, a
`functools.partial` or `partialmethod` through the function it calls with the bound arguments left out, a callable
instance through its `__call__`, and an annotation that fails to evaluate shows as written, whatever its own code
raises, with a warning only when it names something undefined or isn't valid Python.

### How return type options interact

The return type options combine as follows:

- **Both defaults** (`typehints_document_rtype = True`, `typehints_use_rtype = True`) -- return type appears as a
  separate `:rtype:` block below the description.
- **Inline mode** (`typehints_document_rtype = True`, `typehints_use_rtype = False`) -- return type is appended to the
  `:return:` text. If there's no `:return:` entry, it falls back to a separate block. A `:return:` entry that already
  states its type, such as napoleon's `*int* -- the value`, is left as it is, while a description that only contains a
  `--`, such as `the value -- or None when missing`, still gets the type. Next to an `:rtype:` field, which the
  annotation replaces, the `:return:` text always counts as a description.
- **Disabled** (`typehints_document_rtype = False`) -- no return type shown, regardless of other settings.
- **Skip None** (`typehints_document_rtype_none = False`) -- hides `None` return types specifically, other return types
  still appear.

Classes and constructors get no return type, and a property shows its type in its header instead. An `:rtype:` written
in the docstring, over one line or several, gives way to the annotation. The separate block goes after the parameter
fields, before the first directive or other block that follows them, or at the end. A return annotation carrying a
`Doc(...)` description adds a `:return:` entry when the docstring has none.
