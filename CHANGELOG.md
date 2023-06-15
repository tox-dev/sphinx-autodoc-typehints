# Changelog

## 1.22

- Allow Sphinx explicitly to write in parallel.
- Fixed crash when documenting ParamSpecArgs

## 1.21.7

- Fixed a bug where if a class has an attribute and a constructor argument with the same name, the constructor argument
  type would be rendered incorrectly (issue 308)

- Fixed napoleon handling of numpy docstrings with no specified return type.

## 1.21.6

- Fix a `Field list ends without a blank line` warning (issue 305).

## 1.21.5

- More robust determination of rtype location / fix issue 302

## 1.21.4

- Improvements to the location of the return type

## 1.21.3

- Use format_annotation to render class attribute type annotations

## 1.21.2

- Fix overloads support

## 1.21.1

- Fix spacing between `:rtype:` and directives

## 1.21

- Handle types from types module
- If module is \_io, use io instead
- Put rtype before examples or usage section
- Remove redundant return type for attributes
- Handle collections.abc.Callable as well as typing.Callable
- Put Literal args in code blocks

## 1.20.2

- Fix Optional role to be data.

## 1.20.1

- Fixed default options not displaying for parameters without type hints.

## 1.20

- Use hatchling instead of setuptools
- Add support for typing.ParamSpec
- Allow star prefixes for parameter names in docstring

## 1.19.2

- Fix incorrect domain used for collections.abc.Callable.

## 1.19.1

- Fix bug for recursive type alias.

## 1.19.0

- Support for CPython 3.11, no longer adds `Optional` when the argument is default per
  [recommendation from PEP-484](https://github.com/tox-dev/sphinx-autodoc-typehints/pull/247).

## 1.18.3

- Support and require `nptyping>=2.1.2`

## 1.18.2

- Support and require `nptyping>=2.1.1`

## 1.18.1

- Fix mocked module import not working when used as guarded import

## 1.18.0

- Support and require `nptyping>=2`
- Handle `UnionType`

## 1.17.1

- Mark it as requiring `nptyping<2`

## 1.17.0

- Add `typehints_use_rtype` option
- Handles `TypeError` when getting source code via inspect

## 1.16.0

- Add support for type subscriptions with multiple elements, where one or more elements are tuples; e.g.,
  `nptyping.NDArray[(Any, ...), nptyping.Float]`
- Fix bug for arbitrary types accepting singleton subscriptions; e.g., `nptyping.Float[64]`
- Resolve forward references
- Expand and better handle `TypeVar`
- Add intershpinx reference link for `...` to `Ellipsis` (as is just an alias)

## 1.15.3

- Prevents reaching inner blocks that contains `if TYPE_CHECKING`

## 1.15.2

- Log a warning instead of crashing when a type guard import fails to resolve
- When resolving type guard imports if the target module does not have source code (such is the case for C-extension
  modules) do nothing instead of crashing

## 1.15.1

- Fix `fully_qualified` should be `typehints_fully_qualified`

## 1.15.0

- Resolve type guard imports before evaluating annotations for objects
- Remove `set_type_checking_flag` flag as this is now done by default
- Fix crash when the `inspect` module returns an invalid python syntax source
- Made formatting function configurable using the option `typehints_formatter`

## 1.14.1

- Fixed `normalize_source_lines()` messing with the indentation of methods with decorators that have parameters starting
  with `def`.
- Handle `ValueError` or `TypeError` being raised when signature of an object cannot be determined
- Fix `KeyError` being thrown when argument is not documented (e.g. `cls` argument for class methods, and `self` for
  methods)

## 1.14.0

- Added `typehints_defaults` config option allowing to automatically annotate parameter defaults.

## 1.13.1

- Fixed `NewType` inserts a reference as first argument instead of a string

## 1.13.0

- Dropped Python 3.6 support
- Python 3.10 support
- Normalize async functions properly
- Allow py310 style annotations (PEP-563)

## 1.12.0

- Dropped Python 3.5 support
- Added the simplify_optional_unions config option (PR by tillhainbach)
- Fixed indentation of multiline strings (PR by Yuxin Wu)

## 1.11.1

- Changed formatting of `None` to point to the Python stdlib docs (PR by Dominic Davis-Foster)
- Updated special dataclass handling (PR by Lihu Ben-Ezri-Ravin)

## 1.11.0

- Dropped support for Sphinx \< 3.0
- Added support for alternative parameter names (`arg`, `argument`, `parameter`)
- Fixed import path for Signature (PR by Matthew Treinish)
- Fixed `TypeError` when formatting a parametrized `typing.IO` annotation
- Fixed data class displaying a return type in its `__init__()` method

## 1.10.3

- Fixed `TypeError` (or wrong rendered class name) when an annotation is a generic class that has a `name` property

## 1.10.2

- Fixed inner classes missing their parent class name(s) when rendered

## 1.10.1

- Fixed `KeyError` when encountering mocked annotations (`autodoc_mock_imports`)

## 1.10.0

- Rewrote the annotation formatting logic (fixes Python 3.5.2 compatibility regressions and an `AttributeError`
  regression introduced in v1.9.0)
- Fixed decorator classes not being processed as classes

## 1.9.0

- Added support for [typing_extensions](https://pypi.org/project/typing-extensions/)
- Added the `typehints_document_rtype` option (PR by Simon-Martin Schröder)
- Fixed metaclasses as annotations causing `TypeError`
- Fixed rendering of `typing.Literal`
- Fixed OSError when generating docs for SQLAlchemy mapped classes
- Fixed unparametrized generic classes being rendered with their type parameters (e.g. `Dict[~KT, ~VT]`)

## 1.8.0

- Fixed regression which caused `TypeError` or `OSError` when trying to set annotations due to PR #87
- Fixed unintentional mangling of annotation type names
- Added proper `:py:data` targets for `NoReturn`, `ClassVar` and `Tuple`
- Added support for inline type comments (like `(int, str) -> None`) (PR by Bernát Gábor)
- Use the native AST parser for type comment support on Python 3.8+

## 1.7.0

- Dropped support for Python 3.4
- Fixed unwrapped local functions causing errors (PR by Kimiyuki Onaka)
- Fixed `AttributeError` when documenting the `__init__()` method of a data class
- Added support for type hint comments (PR by Markus Unterwaditzer)
- Added flag for rendering classes with their fully qualified names (PR by Holly Becker)

## 1.6.0

- Fixed `TypeError` when formatting annotations from a class that inherits from a concrete generic type (report and
  tests by bpeake-illuscio)
- Added support for `typing_extensions.Protocol` (PR by Ian Good)
- Added support for `typing.NewType` (PR by George Leslie-Waksman)

## 1.5.2

- Emit a warning instead of crashing when an unresolvable forward reference is encountered in type annotations

## 1.5.1

- Fixed escape characters in parameter default values getting lost during signature processing
- Replaced use of the `config-inited` event (which inadvertently required Sphinx 1.8) with the `builder-inited` event

## 1.5.0

- The setting of the `typing.TYPECHECKING` flag is now configurable using the `set_type_checking_flag` option

## 1.4.0

- The extension now sets `typing.TYPECHECKING` to `True` during setup to include conditional imports which may be used
  in type annotations
- Fixed parameters with trailing underscores (PR by Daniel Knell)
- Fixed KeyError with private methods (PR by Benito Palacios Sánchez)
- Fixed deprecation warning about the use of formatargspec (PR by Y. Somda)
- The minimum Sphinx version is now v1.7.0

## 1.3.1

- Fixed rendering of generic types outside the typing module (thanks to Tim Poterba for the PR)

## 1.3.0

- Fixed crash when processing docstrings from nested classes (thanks to dilyanpalauzov for the fix)
- Added support for Python 3.7
- Dropped support for Python 3.5.0 and 3.5.1

## 1.2.5

- Ensured that `:rtype:` doesn\'t get joined with a paragraph of text (thanks to Bruce Merry for the PR)

## 1.2.4

- Removed support for `backports.typing` as it has been removed from the PyPI
- Fixed first parameter being cut out from class methods and static methods (thanks to Josiah Wolf Oberholtzer for the
  PR)

## 1.2.3

- Fixed `process_signature()` clobbering any explicitly overridden signatures from the docstring

## 1.2.2

- Explicitly prefix `:class:`, `:mod:` et al with `:py:`, in case `py` is not the default domain of the project (thanks
  Monty Taylor)

## 1.2.1

- Fixed ``ValueError` when``getargspec()\`\` encounters a built-in function
- Fixed `AttributeError` when `Any` is combined with another type in a `Union` (thanks Davis Kirkendall)

## 1.2.0

- Fixed compatibility with Python 3.6 and 3.5.3
- Fixed `NameError` when processing signatures of wrapped functions with type hints
- Fixed handling of slotted classes with no `__init__()` method
- Fixed Sphinx warning about parallel reads
- Fixed return type being added to class docstring from its `__init__()` method (thanks to Manuel Krebber for the patch)
- Fixed return type hints of `@property` methods being omitted (thanks to pknight for the patch)
- Added a test suite (thanks Manuel Krebber)

## 1.1.0

- Added proper support for `typing.Tuple` (pull request by Manuel Krebber)

## 1.0.6

- Fixed wrong placement of `:rtype:` if a multi-line `:param:` or a `:returns:` is used

## 1.0.5

- Fixed coroutine functions\' signatures not being processed when using sphinxcontrib-asyncio

## 1.0.4

- Fixed compatibility with Sphinx 1.4

## 1.0.3

- Fixed \"self\" parameter not being removed from exception class constructor signatures
- Fixed process_signature() erroneously removing the first argument of a static method

## 1.0.2

- Fixed exception classes not being processed like normal classes

## 1.0.1

- Fixed errors caused by forward references not being looked up with the right globals

## 1.0.0

- Initial release
