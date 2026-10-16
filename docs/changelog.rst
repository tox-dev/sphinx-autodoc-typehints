###########
 Changelog
###########

.. towncrier-draft-entries:: Unreleased

.. towncrier release notes start

*********************
 3.13.10 (2026-10-13)
*********************

- Link ``typing.Self``, ``Never``, ``LiteralString``, ``Final``, ``TypeAlias``, ``TypeGuard``, ``TypeIs``, ``Required``,
  ``NotRequired``, ``ReadOnly``, ``Unpack``, ``Concatenate`` and ``TypeForm`` to the Python docs instead of rendering
  them as unresolved text, as well as ``ParamSpecArgs`` and ``ParamSpecKwargs`` on Python 3.12. :pr:`786`
- Render a bare ``Literal`` without empty brackets. :pr:`788`
- Annotating with the ``TypeVar`` or ``ParamSpec`` class itself no longer prints its member descriptors. :pr:`787`
- Drop the type hints from the signatures of ``NamedTuple`` classes and classes that only define ``__new__``, like other
  classes. :pr:`784`

********************
 3.13.9 (2026-10-06)
********************

- Fix the forward-reference warning when documenting NumPy's ``clip`` by resolving generic parameters declared in stub
  signatures. :pr:`780`

********************
 3.13.8 (2026-09-29)
********************

- Resolve field types of a ``NamedTuple`` imported under ``TYPE_CHECKING`` when Sphinx documents the class before any
  function from its module, removing a forward-reference warning. :pr:`775`

********************
 3.13.7 (2026-09-18)
********************

- Mock a dependency that a ``TYPE_CHECKING`` block imports but that is not installed, so its types still render as
  cross-references instead of raising a ``Failed guarded type import`` warning. Entries added to
  :confval:`autodoc_mock_imports` only to silence that warning can go. :pr:`770`

********************
 3.13.6 (2026-09-09)
********************

- Expand a type alias when it is not documented and keep its name when it is, regardless of the order objects are
  documented in. :pr:`766`

********************
 3.13.5 (2026-09-01)
********************

- Fix a ``NameError`` crash for a PEP 695 alias defined in another module whose value uses names imported under
  ``TYPE_CHECKING``. :pr:`765`

********************
 3.13.4 (2026-08-24)
********************

- Stop warning ``unknown role name`` for annotations that carry an intersphinx ``external+`` role. :pr:`761`
- A failing ``TYPE_CHECKING`` statement binds only the names it defines, so comprehension and loop targets no longer
  shadow builtins such as ``type`` in rendered annotations. :pr:`760`

********************
 3.13.3 (2026-08-24)
********************

- Stop warning ``unknown role name`` for docstrings that reference another project through an intersphinx ``external+``
  role. :pr:`756`
- A ``TYPE_CHECKING`` block holding expressions the interpreter rejects no longer emits ``Failed guarded type import``
  and forward-reference warnings; its names render as forward references. :pr:`757`
- Fix an ``ExtensionError`` about ``_annotation_globals`` when documenting one object starts documenting another.
  :pr:`758`

********************
 3.13.2 (2026-08-04)
********************

- Support subscripted type aliases. :pr:`745`

********************
 3.13.1 (2026-08-03)
********************

- Fix a ``TypeError`` crash for a module that imports ``TypeAliasType``, whose ``__type_params__`` is not a tuple.
  :pr:`742`
- Run each top-level statement of a ``TYPE_CHECKING`` block separately, so one unimportable name no longer leaves the
  names after it unbound, and keep a missing stub from cascading into forward-reference warnings. :pr:`743`

********************
 3.13.0 (2026-07-20)
********************

- Declare Python 3.15 support. :pr:`735`

********************
 3.12.1 (2026-07-03)
********************

- Resolve the self-reference of a recursive PEP 695 alias defined in another module, fixing a nitpick warning. :pr:`724`

********************
 3.12.0 (2026-06-25)
********************

- Render self-referential PEP 695 type aliases such as ``type RecType = int | list[RecType]`` instead of aborting with
  ``maximum recursion depth exceeded``. :pr:`721`

********************
 3.11.1 (2026-07-15)
********************

- Use the ``py:class`` role for ``types`` module members on Python 3.13+, matching the Python docs. :pr:`732`
- Keep the autosummary one-line summary of overloaded functions above the overload list. :pr:`731`

********************
 3.11.0 (2026-06-11)
********************

- Type properties and attributes of C extensions (getset and member descriptors) from their ``.pyi`` stub. :pr:`716`

********************
 3.10.6 (2026-06-11)
********************

- Keep the type and default of parameters with a trailing underscore, such as ``lambda_``, when documented through
  napoleon. :pr:`714`
- Survive errors raised when Python 3.14 lazily evaluates annotations, such as a non-subscriptable generic. :pr:`713`

********************
 3.10.5 (2026-06-03)
********************

- Keep the first parameter of methods bound on class instances. :pr:`705`
- Use the ``py:class`` role for ``Ellipsis`` and ``NotImplementedType`` on Python 3.13+, matching the Python docs.
  :pr:`707`

********************
 3.10.4 (2026-05-31)
********************

- Fix a ``NameError`` crash on Python 3.14 for annotations that use names imported only under ``TYPE_CHECKING``.
  :pr:`704`

********************
 3.10.3 (2026-05-28)
********************

- Report the extension version in Sphinx error tracebacks. :pr:`687`
- Support the PEP 695 ``type`` statement and ``TypeAliasType`` on Python 3.12+. :pr:`691`
- Fix a cache warning when :confval:`typehints_formatter` is set. :pr:`696`
- Resolve type hints for PyO3, pybind11 and nanobind native submodules from their stubs. :pr:`702`

********************
 3.10.2 (2026-04-15)
********************

- Tolerate malformed ``:ivar`` fields, such as a bare ``:ivar :``, instead of crashing. :pr:`684`

********************
 3.10.1 (2026-04-13)
********************

- Show the annotations of functions decorated with ``@typing.no_type_check``. :pr:`681`

********************
 3.10.0 (2026-04-09)
********************

- Fill ``:vartype:`` for instance variables documented with ``:ivar:`` and annotated in ``__init__`` as
  ``self.name: T = ...``. :pr:`678`
- Stop documented union aliases from an intersphinx inventory replacing every ``X | Y`` annotation. :pr:`679`

********************
 3.9.11 (2026-03-24)
********************

- Resolve imports inside ``if`` blocks of ``.pyi`` stubs. :pr:`670`
- Evaluate stub-only definitions such as ``TypeVar`` and ``TypedDict`` when resolving annotations. :pr:`671`

********************
 3.9.10 (2026-03-23)
********************

- Use the ``__new__`` parameter annotations from stubs instead of class variables. :pr:`667`
- Fix spurious forward-reference warnings when the same stubbed object is documented through several import paths.
  :pr:`668`

*******************
 3.9.9 (2026-03-20)
*******************

- Resolve relative imports in ``.pyi`` stubs. :pr:`663`

*******************
 3.9.8 (2026-03-09)
*******************

- Keep the blank line after a field list when replacing napoleon ``:type:`` fields, fixing a
  ``Field list ends without a blank line`` warning. :pr:`659`

*******************
 3.9.7 (2026-03-05)
*******************

- Resolve ``NamedTuple`` field annotations from the class, fixing forward-reference warnings with
  ``from __future__ import annotations``. :pr:`657`

*******************
 3.9.6 (2026-03-04)
*******************

- Find stubs at the parent package level for C and Rust extension functions it re-exports. :pr:`655`

*******************
 3.9.5 (2026-03-02)
*******************

- Resolve names imported only in ``.pyi`` stubs, so stub types render as cross-references. :pr:`654`

*******************
 3.9.4 (2026-03-02)
*******************

- Find the stub of extension modules with platform-tagged filenames. :pr:`652`

*******************
 3.9.3 (2026-03-02)
*******************

- Stop builtin types like ``dict`` from resolving to an intersphinx alias such as ``wsgiref.types.WSGIEnvironment``.
  :pr:`650`

*******************
 3.9.2 (2026-03-01)
*******************

- Fix an ``AttributeError`` for intersphinx objects without ``__qualname__``. :pr:`648`

*******************
 3.9.1 (2026-03-01)
*******************

- Fix an ``AttributeError`` reading the intersphinx inventory on Sphinx 9.1. :pr:`647`

*******************
 3.9.0 (2026-03-01)
*******************

- Remap classes whose ``__module__`` points to a private module, such as ``threading.local``, to their documented path
  using intersphinx inventories. :pr:`644`
- Add the :confval:`typehints_document_overloads` option and a ``:no-overloads:`` docstring marker to turn off overload
  rendering. :pr:`645`
- Resolve forward references in nested attrs classes. :pr:`646`

*******************
 3.8.0 (2026-02-25)
*******************

- Render ``@overload`` variants in the docstring. :pr:`625`
- Keep type aliases documented with ``.. py:type::`` instead of expanding them. :pr:`626`
- Use ``annotationlib`` on Python 3.14+ to partially resolve forward references. :pr:`627`
- Add the source location to warnings. :pr:`629`
- Resolve type hints from ``.pyi`` stub files for C extensions and other compiled modules. :pr:`630`
- Use ``Annotated[T, Doc(...)]`` metadata as the parameter description. :pr:`631`
- Read attribute types of classic ``@attr.s`` classes from ``attr.ib(type=...)``. :pr:`633`
- Rewrite the README following the Diataxis framework. :pr:`634`

*******************
 3.7.0 (2026-02-23)
*******************

- Remove the ``docs`` and ``testing`` extras; development dependencies moved to dependency groups. :pr:`612`
- Resolve PEP 695 type parameters in annotations with ``from __future__ import annotations``. :pr:`614`
- Separate an injected ``:rtype:`` from the preceding paragraph. :pr:`615`
- Skip the return type for generators whose docstring has a ``Yields`` section. :pr:`616`
- Stop warning on ``ImportError`` from ``TYPE_CHECKING`` blocks of third-party packages. :pr:`617`
- Fix a ``KeyError`` for methods missing from the parent class ``__dict__``. :pr:`620`
- Render ``NewType`` as its name followed by its supertype. :pr:`622`
- Link enum members in ``Literal`` types. :pr:`623`
- Stop directives from running twice while locating the ``:rtype:`` insertion point, fixing duplicate IDs with
  extensions such as sphinx-needs. :pr:`624`

*******************
 3.6.3 (2026-02-18)
*******************

- Remove the extra ``()`` after ``NewType`` in rendered output. :pr:`608`
- Fix a ``ValueError`` for objects with circular ``__wrapped__`` chains. :pr:`607`
- Fix an ``IndexError`` with :confval:`always_document_param_types` and ``typehints_defaults = "braces-after"``.
  :pr:`605`
- Fix a warning when documenting ``__new__`` of ``NamedTuple`` subclasses. :pr:`606`

*******************
 3.6.2 (2026-01-02)
*******************

- Fix compatibility with Sphinx 9.1; require Sphinx 9.1 and Python 3.12 or later. :pr:`595`

*******************
 3.6.1 (2026-01-02)
*******************

- Keep ``Annotated`` metadata and ``Required``, ``NotRequired`` and ``ReadOnly`` qualifiers in type hints. :pr:`594`

*******************
 3.6.0 (2025-12-08)
*******************

- Use the Sphinx 9 class interface; require Sphinx 9.0.4 or later. :pr:`589`

*******************
 3.5.2 (2025-10-16)
*******************

- Keep the docstring type of a parameter without annotation that has a default value. :pr:`576`

*******************
 3.5.1 (2025-10-09)
*******************

- Declare Python 3.14 support. :pr:`571`

*******************
 3.5.0 (2025-10-09)
*******************

- Support the ``Union`` type on its own. :pr:`570`

*******************
 3.4.0 (2025-10-08)
*******************

- Support Python 3.14. :pr:`569`

*******************
 3.3.0 (2025-10-08)
*******************

- Add types and subtypes to warnings so :confval:`suppress_warnings` can silence them. :pr:`562`

*******************
 3.2.0 (2025-04-25)
*******************

- Fix a broken changelog link. :pr:`530`
- Fix missing links for a union with an unevaluated type alias. :pr:`533`
- Stop adding ``:rtype: None``. :pr:`538`
- Place ``:rtype:`` after a directive. :pr:`537`

*******************
 3.1.0 (2025-02-19)
*******************

- Support Sphinx 8.2; drop Python 3.10, as Sphinx does. :pr:`525`

*******************
 3.0.1 (2025-01-16)
*******************

- Fix the roles emitted for ``types`` module members. :pr:`516`

*******************
 3.0.0 (2025-01-02)
*******************

- Replace use of a private docutils API with the public one. :pr:`507`
- Drop support for nptyping. :pr:`514`

*******************
 2.5.0 (2024-10-09)
*******************

- Apply :confval:`typehints_formatter` to the signature. :pr:`494`

*******************
 2.4.4 (2024-09-18)
*******************

- Fix a broken link in the README.

*******************
 2.4.3 (2024-09-17)
*******************

- Update the README.

*******************
 2.4.2 (2024-09-17)
*******************

- Internal maintenance; no user-facing changes.

*******************
 2.4.1 (2024-09-12)
*******************

- Fix placement of the return type when the docstring has a doctest. :pr:`482`

*******************
 2.4.0 (2024-09-07)
*******************

- Drop Python 3.9 support.
- Add Python 3.13 support.

*******************
 2.3.0 (2024-08-29)
*******************

- Add the :confval:`typehints_fixup_module_name` option to rewrite module names. :pr:`474`

*******************
 2.2.3 (2024-07-17)
*******************

- Fix rendering when the docstring starts with a directive. :pr:`468`

*******************
 2.2.2 (2024-06-22)
*******************

- Fix ``typehints_defaults = "braces-after"`` for a multiline ``:param:`` entry. :pr:`464`

*******************
 2.2.1 (2024-06-21)
*******************

- Fix an exception for classes with a custom metaclass, alias lookup by the wrong name, and aliased return types being
  ignored. :pr:`463`

*******************
 2.2.0 (2024-06-19)
*******************

- Honor the :confval:`autodoc_type_aliases` configuration. :pr:`459`

*******************
 2.1.1 (2024-06-03)
*******************

- Internal maintenance; no user-facing changes.

*******************
 2.1.0 (2024-04-17)
*******************

- Support Sphinx 7.3; drop Python 3.8. :pr:`448`

*******************
 2.0.1 (2024-04-10)
*******************

- Document a missing option in the README. :pr:`446`
- Ignore ``rst_prolog`` and ``rst_epilog`` when locating where to inject the return type. :pr:`445`

*******************
 2.0.0 (2024-02-07)
*******************

- Add the :confval:`always_use_bars_union` option to render unions and optionals with ``|``. It is on by default, hence
  the major version. :pr:`418`

********************
 1.25.3 (2024-01-26)
********************

- Stop docstring parsing from overwriting the Sphinx configuration. :pr:`422`

********************
 1.25.2 (2023-11-10)
********************

- Make types in the signature respect :confval:`typehints_fully_qualified`. :pr:`400`

********************
 1.25.1 (2023-11-10)
********************

- Put an escaped space between a cross-reference and its type arguments. :pr:`399`

********************
 1.25.0 (2023-11-09)
********************

- Wrap generated types in a ``sphinx_autodoc_typehints-type`` CSS class. :pr:`397`

********************
 1.24.1 (2023-11-01)
********************

- Evaluate nested type guards recursively. :pr:`393`

********************
 1.24.0 (2023-07-21)
********************

- Drop the ``typed-ast`` dependency. :pr:`373`

********************
 1.23.3 (2023-06-26)
********************

- Fix type guard handling for classes. :pr:`365`

********************
 1.23.2 (2023-06-16)
********************

- Remove the dependency on itself from the package metadata. :pr:`361`

********************
 1.23.1 (2023-06-15)
********************

- Fix a broken GitHub link in the README. :pr:`346`
- Add Python 3.12 support. :pr:`352`

********************
 1.23.0 (2023-04-14)
********************

- Handle forward references in attrs classes. :pr:`345`

******************
 1.22 (2023-01-27)
******************

- Allow Sphinx to write in parallel. :pr:`317`
- Fix crash when documenting ``ParamSpecArgs``. :pr:`319`

********************
 1.21.8 (2023-01-23)
********************

- Add line numbers to more docutils nodes so the return type lands in the right place. :pr:`316`

********************
 1.21.7 (2023-01-20)
********************

- Fix a constructor argument rendering with the wrong type when the class has an attribute with the same name. :pr:`309`
- Fix napoleon handling of numpy docstrings with no explicit return type. :pr:`311`

********************
 1.21.6 (2023-01-20)
********************

- Fix a ``Field list ends without a blank line`` warning. :pr:`307`

********************
 1.21.5 (2023-01-19)
********************

- Find where the ``:rtype:`` field goes in more docstring layouts. :pr:`304`

********************
 1.21.4 (2023-01-17)
********************

- Improve the location of the return type. :pr:`300`

********************
 1.21.3 (2023-01-17)
********************

- Use ``format_annotation`` to render class attribute type annotations. :pr:`299`

********************
 1.21.2 (2023-01-17)
********************

- Fix overloads support. :pr:`297`

********************
 1.21.1 (2023-01-16)
********************

- Fix spacing between ``:rtype:`` and directives. :pr:`294`

********************
 1.21.0 (2023-01-15)
********************

- Put ``Literal`` arguments in code blocks. :pr:`288`
- Handle ``collections.abc.Callable`` as well as ``typing.Callable``. :pr:`289`
- Remove the redundant return type for attributes. :pr:`287`
- Put ``:rtype:`` before an examples or usage section. :pr:`290`
- Render module ``_io`` as ``io``. :pr:`291`
- Handle types from the ``types`` module. :pr:`292`

********************
 1.20.2 (2023-01-13)
********************

- Use the data role for an ``Optional`` created from ``| None``. :pr:`285`

********************
 1.20.1 (2023-01-06)
********************

- Show default values for parameters without type hints. :pr:`279`

********************
 1.20.0 (2023-01-05)
********************

- Add the :confval:`typehints_use_signature` and :confval:`typehints_use_signature_return` options. :pr:`278`

********************
 1.19.5 (2022-11-01)
********************

- Link the pyproject-api docs as an example of this extension. :pr:`267`

********************
 1.19.4 (2022-09-27)
********************

- Fix an ``IndexError`` for line and keyword split. :pr:`261`

********************
 1.19.3 (2022-09-26)
********************

- Support ``typing.ParamSpec``. :pr:`255`
- Allow star prefixes for parameter names in docstrings. :pr:`254`
- Build with hatchling instead of setuptools.

********************
 1.19.2 (2022-08-08)
********************

- Use the data role only for annotations from the ``typing`` module. :pr:`250`

********************
 1.19.1 (2022-07-31)
********************

- Support recursive type aliases. :pr:`248`

********************
 1.19.0 (2022-07-27)
********************

- Support Python 3.11 and stop adding ``Optional`` when the default is ``None``, as PEP 484 recommends. :pr:`247`

********************
 1.18.3 (2022-06-10)
********************

- Support and require ``nptyping>=2.1.2``. :pr:`235`

********************
 1.18.2 (2022-06-03)
********************

- Support and require ``nptyping>=2.1.1``. :pr:`232`

********************
 1.18.1 (2022-04-13)
********************

- Fix mocked module import not working when used as guarded import.

********************
 1.18.0 (2022-04-12)
********************

- Support and require ``nptyping>=2``.
- Handle ``UnionType``.

********************
 1.17.1 (2022-04-12)
********************

- Require ``nptyping<2``.

********************
 1.17.0 (2022-02-11)
********************

- Add the :confval:`typehints_use_rtype` option.
- Handle ``TypeError`` when getting source code via ``inspect``.

********************
 1.16.0 (2022-01-25)
********************

- Support type subscriptions with multiple elements where one or more elements are tuples, such as
  ``nptyping.NDArray[(Any, ...), nptyping.Float]``.
- Fix arbitrary types accepting singleton subscriptions, such as ``nptyping.Float[64]``.
- Resolve forward references.
- Expand and better handle ``TypeVar``.
- Link ``...`` to ``Ellipsis`` through intersphinx.

********************
 1.15.3 (2022-01-18)
********************

- Stop descending into inner blocks that contain ``if TYPE_CHECKING``.

********************
 1.15.2 (2022-01-11)
********************

- Log a warning instead of crashing when a type guard import fails to resolve.
- Do nothing instead of crashing when resolving type guard imports of a module without source code, such as a C
  extension.

********************
 1.15.1 (2022-01-10)
********************

- Rename ``fully_qualified`` to :confval:`typehints_fully_qualified`.

********************
 1.15.0 (2022-01-10)
********************

- Resolve type guard imports before evaluating annotations for objects.
- Remove the ``set_type_checking_flag`` option, as this is now done by default.
- Fix crash when the ``inspect`` module returns invalid Python source.
- Add the :confval:`typehints_formatter` option to configure the formatting function.

********************
 1.14.1 (2022-01-07)
********************

- Fix ``normalize_source_lines()`` breaking the indentation of methods with decorators whose parameters start with
  ``def``.
- Handle ``ValueError`` or ``TypeError`` raised when the signature of an object cannot be determined.
- Fix ``KeyError`` when an argument is not documented, such as ``cls`` for class methods and ``self`` for methods.

********************
 1.14.0 (2022-01-06)
********************

- Add the :confval:`typehints_defaults` option to annotate parameter defaults.

********************
 1.13.1 (2022-01-04)
********************

- Fix ``NewType`` inserting a reference as first argument instead of a string.

********************
 1.13.0 (2022-01-01)
********************

- Drop Python 3.6 support.
- Add Python 3.10 support.
- Normalize async functions.
- Allow Python 3.10 style annotations (PEP 563).

********************
 1.12.0 (2021-04-15)
********************

- Drop Python 3.5 support.
- Add the :confval:`simplify_optional_unions` option.
- Fix indentation of multiline strings.

********************
 1.11.1 (2020-10-12)
********************

- Point ``None`` to the Python stdlib docs.
- Update special dataclass handling.

********************
 1.11.0 (2020-06-21)
********************

- Drop support for Sphinx < 3.0.
- Support alternative parameter names (``arg``, ``argument``, ``parameter``).
- Fix the import path for ``Signature``.
- Fix ``TypeError`` when formatting a parametrized ``typing.IO`` annotation.
- Fix data classes displaying a return type in their ``__init__()`` method.

********************
 1.10.3 (2019-11-11)
********************

- Fix ``TypeError`` (or a wrong class name) when an annotation is a generic class that has a ``name`` property.

********************
 1.10.2 (2019-11-05)
********************

- Fix inner classes missing their parent class names when rendered.

********************
 1.10.1 (2019-11-04)
********************

- Fix ``KeyError`` with mocked annotations (:confval:`autodoc_mock_imports`).

********************
 1.10.0 (2019-11-03)
********************

- Rewrite the annotation formatting logic, fixing Python 3.5.2 compatibility and an ``AttributeError`` introduced in
  1.9.0.
- Process decorator classes as classes.

*******************
 1.9.0 (2019-10-25)
*******************

- Support ``typing_extensions``.
- Add the :confval:`typehints_document_rtype` option.
- Fix metaclasses as annotations causing ``TypeError``.
- Fix rendering of ``typing.Literal``.
- Fix ``OSError`` when generating docs for SQLAlchemy mapped classes.
- Fix unparametrized generic classes rendering with their type parameters, such as ``Dict[~KT, ~VT]``.

*******************
 1.8.0 (2019-09-11)
*******************

- Fix a regression causing ``TypeError`` or ``OSError`` when setting annotations.
- Fix unintentional mangling of annotation type names.
- Add ``:py:data`` targets for ``NoReturn``, ``ClassVar`` and ``Tuple``.
- Support inline type comments such as ``(int, str) -> None``.
- Use the native AST parser for type comment support on Python 3.8+.

*******************
 1.7.0 (2019-07-24)
*******************

- Drop Python 3.4 support.
- Fix unwrapped local functions causing errors.
- Fix ``AttributeError`` when documenting the ``__init__()`` method of a data class.
- Support type hint comments.
- Add an option to render classes with their fully qualified names.

*******************
 1.6.0 (2018-12-23)
*******************

- Fix ``TypeError`` when formatting annotations from a class that inherits from a concrete generic type.
- Support ``typing_extensions.Protocol``.
- Support ``typing.NewType``.

*******************
 1.5.2 (2018-12-02)
*******************

- Warn instead of crashing on an unresolvable forward reference in type annotations.

*******************
 1.5.1 (2018-11-20)
*******************

- Keep escape characters in parameter default values during signature processing.
- Use the :event:`builder-inited` event instead of :event:`config-inited`, which required Sphinx 1.8.

*******************
 1.5.0 (2018-11-14)
*******************

- Add the ``set_type_checking_flag`` option to control setting ``typing.TYPE_CHECKING``.

*******************
 1.4.0 (2018-11-10)
*******************

- Set ``typing.TYPE_CHECKING`` to ``True`` during setup to include conditional imports used in type annotations.
- Fix parameters with trailing underscores.
- Fix ``KeyError`` with private methods.
- Fix a deprecation warning about the use of ``formatargspec``.
- Require Sphinx 1.7.0 or later.
- Fix rendering of generic types outside the ``typing`` module.

*******************
 1.3.0 (2018-03-18)
*******************

- Fix crash when processing docstrings from nested classes.
- Add Python 3.7 support.
- Drop support for Python 3.5.0 and 3.5.1.

*******************
 1.2.5 (2018-02-12)
*******************

- Keep ``:rtype:`` from joining a paragraph of text.

*******************
 1.2.4 (2018-01-17)
*******************

- Remove support for ``backports.typing``, as it was removed from PyPI.
- Fix the first parameter being cut from class methods and static methods.

*******************
 1.2.3 (2017-08-26)
*******************

- Stop ``process_signature()`` clobbering signatures explicitly overridden in the docstring.
- Prefix ``:class:``, ``:mod:`` and other roles with ``:py:``, in case ``py`` is not the default domain of the project.

*******************
 1.2.1 (2017-08-01)
*******************

- Fix ``ValueError`` when ``getargspec()`` encounters a built-in function.
- Fix ``AttributeError`` when ``Any`` is combined with another type in a ``Union``.

*******************
 1.2.0 (2017-03-26)
*******************

- Fix compatibility with Python 3.6 and 3.5.3.
- Fix ``NameError`` when processing signatures of wrapped functions with type hints.
- Fix handling of slotted classes with no ``__init__()`` method.
- Fix a Sphinx warning about parallel reads.
- Stop adding the return type of ``__init__()`` to the class docstring.
- Keep the return type hints of ``@property`` methods.

*******************
 1.1.0 (2016-08-19)
*******************

- Support ``typing.Tuple``.

*******************
 1.0.6 (2016-05-08)
*******************

- Fix placement of ``:rtype:`` after a multi-line ``:param:`` or a ``:returns:``.

*******************
 1.0.5 (2016-05-03)
*******************

- Process the signatures of coroutine functions when using sphinxcontrib-asyncio.

*******************
 1.0.4 (2016-04-09)
*******************

- Fix compatibility with Sphinx 1.4.

*******************
 1.0.3 (2015-11-19)
*******************

- Remove ``self`` from exception class constructor signatures.
- Stop ``process_signature()`` removing the first argument of a static method.

*******************
 1.0.2 (2015-10-31)
*******************

- Process exception classes like normal classes.

*******************
 1.0.1 (2015-09-22)
*******************

- Look up forward references with the right globals.

*******************
 1.0.0 (2015-09-22)
*******************

- Initial release.
