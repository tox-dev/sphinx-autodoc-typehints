# sphinx-autodoc-typehints

[![PyPI](https://img.shields.io/pypi/v/sphinx-autodoc-typehints?style=flat-square)](https://pypi.org/project/sphinx-autodoc-typehints/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/sphinx-autodoc-typehints.svg)](https://pypi.org/project/sphinx-autodoc-typehints/)
[![Downloads](https://pepy.tech/badge/sphinx-autodoc-typehints/month)](https://pepy.tech/project/sphinx-autodoc-typehints)
[![check](https://github.com/tox-dev/sphinx-autodoc-typehints/actions/workflows/check.yaml/badge.svg)](https://github.com/tox-dev/sphinx-autodoc-typehints/actions/workflows/check.yaml)

This [Sphinx](https://www.sphinx-doc.org/) extension reads the
[type hints](https://docs.python.org/3/library/typing.html) of the code autodoc documents and writes them into the
parameter and return fields, so you state each type once, in the code. Sphinx's own
[`autodoc_typehints = "description"`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_typehints)
moves types into the description too; this extension also links every part of a type, resolves names imported under
`TYPE_CHECKING` or declared in `.pyi` stubs, and handles overloads, default values, and docstrings in napoleon or
numpydoc style. The [GitHub releases page](https://github.com/tox-dev/sphinx-autodoc-typehints/releases) lists the
changes in each version.

<!-- mdformat-toc start --slug=github --no-anchors --maxlevel=6 --minlevel=2 -->

- [Quick start](#quick-start)
- [How-to guides](#how-to-guides)
  - [Choose where types appear](#choose-where-types-appear)
  - [Use with napoleon](#use-with-napoleon)
  - [Use with numpydoc](#use-with-numpydoc)
  - [Document every parameter](#document-every-parameter)
  - [Show default values](#show-default-values)
  - [Control return types](#control-return-types)
  - [Control how unions render](#control-how-unions-render)
  - [Qualify or rewrite module names](#qualify-or-rewrite-module-names)
  - [Write a custom formatter](#write-a-custom-formatter)
  - [Link type aliases](#link-type-aliases)
  - [Document `**kwargs` with `Unpack[TypedDict]`](#document-kwargs-with-unpacktypeddict)
  - [Document overloads](#document-overloads)
  - [Document code that imports under `TYPE_CHECKING`](#document-code-that-imports-under-type_checking)
  - [Document C extensions with `.pyi` stubs](#document-c-extensions-with-pyi-stubs)
  - [Use PEP 484 type comments](#use-pep-484-type-comments)
  - [Fix standard library cross-references](#fix-standard-library-cross-references)
  - [Silence a warning](#silence-a-warning)
- [Reference](#reference)
  - [Configuration options](#configuration-options)
  - [Warnings](#warnings)
  - [Typing constructs](#typing-constructs)
  - [Object features](#object-features)
    - [Deprecations](#deprecations)
    - [Overrides](#overrides)
    - [Property setters](#property-setters)
    - [`TypedDict` classes](#typeddict-classes)
    - [Attributes](#attributes)
    - [Generators](#generators)
  - [Parameter matching rules](#parameter-matching-rules)
  - [How the return options combine](#how-the-return-options-combine)
- [How it works](#how-it-works)

<!-- mdformat-toc end -->

## Quick start

Install it from PyPI; it needs Python 3.12 or later and Sphinx 9.1 or later.

```bash
pip install sphinx-autodoc-typehints
```

Every example in this README documents a module `mod` with `.. automodule:: mod` and its `:members:` option, then shows
what the Sphinx text builder writes for it. Load the extension after autodoc in `conf.py`, then annotate the code and
leave the types out of the docstring.

<!-- example: quick-start -->

```python
# load autodoc first, then this extension
extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
```

```python
def format_unit(value: float, unit: str) -> str:
    """
    Format a value with its unit.

    :param value: a numeric value
    :param unit: the unit, such as kg or m
    """
    return f"{value} {unit}"
```

```text
mod.format_unit(value, unit)

   Format a value with its unit.

   Parameters:
      * **value** ("float") -- a numeric value

      * **unit** ("str") -- the unit, such as kg or m

   Return type:
      "str"
```

The extension is safe for parallel builds (`sphinx-build -j`).

## How-to guides

### Choose where types appear

By default the types go into the fields below the signature, and the signature lists the names alone. Two options keep
them in the signature as well.

<!-- example: use-signature -->

```python
# keep the parameter types in the signature
typehints_use_signature = True
# keep the return type in the signature
typehints_use_signature_return = True
```

```python
def format_unit(value: float, unit: str) -> str:
    """
    Format a value with its unit.

    :param value: a numeric value
    :param unit: the unit, such as kg or m
    """
    return f"{value} {unit}"
```

```text
mod.format_unit(value: float, unit: str) -> str

   Format a value with its unit.

   Parameters:
      * **value** ("float") -- a numeric value

      * **unit** ("str") -- the unit, such as kg or m

   Return type:
      "str"
```

`typehints_formatter`, `typehints_fixup_module_name`, `typehints_fully_qualified` and documented type aliases apply to
the kept types as they do to the fields. Python's own spelling decides the rest, so a `NewType` shows by its name,
`UserId` where the field reads `UserId (int)`, and a type variable no signature declares shows as `~module.T`.

Sphinx's own
[`autodoc_typehints`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_typehints)
setting, at `"description"` or `"both"`, adds the parameters a docstring leaves out, with plain unlinked types, next to
the ones this extension writes. Set it to `"none"` to leave the fields to this extension.

With
[`autoclass_content = "both"`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autoclass_content),
or the `:class-doc-from: both` option of an `autoclass` directive, Sphinx joins the class and constructor docstrings. A
parameter either of them documents gets its type there, and `always_document_param_types` adds the rest once, under the
constructor docstring. The constructor's overloads, the keys of `**kwargs: Unpack[...]` and a `Doc()` description go
there too, while a `@deprecated` notice heads the class docstring.

### Use with napoleon

Load [`sphinx.ext.napoleon`](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html) before this extension
to write Google or NumPy style docstrings.

<!-- example: napoleon -->

```python
# napoleon has to rewrite the docstring before this extension reads it
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx_autodoc_typehints"]
```

```python
def format_unit(value: float, unit: str) -> str:
    """
    Format a value with its unit.

    Args:
        value: a numeric value
        unit: the unit, such as kg or m

    Returns:
        the value followed by its unit
    """
    return f"{value} {unit}"
```

```text
mod.format_unit(value, unit)

   Format a value with its unit.

   Parameters:
      * **value** ("float") -- a numeric value

      * **unit** ("str") -- the unit, such as kg or m

   Return type:
      "str"

   Returns:
      the value followed by its unit
```

Napoleon and this extension share one return type, and napoleon's `:rtype:` gives way to the annotation. Setting
[`napoleon_use_rtype = False`](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html#confval-napoleon_use_rtype)
makes napoleon put the docstring's type into the `Returns` text, so set `typehints_use_rtype = False` as well, or the
type shows twice; a type the `Returns` section writes then stays in place of the annotation's.

Turning
[`napoleon_use_param`](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html#confval-napoleon_use_param)
or `napoleon_use_keyword` off makes napoleon list the parameters or the keyword arguments in one combined field, and the
types go in parentheses after each name. A type the docstring writes there stays. The types napoleon's `Attributes`
section would read from annotations come from this extension, see [Attributes](#attributes).

### Use with numpydoc

Load [numpydoc](https://numpydoc.readthedocs.io/) before this extension.

<!-- example: numpydoc -->

```python
# numpydoc has to rewrite the docstring before this extension reads it
extensions = ["sphinx.ext.autodoc", "numpydoc", "sphinx_autodoc_typehints"]
```

```python
def format_unit(value: float, unit: str) -> str:
    """
    Format a value with its unit.

    Parameters
    ----------
    value
        a numeric value
    unit
        the unit, such as kg or m

    Returns
    -------
    str
        the value followed by its unit
    """
    return f"{value} {unit}"
```

```text
mod.format_unit(value, unit)

   Format a value with its unit.

   Parameters:
      * **value** ("float") -- a numeric value

      * **unit** ("str") -- the unit, such as kg or m

   Return type:
      "str"

   Returns:
      the value followed by its unit
```

The extension turns the `Parameters`, `Other Parameters`, `Returns`, `Yields` and `Raises` sections numpydoc writes into
field lists first, then types them as it types Sphinx-style fields. An entry naming several parameters, `a, b : int`,
splits into one per name, and a type the docstring writes stays for a parameter without an annotation. A `:Parameters:`
field list written by hand, as docutils writes its own docstrings, stays as written, since numpydoc sets each parameter
name in bold and the extension takes a field without that markup for one written by hand.

### Document every parameter

The extension types the parameters the docstring names, and `always_document_param_types` adds the ones it leaves out.

<!-- example: every-parameter -->

```python
# add a field for each parameter the docstring leaves out
always_document_param_types = True
```

```python
def format_unit(value: float, unit: str, precision: int = 2) -> str:
    """
    Format a value with its unit.

    :param value: a numeric value
    """
    return f"{value:.{precision}f} {unit}"
```

```text
mod.format_unit(value, unit, precision=2)

   Format a value with its unit.

   Parameters:
      * **value** ("float") -- a numeric value

      * **unit** ("str")

      * **precision** ("int")

   Return type:
      "str"
```

The added fields follow the signature's order, next to the documented ones. With napoleon's combined `Parameters` or
`Keyword Arguments` field, they join that field.

### Show default values

`typehints_defaults` writes each parameter's default next to its type.

<!-- example: defaults-braces -->

```python
# show the default inside the parentheses that hold the type
typehints_defaults = "braces"
```

```python
def format_unit(value: float, unit: str = "kg") -> str:
    """
    Format a value with its unit.

    :param value: a numeric value
    :param unit: the unit
    """
    return f"{value} {unit}"
```

```text
mod.format_unit(value, unit='kg')

   Format a value with its unit.

   Parameters:
      * **value** ("float") -- a numeric value

      * **unit** ("str" (default: "'kg'")) -- the unit

   Return type:
      "str"
```

`"comma"` writes `unit (str, default: 'kg')` instead, and `"braces-after"` puts `(default: 'kg')` at the end of the
description, closing its last plain paragraph; a list, a directive or a literal block ending the description stays as
written. Both `None`, the default, and `False` leave the defaults out of the docs. A parameter typed in its docstring,
by a `:type:` field, as `:param int x:` or in napoleon's combined field, gets its default next to that type.

A dataclass field declared with `field(default_factory=list)`, or an attrs one with `attrs.field(factory=list)`, shows
the call that builds its default, `list()`, in the signature and in the field. An attrs factory taking the instance
reads `make(self)`. A lambda keeps the `<factory>` placeholder, as the extension can't recover its source from the
`__init__` dataclasses generate.

### Control return types

The return type gets a field of its own unless you tell the extension otherwise.

<!-- example: rtype-inline -->

```python
# write the return type into the Returns text instead of its own field
typehints_use_rtype = False
```

```python
def format_unit(value: float, unit: str) -> str:
    """
    Format a value with its unit.

    :param value: a numeric value
    :param unit: the unit
    :return: the value followed by its unit
    """
    return f"{value} {unit}"
```

```text
mod.format_unit(value, unit)

   Format a value with its unit.

   Parameters:
      * **value** ("float") -- a numeric value

      * **unit** ("str") -- the unit

   Returns:
      "str" -- the value followed by its unit
```

`typehints_document_rtype = False` drops the return type, and `typehints_document_rtype_none = False` drops it only when
it's `None`. [How the return options combine](#how-the-return-options-combine) covers the cases these settings meet.

### Control how unions render

A union written with the pipe, `str | int`, renders that way. One written as `Union[str, int]` or `Optional[str]`
renders as written before Python 3.14, unless `always_use_bars_union` is on.

<!-- example: unions-bars -->

```python
# render Union[...] and Optional[...] with pipes
always_use_bars_union = True
```

```python
from typing import Optional


def find(name: Optional[str]) -> int:
    """
    Find a record.

    :param name: the name to look for
    """
    return 0
```

```text
mod.find(name)

   Find a record.

   Parameters:
      **name** ("str" | "None") -- the name to look for

   Return type:
      "int"
```

Python 3.14 merged `Union` with the pipe syntax, so there every union renders with pipes, whatever the setting says.
Before 3.14, a pipe next to a typing construct, `Literal["a"] | None`, builds the object `Optional[...]` builds, so it
renders like one unless `always_use_bars_union` is on. `simplify_optional_unions`, on by default, flattens
`Optional[Union[A, B]]` to `Union[A, B, None]`; turned off, a `Union[...]` holding `None` shows as `Optional[...]`. It
has no effect on Python 3.14, or on a union written with pipes.

### Qualify or rewrite module names

The extension shows a type by its name, linked to its full path, and `typehints_fully_qualified` shows the full path
instead.

<!-- example: fully-qualified -->

```python
# show each type with its module
typehints_fully_qualified = True
```

```python
from decimal import Decimal


def total(prices: list[Decimal]) -> Decimal:
    """
    Add the prices up.

    :param prices: the prices
    """
    return sum(prices, Decimal())
```

```text
mod.total(prices)

   Add the prices up.

   Parameters:
      **prices** ("list"["decimal.Decimal"]) -- the prices

   Return type:
      "decimal.Decimal"
```

The option follows Sphinx's
[`autodoc_typehints_format`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_typehints_format)
unless you set it, so `autodoc_typehints_format = "fully-qualified"` turns it on.

Some libraries define a type under one module and document it under another. GTK's `gi.repository.Gtk.Window` appears as
`Gtk.Window` in its docs, which breaks the
[intersphinx](https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html) link.
`typehints_fixup_module_name` rewrites the module before the extension builds the link.

```python
# link gi.repository.Gtk.Window to Gtk.Window
def fixup_module_name(module: str) -> str:
    return module.removeprefix("gi.repository.")


typehints_fixup_module_name = fixup_module_name
```

Sphinx can't store a function in its cached environment, so the extension compares the function's source to tell an edit
apart; editing it re-reads every document on the next incremental build. A change to a helper the function calls, or to
data it reads, goes unseen, so run `sphinx-build -E` after one. A `functools.partial` or a callable instance has no
source to compare, so each build re-reads every document; assign a plain function to keep builds incremental.

### Write a custom formatter

`typehints_formatter` takes a callable with the signature `(annotation, config) -> str | None`. It receives each
annotation and the Sphinx [`Config`](https://www.sphinx-doc.org/en/master/extdev/appapi.html#sphinx.config.Config), and
returns the [reStructuredText](https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html) to show, or
`None` to fall back to the default rendering.

<!-- example: formatter -->

```python
# show bool as a plain word
def format_bool(annotation, config):
    return "boolean" if annotation is bool else None


typehints_formatter = format_bool
```

```python
def toggle(flag: bool, times: int) -> bool:
    """
    Flip the flag.

    :param flag: the flag
    :param times: how often to flip it
    """
    return flag ^ (times % 2 == 1)
```

```text
mod.toggle(flag, times)

   Flip the flag.

   Parameters:
      * **flag** (boolean) -- the flag

      * **times** ("int") -- how often to flip it

   Return type:
      boolean
```

With `typehints_use_signature` or `typehints_use_signature_return`, the formatter decides the types kept in the
signature too, where its markup becomes the name it refers to, so `` :class:`bool` `` turns into `bool`. The extension
registers `typehints_formatter` with an empty rebuild value, so Sphinx keeps its cached documents when the formatter
changes; run `sphinx-build -E` after editing it. A value that is not callable stops the build with a `ConfigError`.

### Link type aliases

A `type` alias with a `.. py:type::` entry in the docs, which `automodule` writes for one it documents, renders by its
name and links to that entry. Without the entry the annotation expands to the type it stands for.

<!-- example: type-alias -->

```python
# the defaults cover this
extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
```

```python
type Vector = list[float]
"""Coordinates along each axis."""


def scale(vector: Vector, factor: float) -> Vector:
    """
    Scale a vector.

    :param vector: the vector
    :param factor: the factor
    """
    return [item * factor for item in vector]
```

```text
type mod.Vector = list[float]

   Coordinates along each axis.

mod.scale(vector, factor)

   Scale a vector.

   Parameters:
      * **vector** ("Vector") -- the vector

      * **factor** ("float") -- the factor

   Return type:
      "Vector"
```

The entry has to name the alias where the annotation looks it up. `.. py:type:: pkg.Vector` serves the functions of
`pkg`, and an alias documented in a submodule such as `pkg.compat` does not. The extension picks between the alias and
the type it stands for once Sphinx has read every document, so the entry may come after the function or sit in another
document, and `-j` doesn't change the result. Sphinx writes a signature that `typehints_use_signature` keeps while it
still reads documents, so that signature names the alias only when Sphinx read the entry first.

A plain assignment, `Count = int`, evaluates to the type it names, so without `from __future__ import annotations` the
extension reads the function's source to tell `limit: Count` from `limit: int`. A function without source, such as a
generated one, shows the type the alias names. An alias in
[`autodoc_type_aliases`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_type_aliases)
renders by its name and links to the target it names when the docs document that target; otherwise the name shows as
plain text, so the value may be a display string too.

A recursive alias, `type Json = dict[str, Json] | list[Json] | str`, renders its self-reference as a link to its name. A
generic alias used with arguments, `Pairs[int]`, expands with the arguments in place, or shows by name when they don't
fit its parameters.

### Document `**kwargs` with `Unpack[TypedDict]`

[PEP 692](https://peps.python.org/pep-0692/) types `**kwargs` through a
[`TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict). The extension gives each keyword argument
the docstring names the type of its `TypedDict` entry.

<!-- example: kwargs -->

```python
# napoleon gives the keyword arguments a section of their own
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx_autodoc_typehints"]
# add a keyword field for each TypedDict entry the docstring leaves out
always_document_param_types = True
```

```python
from typing import Required, TypedDict, Unpack

from typing_extensions import ReadOnly


class Options(TypedDict, total=False):
    """The options of a run."""

    verbose: Required[bool]
    level: int
    name: ReadOnly[str]


def configure(**kwargs: Unpack[Options]) -> None:
    """
    Configure the run.

    :param kwargs: the options
    :keyword verbose: print every step
    """
```

```text
class mod.Options

   The options of a run.

mod.configure(**kwargs)

   Configure the run.

   Parameters:
      **kwargs** ("Unpack"["Options"]) -- the options

   Keyword Arguments:
      * **verbose** ("bool") -- print every step

      * **level** ("NotRequired"["int"])

      * **name** ("NotRequired"["ReadOnly"["str"]])

   Return type:
      "None"
```

A caller may leave `level` out, so it reads `NotRequired[int]`, and a `ReadOnly` entry keeps its `ReadOnly[...]`. An
entry described through `Annotated[..., Doc(...)]` gets a keyword field of its own without the setting.

### Document overloads

The extension lists the [`@overload`](https://docs.python.org/3/library/typing.html#typing.overload) signatures of a
function in an `Overloads` field.

<!-- example: overloads -->

```python
# on by default, False drops the Overloads field
typehints_document_overloads = True
```

```python
from typing import overload


@overload
def parse(text: str, /, *, strict: bool = ...) -> int: ...
@overload
def parse(text: bytes) -> str: ...
def parse(text: str | bytes, /, *, strict: bool = False) -> int | str:
    """Parse the text."""
    return 0 if isinstance(text, str) else ""
```

```text
mod.parse(text, /, *, strict=False)

   Parse the text.

   Overloads:
      * **text** ("str"), /, *, **strict** ("bool") = "..." → "int"

      * **text** ("bytes") → "str"
```

Each overload reads like its signature, with its `/` and `*` markers, the stars of `*args` and `**kwargs`, and its
defaults as written; an overload taking nothing shows as `()`. The field leaves out `self` and `cls` and goes right
after the summary paragraph, so [autosummary](https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html)
still picks the summary up. A function documented through its overloads gets no return type, as each overload states its
own. A class lists the overloads of its `__init__` or `__new__`.

Write `:no-overloads:` in a docstring to drop the field for that function alone; the extension strips the marker from
the output, also with `typehints_document_overloads` off.

With `typehints_use_signature = True` the overloads replace the signature instead, one line each, and the field goes
away. Each line shows its return type, as that's what tells overloads apart, except for a class, whose lines list its
constructor's parameters. A default an overload writes as `...` stays `...`: it marks the parameter optional, while the
implementation's default may be a value the overload's type rules out, as `True` for `flag: Literal[False] = ...`. Only
the first line is the link target. A signature written in the directive, `.. autofunction:: f(x)`, stays as written and
keeps the overloads in the field, while `:no-overloads:` keeps the implementation's signature.

### Document code that imports under `TYPE_CHECKING`

The extension runs the module's [`TYPE_CHECKING`](https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING)
blocks during the build, so annotations naming what they import resolve and link.

<!-- example: type-checking -->

```python
# silence the warning a guarded import that fails raises
suppress_warnings = ["sphinx_autodoc_typehints.guarded_import"]
```

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal


def total(prices: list[Decimal]) -> Decimal:
    """
    Add the prices up.

    :param prices: the prices
    """
    return sum(prices)
```

```text
mod.total(prices)

   Add the prices up.

   Parameters:
      **prices** ("list"["Decimal"]) -- the prices

   Return type:
      "Decimal"
```

Two modules that import each other's types work the same way. Guard the import, and add
[`from __future__ import annotations`](https://docs.python.org/3/library/__future__.html#module-__future__) so Python
doesn't evaluate the annotations at import time.

Any module-level guard counts, whether it names `TYPE_CHECKING` or `t.TYPE_CHECKING`, takes the `else` branch of
`if not TYPE_CHECKING:`, or joins the test to others with `and` or `or`. Annotations read the names as a type checker
does, so with `else: ArrayLike = Any` they show the guarded `ArrayLike`. The module itself stays as it is at runtime.
The fallback stays for your code and for autodoc, and a name only the block binds, such as a `Protocol` defined there,
doesn't become a member `automodule` lists.

When the block imports a dependency the docs environment lacks, the extension mocks it the way
[`autodoc_mock_imports`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_mock_imports)
would, so its types still render as references; install it when you want those references to resolve. An import that
fails for another reason, such as a dependency that raises on import, warns under
`sphinx_autodoc_typehints.guarded_import`. When the module's source does not parse as a whole, as with one a custom
loader compiles from another language, the extension reads each guard on its own, and a guard that doesn't parse warns
too. A guarded statement only a type checker accepts, and that imports nothing, goes by without a warning, and the names
it would define still work in annotations.

### Document C extensions with `.pyi` stubs

The extension reads [`.pyi` stub files](https://typing.python.org/en/latest/spec/distributing.html#stub-files). Place
one next to the `.so` or `.pyd` file, or as `__init__.pyi` in the package directory, and functions without annotations
take their types from it.

- A function a package re-exports from a native submodule, `pkg._native.parse` exposed as `pkg.parse`, takes its types
  from the package's `__init__.pyi`. A native submodule without a `__file__`, as PyO3 builds them, finds its stub too.
- A function whose stub imports it from another stub, as `attrs/__init__.pyi` does with
  `from attr import asdict as asdict`, takes its types from that stub.
- The `@overload` variants of a stub combine into a union, unless the stub also gives the implementation's signature.
- The extension follows `if sys.version_info` and `if sys.platform` branches for the running interpreter.
- A name only the stub defines, including a `TypeAlias` or `type` alias, renders as a reference.
- A module the stub imports that isn't installed, `import numpy.typing as npt` without numpy, gets mocked as
  `autodoc_mock_imports` would, so `npt.NDArray` still renders as a reference.
- A C attribute, a getset or member descriptor, takes its type from the stub's `@property` or class annotation.
- Editing a stub re-reads the pages documenting what it describes on the next incremental build.
- Looking for a stub reads a package's attributes without running its [PEP 562](https://peps.python.org/pep-0562/)
  `__getattr__`, so a package that imports on first access, or renames what it hands out as anyio does, stays as autodoc
  found it.

### Use PEP 484 type comments

A function without annotations can carry its types in a [type comment](https://peps.python.org/pep-0484/#type-comments).

<!-- example: type-comments -->

```python
# the defaults cover this
extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
```

```python
def scale(value, factor):
    # type: (float, int) -> float
    """
    Scale a value.

    :param value: the value
    :param factor: the factor
    """
    return value * factor
```

```text
mod.scale(value, factor)

   Scale a value.

   Parameters:
      * **value** ("float") -- the value

      * **factor** ("int") -- the factor

   Return type:
      "float"
```

The per-argument form, a `# type:` comment after each parameter, works too, and the comment may leave out `self` or
`cls`. A comment that doesn't parse warns under `sphinx_autodoc_typehints.comment`.

### Fix standard library cross-references

Many standard library classes report a module other than the one their docs use. `threading.local` reports its module as
`_thread._local`, and `concurrent.futures.Executor` reports `concurrent.futures._base.Executor` as its path. A link
built from those paths finds no target. Load
[intersphinx](https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html) and the extension maps each
runtime path to the documented one, read from the inventories intersphinx loads.

```python
# load intersphinx so the extension can read the documented paths
extensions = ["sphinx.ext.autodoc", "sphinx.ext.intersphinx", "sphinx_autodoc_typehints"]
# the inventory of the Python docs
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
```

Without intersphinx the extension still relocates the classes Sphinx itself knows about, such as `pathlib.Path`, which
lives in `pathlib._local` from Python 3.13 on.

### Silence a warning

Name the warning's category in Sphinx's
[`suppress_warnings`](https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-suppress_warnings):

```python
# silence every warning this extension raises
suppress_warnings = ["sphinx_autodoc_typehints"]
```

[Warnings](#warnings) lists each category with its cause and fix.

## Reference

### Configuration options

Sphinx re-reads every document when an option marked `env` changes; a change to one with an empty rebuild column leaves
the cached documents as they are.

| Option                           | Type           | Default | Rebuild | Effect                                                                                               | How-to                                                              |
| -------------------------------- | -------------- | ------- | ------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `always_document_param_types`    | `bool`         | `False` | `env`   | Add a field for each parameter the docstring leaves out                                              | [Document every parameter](#document-every-parameter)               |
| `always_use_bars_union`          | `bool`         | `False` | `env`   | Render `Union[...]` and `Optional[...]` with pipes; Python 3.14 does so regardless                   | [Control how unions render](#control-how-unions-render)             |
| `simplify_optional_unions`       | `bool`         | `True`  | `env`   | Flatten `Optional[Union[A, B]]` to `Union[A, B, None]` before Python 3.14                            | [Control how unions render](#control-how-unions-render)             |
| `typehints_defaults`             | `str \| None`  | `None`  | `env`   | Show defaults in the `"comma"`, `"braces"` or `"braces-after"` style; `None` or `False` hides them   | [Show default values](#show-default-values)                         |
| `typehints_document_overloads`   | `bool`         | `True`  | `env`   | List `@overload` signatures in an `Overloads` field                                                  | [Document overloads](#document-overloads)                           |
| `typehints_document_rtype`       | `bool`         | `True`  | `env`   | Add the return type                                                                                  | [Control return types](#control-return-types)                       |
| `typehints_document_rtype_none`  | `bool`         | `True`  | `env`   | Add the return type when it's `None`                                                                 | [Control return types](#control-return-types)                       |
| `typehints_fixup_module_name`    | `(str) -> str` | `None`  | `env`   | Rewrite a module path before the extension builds a link                                             | [Qualify or rewrite module names](#qualify-or-rewrite-module-names) |
| `typehints_formatter`            | callable       | `None`  |         | Render an annotation with a `(annotation, config) -> str \| None` callable; `None` keeps the default | [Write a custom formatter](#write-a-custom-formatter)               |
| `typehints_fully_qualified`      | `bool`         | `False` | `env`   | Show each type with its module; follows `autodoc_typehints_format` unless set                        | [Qualify or rewrite module names](#qualify-or-rewrite-module-names) |
| `typehints_use_rtype`            | `bool`         | `True`  | `env`   | Give the return type its own field; `False` writes it into the `:return:` text                       | [Control return types](#control-return-types)                       |
| `typehints_use_signature`        | `bool`         | `False` | `env`   | Keep the parameter types in the signature                                                            | [Choose where types appear](#choose-where-types-appear)             |
| `typehints_use_signature_return` | `bool`         | `False` | `env`   | Keep the return type in the signature                                                                | [Choose where types appear](#choose-where-types-appear)             |

A `typehints_defaults` outside `"comma"`, `"braces"`, `"braces-after"`, `None` and `False`, or a `typehints_formatter`
that isn't callable, stops the build with a `ConfigError` before Sphinx reads any document.

### Warnings

Every warning carries the type `sphinx_autodoc_typehints` and a subtype; `suppress_warnings` takes either.

| Category                                      | Cause                                                                                                              | Fix                                                         |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| `sphinx_autodoc_typehints`                    | Any of the warnings below                                                                                          | Suppress it to silence them all                             |
| `sphinx_autodoc_typehints.comment`            | A type comment doesn't parse, or lists fewer types than the function has parameters                                | Correct the comment, or replace it with annotations         |
| `sphinx_autodoc_typehints.forward_reference`  | An annotation names something undefined or isn't valid Python; it shows as written                                 | Define or import the name, under `TYPE_CHECKING` if need be |
| `sphinx_autodoc_typehints.guarded_import`     | A `TYPE_CHECKING` import fails for a reason other than an absent dependency, or a guard doesn't parse              | Fix the docs environment so the import runs                 |
| `sphinx_autodoc_typehints.local_function`     | The extension can't process a method of a class defined inside a function                                          | Wrap a decorator's wrapper with `functools.wraps`           |
| `sphinx_autodoc_typehints.multiple_ast_nodes` | The source of a function without annotations parses to more than one definition, so its type comment can't be read | Define the function with `def` on lines of its own          |

### Typing constructs

The table shows how a field renders each annotation, every name linked to its documentation. It evaluates the
annotations in this namespace:

<!-- typing-namespace -->

```python
from collections.abc import Callable
from dataclasses import InitVar
from enum import Enum
from types import ModuleType
from typing import (
    Annotated,
    Concatenate,
    Literal,
    NewType,
    NotRequired,
    Optional,
    ParamSpec,
    TypeVar,
    TypeVarTuple,
    Union,
    Unpack,
)

from typing_extensions import Self, Sentinel

T = TypeVar("T")
B = TypeVar("B", bound=int)
C = TypeVar("C", str, bytes)
P = ParamSpec("P")
Ts = TypeVarTuple("Ts")
UserId = NewType("UserId", int)
Color = Enum("Color", "RED GREEN")
MISSING = Sentinel("MISSING")
type Vector = list[float]
type Pairs[K] = dict[K, K]
```

| Construct                                        | Annotation                           | Rendered                                        | Python  |
| ------------------------------------------------ | ------------------------------------ | ----------------------------------------------- | ------- |
| union written with pipes                         | `int \| None`                        | `int \| None`                                   |         |
| `Optional`                                       | `Optional[int]`                      | `Optional[int]`                                 | `<3.14` |
| `Optional`                                       | `Optional[int]`                      | `int \| None`                                   | `3.14+` |
| `Union`                                          | `Union[int, str]`                    | `Union[int, str]`                               | `<3.14` |
| `Union`                                          | `Union[int, str]`                    | `int \| str`                                    | `3.14+` |
| pipe next to a typing construct                  | `Literal["a"] \| None`               | `Optional[Literal['a']]`                        | `<3.14` |
| pipe next to a typing construct                  | `Literal["a"] \| None`               | `Literal['a'] \| None`                          | `3.14+` |
| `Literal`                                        | `Literal["a", "b"]`                  | `Literal['a', 'b']`                             |         |
| `Literal` of an enum member, linked              | `Literal[Color.RED]`                 | `Literal[Color.RED]`                            |         |
| `Callable`                                       | `Callable[[int, str], bool]`         | `Callable[[int, str], bool]`                    |         |
| `Callable` taking any arguments                  | `Callable[..., bool]`                | `Callable[..., bool]`                           |         |
| `ParamSpec`                                      | `Callable[P, int]`                   | `Callable[ParamSpec(P), int]`                   |         |
| `Concatenate`                                    | `Callable[Concatenate[int, P], int]` | `Callable[Concatenate[int, ParamSpec(P)], int]` |         |
| `ParamSpec` components                           | `P.args`                             | `ParamSpecArgs(P)`                              |         |
| `TypeVar` no signature declares                  | `T`                                  | `TypeVar(T)`                                    |         |
| `TypeVar` with a bound                           | `B`                                  | `TypeVar(B, bound=int)`                         |         |
| `TypeVar` with constraints                       | `C`                                  | `TypeVar(C, str, bytes)`                        |         |
| `TypeVarTuple`                                   | `tuple[*Ts]`                         | `tuple[Unpack[TypeVarTuple(Ts)]]`               |         |
| `Unpack`                                         | `Unpack[Ts]`                         | `Unpack[TypeVarTuple(Ts)]`                      |         |
| `NewType`, with the type it wraps                | `UserId`                             | `UserId (int)`                                  |         |
| `Annotated`, metadata dropped                    | `Annotated[int, "meta"]`             | `int`                                           |         |
| empty tuple                                      | `tuple[()]`                          | `tuple[()]`                                     |         |
| variable-length tuple                            | `tuple[int, ...]`                    | `tuple[int, ...]`                               |         |
| `NoneType`                                       | `type(None)`                         | `None`                                          |         |
| class from the `types` module                    | `ModuleType`                         | `ModuleType`                                    |         |
| dataclass `InitVar`                              | `InitVar[int]`                       | `InitVar[int]`                                  |         |
| `TypedDict` qualifier                            | `NotRequired[int]`                   | `NotRequired[int]`                              |         |
| `typing_extensions` backport, linked to `typing` | `Self`                               | `Self`                                          |         |
| PEP 661 sentinel, linked as module data          | `MISSING`                            | `MISSING`                                       |         |
| `type` alias without a `.. py:type::` entry      | `Vector`                             | `list[float]`                                   |         |
| generic `type` alias with arguments              | `Pairs[int]`                         | `dict[int, int]`                                |         |

A name shows without its module unless `typehints_fully_qualified` is on. A type parameter a signature declares, as
`def first[T: Sized](items: T)` or `class Box(Generic[T])` does, renders by name, `T`, with its bound in the signature;
`P.args` renders as `P.args` when the signature declares `**P`. A `Doc(...)` in `Annotated` metadata becomes the
parameter's description. With Sphinx's
[`python_display_short_literal_types`](https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-python_display_short_literal_types)
on, `Literal["a", "b"]` renders as `'a' | 'b'`. A class from a module in `autodoc_mock_imports`, subscripted or not,
renders by its name.

The same rendering applies to the header autodoc writes for data, an attribute or a property, so
`count: Annotated[int, ...]` shows as `count: int` there. A header written by hand, such as `.. py:data:: mod.x` with a
`:type:` option, keeps its type as written. Each type the extension adds sits in an inline element with the CSS class
`sphinx_autodoc_typehints-type`, for a theme or stylesheet to target.

### Object features

Beyond parameters and return types, the extension adds fields for decorators and properties, for `TypedDict` classes and
dataclasses, and for attributes.

<!-- example: object-features -->

```python
# the defaults cover this
extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
```

```python
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import NotRequired, override

from typing_extensions import ReadOnly, TypedDict, deprecated


class Base:
    """A runner."""

    def run(self, count: int) -> str:
        """Run the job."""
        return ""


class Job(Base):
    """
    A job.

    :ivar retries: how often it ran again
    """

    def __init__(self) -> None:
        self.retries: int = 0

    @override
    def run(self, count: int) -> str:
        """Run the job once more."""
        return ""

    @property
    def size(self) -> int:
        """The size of the job."""
        return 0

    @size.setter
    def size(self, new: int | str) -> None: ...


class Counts(TypedDict, extra_items=int):
    """Counts by name."""

    total: int
    """The sum of the counts."""
    rating: ReadOnly[NotRequired[float]]
    """How good the counts look."""


@dataclass
class Batch:
    """A batch of jobs."""

    name: str
    """The name of the batch."""
    jobs: list[Job] = field(default_factory=list)
    """The jobs in the batch."""


@deprecated("Use count_up() instead.")
def count_down(start: int) -> Iterator[int]:
    """
    Count down to zero.

    :param start: where to start
    :yields: the numbers
    """
    yield from range(start, -1, -1)
```

```text
class mod.Base

   A runner.

   run(count)

      Run the job.

      Return type:
         "str"

class mod.Batch(name, jobs=list())

   A batch of jobs.

   jobs: list[Job]

      The jobs in the batch.

   name: str

      The name of the batch.

class mod.Counts

   Counts by name.

   Extra items:
      "int"

   rating: NotRequired[ReadOnly[float]]

      How good the counts look.

   total: int

      The sum of the counts.

class mod.Job

   A job.

   Variables:
      **retries** ("int") -- how often it ran again

   run(count)

      Run the job once more.

      Return type:
         "str"

      Overrides:
         "Base.run"

   property size: int

      The size of the job.

      Setter accepts:
         "int" | "str"

mod.count_down(start)

   Count down to zero.

   Deprecated: Use count_up() instead.

   Parameters:
      **start** ("int") -- where to start

   Yields:
      "int" -- the numbers
```

#### Deprecations

A function, method or class decorated with
[`@warnings.deprecated`](https://docs.python.org/3/library/warnings.html#warnings.deprecated), or its
`typing_extensions` backport, gets a notice below its summary, styled like Sphinx's
[`deprecated`](https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#directive-deprecated)
directive. The message shows as written, without markup, since it's the text the object warns with at runtime. A
docstring with a `.. deprecated::` directive of its own, which can name the version, gets no second notice, and the
extension doesn't mark a subclass of a deprecated class.

#### Overrides

A method or property marked with [`@typing.override`](https://docs.python.org/3/library/typing.html#typing.override)
gets an `Overrides` field linking the member it replaces, in the nearest base class that defines it. A method no base
class defines gets no field. Listed under a subclass with `:inherited-members:`, the method still links what it
overrides in its own class's bases, and the link goes through `typehints_fixup_module_name` like any other.

#### Property setters

Autodoc puts the type a property's getter returns in its header. When the setter's value parameter has another
annotation, the property gets a `Setter accepts` field with it. A property without a setter, such as a
`functools.cached_property`, a setter annotated with the getter's type, or one without an annotation gets no field, and
a docstring with a `:Setter accepts:` field of its own keeps it.

#### `TypedDict` classes

A `TypedDict` documented with `:members:` lists its keys as attributes; keys without a docstring need `:undoc-members:`.
Keys a caller may leave out show as `NotRequired[...]`, also when the class's `total=False` makes them so, and keys a
caller must pass show their type alone, also when written as `Required[...]`. A
[PEP 705](https://peps.python.org/pep-0705/) `ReadOnly` entry keeps its `ReadOnly[...]`, inside `NotRequired[...]` as
the typing spec nests them. The items a [PEP 728](https://peps.python.org/pep-0728/) `TypedDict` accepts beyond its keys
show in an `Extra items` field; a `closed=True` class, or one inheriting from it, shows `Never`, its equivalent. A
docstring with its own `:Extra items:` field keeps it.

#### Attributes

An attribute annotated in the class body, or where `__init__` assigns it, gets its type in the `:ivar:`, `:cvar:` or
`:var:` field that documents it. A `ClassVar[...]` or `Final[...]` shows the type it holds, and where both declare an
attribute, the `__init__` annotation wins. Assignments inside `if`, `try` and `with` blocks count, ones in nested
functions don't, and an `:ivar int retries:` or a `:vartype retries:` of its own stays as written.

With napoleon, the extension types the entries of an `Attributes` section the same way. That covers a class's attributes
annotated in the class body or where `__init__` assigns them, and a module's annotated at module level, whether napoleon
writes them as `:ivar:` fields or, with `napoleon_use_ivar` off, as `.. attribute::` entries. A type the docstring
writes, as in `count (int): ...`, stays. With
[`napoleon_attr_annotations`](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html#confval-napoleon_attr_annotations)
off, napoleon's entries take no type from annotations, as napoleon would give them none; an attribute annotated where
`__init__` assigns it still gets its type in napoleon's `:ivar:` fields, and so does an `:ivar:` field or
`.. attribute::` entry the docstring writes itself.

The extension takes the annotations of [attrs](https://www.attrs.org/) fields from attrs' metadata, and those of
[dataclass](https://docs.python.org/3/library/dataclasses.html) fields from the class body. Autodoc skips a field
without a docstring unless the directive has `:undoc-members:`.

#### Generators

A function annotated to return a `Generator`, `Iterator`, `AsyncGenerator` or `AsyncIterator` whose docstring has a
`Yields` section, `:Yields:`, `:yields:` or `:yield:` as napoleon and numpydoc write it, gets no return type. The
yielded type goes into that section instead, unless it states one. A generator that also hands back a value with
`return`, `Generator[int, None, bool]`, and documents it in a `Returns` section gets that value's type, `bool`, as its
return type. Wrapping the annotation in `Annotated` changes none of this.

### Parameter matching rules

The extension adds a type to the parameters that already have a field in the docstring. A parameter whose annotation
carries a `Doc(...)` description gets a field of its own, the entries of napoleon's combined parameter field get their
types in place, and `always_document_param_types` adds the rest.

The extension reads parameters from the `:param`, `:parameter`, `:arg`, `:argument`, `:keyword`, `:kwarg` and `:kwparam`
fields. A field may name `*args` and `**kwargs` bare or with escaped stars, as `args` or `\*args`. Only a field that
starts a line counts, and one indented into a literal block, a code block or a directive such as a note stays as
written. A type in the field, `:param int x:`, and a `:type x:` field give way to the annotation, and a parameter
without one keeps its docstring type. A keyword argument napoleon writes as a `:keyword:` field gets a `:paramtype:`
next to it, and a `:kwtype:` napoleon wrote from the docstring counts as a type the docstring states.

Some objects take their annotations from another object:

- a decorated function, from its `__wrapped__`
- a class or function stating its signature in `__signature__`, as a pydantic model does, from that signature
- a `functools.partial` or `partialmethod`, from the function it calls, without the bound arguments
- a callable instance documented as a function or method, from its `__call__`

A `@typing.no_type_check` function still gets its types. A data or attribute entry holding a callable gets no parameter
or return types, as it documents a value. An annotation that fails to evaluate shows as written, whatever its own code
raises; it warns under `sphinx_autodoc_typehints.forward_reference` only when it names something undefined or isn't
valid Python.

### How the return options combine

| `typehints_document_rtype` | `typehints_use_rtype` | Result                                                                                      |
| -------------------------- | --------------------- | ------------------------------------------------------------------------------------------- |
| `True`                     | `True`                | The return type gets its own field after the parameter fields                               |
| `True`                     | `False`               | The return type opens the `:return:` text, or gets its own field when there's no `:return:` |
| `False`                    | either                | No return type from the annotation; an `:rtype:` the docstring writes stays                 |

`typehints_document_rtype_none = False` hides a `None` return type in each of these, and `Annotated[None, Doc(...)]`
keeps its description without the type. With `typehints_use_rtype = False`, a `:return:` that already states its type,
such as napoleon's `*int* -- the value`, stays as it is; a description that only contains a `--`, such as
`the value -- or None when missing`, still gets the type. Next to an `:rtype:` field, which the annotation replaces, the
`:return:` text counts as a description.

Classes and constructors get no return type, and a property shows its type in its header. An `:rtype:` the docstring
writes, over one line or several, gives way to the annotation. The separate field goes after the parameter fields,
before the first directive or other block that follows them, or at the end. A return annotation carrying a `Doc(...)`
description adds a `:return:` field when the docstring has none.

## How it works

The extension hooks into autodoc's events and Sphinx's transforms.

```text
autodoc-process-signature      strip the annotations from the signature, keep them with typehints_use_signature
autodoc-process-docstring      evaluate the annotations, write the types into the docstring's fields
object-description-transform   add the type parameters after the name, render the header's type again
post-transform                 choose between each type alias and the type it stands for
```

A signature you write yourself, in the directive as `.. autofunction:: mod.f(x, y=3)` or on the docstring's first line
with
[`autodoc_docstring_signature`](https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_docstring_signature),
stays as written when it names other parameters than the object takes. The extension replaces one with the same
parameters, differing only in defaults or types, with the object's own, and does the same for one made of `*args` and
`**kwargs` alone, which autodoc falls back to when it can't see a class's parameters. A class takes the parameters
autodoc reads for it, those of its metaclass's `__call__` ahead of `__new__` and `__init__`, unless that `__call__` only
passes `*args` and `**kwargs` on.

Autodoc writes the type after the name of data, an attribute or a property itself, evaluating the annotation before any
event runs, so a name imported under `TYPE_CHECKING` resolves there only when documenting something else imported it
first. The extension renders that type again once Sphinx builds the header, the way it renders a field's type, with the
type aliases, `typehints_fully_qualified` and the `TYPE_CHECKING` imports applied. `RATE: decimal.Decimal` therefore
shows as `RATE: Decimal`, as in the field, and a class from a module in `autodoc_mock_imports` shows by its name.

A class whose subscription hands back the class itself, as SQLAlchemy's `TypeEngine` does, evaluates `TypeEngine[_T]` to
a bare `TypeEngine`. The extension evaluates such an annotation again from its source, keeping the arguments, so the
header, the signature, the fields and the overloads show `TypeEngine[_T]`, with `TypeEngine` still linked. The
`__init__` a dataclass or attrs class generates has no source of its own, so its parameters take the annotations its
fields write. A name that the branches of an `if` annotate with different types keeps the bare class, as the source
doesn't tell which branch ran.

Autodoc leaves the type parameters of a generic object out of its signature. The extension adds them after the name,
each with its bound or constraints and its default, the way [PEP 695](https://peps.python.org/pep-0695/) writes them, as
in `def first[T: Sized](items: T)`, `class Stack[T]` and `type Pairs[K] = dict[K, K]`. A class made generic by
subclassing `Generic[T]` shows its parameters the same way. An overload declaring its own,
`def get[S: str](self, key: S)`, renders them by name in its `Overloads` entry. A signature written by hand, such as
`.. py:function:: first(items)`, shows only the type parameters it writes.

A member inherited from a generic base and documented under a subclass that binds the base's type parameters, as
`:inherited-members:` lists it or `.. automethod:: mod.Child.get` names it, shows the arguments the subclass gives them.
With `class Child(Base[int])`, `Base.get(self) -> T` documents as returning `int` under `Child`, while `Base.get` keeps
`T`. The binding follows the bases through each level, so `class C(B[int])` over `class B(A[list[U]])` turns `A`'s `T`
into `list[int]` under `C`. It covers the parameters and return types of methods and constructors, their overloads, the
header of an attribute or property, and the `:vartype:` a class-body annotation gives an `:ivar:`. A `TypedDict` binds
the same way, so `class IntOptions(Options[int])` shows the keys it inherits with `int`, as does
`**kwargs: Unpack[Options[int]]`. A type parameter the subclass leaves unbound, `class Child(Base)`, stays as it is, and
one it passes on, `class Child[U](Base[U])`, renders by name.
