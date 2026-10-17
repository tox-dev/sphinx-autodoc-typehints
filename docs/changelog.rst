###########
 Changelog
###########

.. towncrier-draft-entries:: Unreleased

.. towncrier release notes start

********************
 3.16.0 (2026-10-17)
********************

- Read ``Doc`` descriptions from annotated-doc as well as typing_extensions. :pr:`1083`
- Register the value stylesheet through Sphinx's static-directory API, so loading the extension does not change
  ``html_static_path``. :pr:`1079`
- Honor ``autodoc_use_type_comments = False`` when reading types from a function's ``# type:`` comment. :pr:`1080`
- Use the build platform and false constants when choosing a ``TYPE_CHECKING`` guard's branch; skip guards whose other
  conditions cannot be determined without running code. :pr:`1081`
- Keep single-word prose in hand-written ``:Returns:`` fields, and recognize numpydoc return types containing spaces. :pr:`1082`
- Document support for both Sphinx autodoc implementations and cover re-exported types and ``NamedTuple`` references in
  both modes. :pr:`1084`

********************
 3.15.0 (2026-10-16)
********************

- Allow projects to show selected ``Annotated`` metadata in rendered types with ``typehints_annotated_metadata``. :pr:`1071`
- Process method signatures of classes defined inside functions when the module exports the class under a name autodoc can import. :pr:`1072`
- Let ``typehints_formatter`` receive whether a type appears in a parameter, return, attribute or base when ``typehints_formatter_pass_context`` is enabled. :pr:`1073`
- Reread documents when ``typehints_formatter`` changes in an incremental build, so their rendered types update without ``sphinx-build -E``. :pr:`1069`
- Stop an unchanged incremental build from reporting ``html_static_path`` as changed after the extension adds its stylesheet. :pr:`1070`
- Document inherited special methods of a generic subclass without raising ``Cannot subscript already-subscripted typing.Generic``. :pr:`1074`
- Show a property setter's type when ``Annotated`` metadata raises during comparison with the getter type, instead of failing the build. :pr:`1076`
- Keep the description in a hand-written ``:Returns:`` field instead of interpreting it as a numpydoc return type. :pr:`1077`
- Skip imports under ``if TYPE_CHECKING and False`` instead of resolving types the branch never defines. :pr:`1078`
- Advertise Sphinx, autodoc and type hints in the PyPI keywords instead of unrelated virtual environment terms, and add
  classifiers for documentation, OS independence and the package's type annotations. :pr:`1068`

********************
 3.14.0 (2026-10-16)
********************

- Show the type parameters of PEP 695 functions, classes and type aliases and of ``Generic[T]`` subclasses in their
  signature, such as ``bounded[T: int](value)`` and ``class Stack[T]``, with bounds, constraints and defaults. :pr:`867`
- Type the keys of ``**kwargs: Unpack[TypedDict]`` documented as keyword arguments. :pr:`869`
- Add an ``Overrides`` field linking the base class member a ``@typing.override`` method replaces. :pr:`871`
- Show ``TypedDict`` keys a caller may omit as ``NotRequired[...]``, and add an ``Extra items`` field for PEP 728
  ``extra_items`` and ``closed`` classes. :pr:`873`
- Show the ``@warnings.deprecated`` message as a deprecation notice below the summary. :pr:`874`
- Render a type parameter that the documented signature declares by its name, such as ``T`` instead of
  ``TypeVar(T, bound=int)``, and ``P.args`` and ``P.kwargs`` of a declared ``**P`` as written. :pr:`888`
- Show the return type of a generator with a ``Yields`` section when its docstring has a ``Returns`` section and the
  third argument of its ``Generator`` annotation is not ``None``. :pr:`889`
- With :confval:`typehints_use_signature`, render the types kept in the signature the same way as the fields, so stubs,
  guarded imports, documented aliases, :confval:`typehints_fixup_module_name`, :confval:`typehints_fully_qualified` and
  :confval:`typehints_formatter` apply to both. :pr:`895`
- Render PEP 661 sentinels, the Python 3.15 ``sentinel`` builtin and ``typing_extensions.Sentinel``, by their name as a
  ``py:data`` reference instead of linking a nonexistent ``sentinel`` class. :pr:`912`
- Type ``:ivar:``, ``:cvar:`` and ``:var:`` fields from class-body and base class annotations, dropping ``ClassVar`` and
  ``Final`` qualifiers. :pr:`916`
- Show the yielded type in the ``Yields`` entry of a generator, keeping a type the docstring already states. :pr:`917`
- With napoleon's ``napoleon_use_ivar = False``, type ``.. attribute::`` entries from ``self.x: T`` annotations in
  ``__init__`` unless ``napoleon_attr_annotations = False``; a ``:type:`` already in the docstring wins. :pr:`918`
- Add a ``Setter accepts`` field to a property whose setter annotation differs from the getter's return type. :pr:`919`
- Substitute the type arguments a subclass binds, such as ``int`` for ``T`` under ``class IntStore(Store[int])``, in
  what it inherits from a generic base, covering parameter and return fields, overloads, attribute and property headers,
  ``:vartype:`` fields and ``TypedDict`` keys. :pr:`921`, :pr:`926`, :pr:`938`
- Show a dataclass or attrs default factory as its call, such as ``list()``, in the signature and fields instead of
  ``<factory>`` or ``NOTHING``; lambdas, partials and nested functions keep ``<factory>``. :pr:`922`
- Render the header type of data, attributes and properties the way fields render, so
  :confval:`typehints_fully_qualified`, :confval:`typehints_formatter` and :confval:`typehints_fixup_module_name` apply
  there and the header drops ``Annotated`` metadata. :pr:`923`
- With ``typehints_use_signature = True``, show one typed signature line per ``@overload`` instead of the untyped
  implementation signature and an ``Overloads`` field. :pr:`927`
- Render a module-level ``TypeVar``, ``ParamSpec`` or ``TypeVarTuple`` in docstring fields by its name, as a PEP 695
  type parameter renders, instead of as a ``TypeVar(B, bound=Sized)`` call, and ``P.args`` as written instead of
  ``ParamSpecArgs(P)``; the name links to the variable's own entry, which shows its bound or constraints, when the docs
  document it. :pr:`1044`
- Values in rendered types and defaults, such as ``'fill'`` in ``Literal["fill", 1, None]``, now take the colors of the
  project's Pygments style in light and dark mode, the way a code block does. :pr:`1046`
- Render an unpacked ``TypeVarTuple`` or tuple with the PEP 646 star, ``*Ts`` and ``*tuple[int, ...]``, instead of
  ``Unpack[Ts]``; ``Unpack[TypedDict]`` for ``**kwargs`` keeps its spelling. :pr:`1047`
- Leave out trailing arguments equal to their type parameter's default, so ``typing.ContextManager[None]`` renders as
  ``ContextManager[None]`` instead of ``ContextManager[None, bool | None]`` on Python 3.13 and later; a written
  ``typing.Generator[int, None, None]`` renders as ``Generator[int]``. :pr:`1054`
- Render the ``Bases:`` line of a class documented with ``:show-inheritance:`` as a docstring field renders a type, so a
  generic base such as ``Mapping[str, int]`` follows ``typehints_fully_qualified``, ``typehints_fixup_module_name`` and
  ``typehints_formatter``, and a PEP 695 base such as ``Stack[T]`` keeps its argument where Sphinx left it off. :pr:`1058`
- Render a string annotation that is not a Python expression, such as ``"a positive float"``, as written with a
  ``forward_reference`` warning instead of aborting the build. :pr:`789`
- Load ``sphinx.ext.autodoc`` before connecting to its events, so listing this extension first or omitting autodoc no
  longer fails with ``Unknown event name``. :pr:`790`
- Resolve and link the other annotations of a function when Python cannot evaluate one of them, such as Django's
  ``QuerySet[...]`` without ``django-stubs-ext``, also for a function re-exported with a rewritten ``__module__``, instead
  of showing them all as plain text. :pr:`791`, :pr:`901`
- Document a class that defines ``__new__`` from ``__new__``, as ``inspect.signature`` does, and take a ``__new__``-only
  class's parameter types from ``__new__`` rather than the class body. :pr:`792`
- Keep numpydoc parameter descriptions with several paragraphs or a list, shared type lines such as ``x, y : int``, and
  single ``Yields`` entries. :pr:`793`
- Show ``typehints_defaults = "braces-after"`` defaults on their own parameter when the docstring already has ``:type:``
  lines or napoleon types. :pr:`794`
- Merge the return type into ``:returns:`` with ``typehints_use_rtype = False`` when the docstring also has ``:rtype:`` or
  its ``:returns:`` text starts on the next line. :pr:`795`
- Type napoleon ``Attributes`` entries from the class, ``__init__`` and module annotations, linked and rendered like
  other fields with :confval:`typehints_fully_qualified`, type aliases and :confval:`typehints_formatter` applied, unless
  :confval:`napoleon_attr_annotations` is ``False``. :pr:`796`, :pr:`966`
- Keep the first parameter of static methods bound through ``staticmethod(func)`` and of name-mangled private static
  methods. :pr:`797`
- Link the types in the ``Overloads`` list, leave out ``self`` and ``cls``, and show constructor overloads. :pr:`798`
- Reread the sources when :confval:`always_document_param_types` changes, so incremental builds pick up the new setting. :pr:`799`
- Strip the ``:no-overloads:`` marker from the output when :confval:`typehints_document_overloads` is ``False``. :pr:`800`
- Leave the return annotation off class signatures with ``typehints_use_signature_return = True``. :pr:`801`
- Show a backslash in a signature default once, as plain Sphinx does, unless :confval:`strip_signature_backslash` is on. :pr:`802`
- Report ``sphinx.ext.doctest`` failures on the line the example starts on instead of one line late. :pr:`804`
- Render a ``Callable`` parameterized by a ``ParamSpec`` or ``Concatenate`` as ``Callable[P, int]`` instead of
  ``Callable[[P], int]``. :pr:`805`
- Render ``P.args`` and ``P.kwargs`` as ``ParamSpecArgs(P)`` and ``ParamSpecKwargs(P)``, naming the ``ParamSpec`` they
  belong to. :pr:`806`
- Show the PEP 696 default of a ``TypeVar`` or ``ParamSpec`` after its bound, as in
  ``TypeVar(T, bound=int, default=bool)``. :pr:`807`
- Render a ``ParamSpec`` argument list of a generic as a list, ``Box[[int, str]]``, instead of a tuple. :pr:`808`
- Render a ``TypeVarTuple`` as ``TypeVarTuple(Ts)`` linking to ``typing.TypeVarTuple``, instead of a broken reference that
  loses its name. :pr:`809`
- Fix broken markup and a reference warning for ``Optional[Union[...]]`` with ``simplify_optional_unions = False`` on
  Python before 3.14. :pr:`810`
- Render aliases built with ``typing_extensions.TypeAliasType`` like ``type`` statement aliases instead of as the
  ``TypeAliasType`` class. :pr:`811`
- Resolve names imported under ``TYPE_CHECKING`` guards written through a module alias, on one line, with a comment at
  column zero, or at the end of the file. :pr:`813`
- Resolve the classes, type variables and aliases a class body defines in its method annotations under
  ``from __future__ import annotations``. :pr:`814`, :pr:`941`
- Link instance variable types imported under ``TYPE_CHECKING`` regardless of which class Sphinx documents first. :pr:`815`
- Type keyword arguments documented in a napoleon ``Keyword Args`` section, and stop
  :confval:`always_document_param_types` listing them again under Parameters. :pr:`816`
- With ``autoclass_content = "both"``, list each constructor parameter once, including those added through
  :confval:`always_document_param_types` or ``Doc()``. :pr:`817`, :pr:`925`
- Read stub definitions inside ``sys.version_info`` and ``sys.platform`` blocks, merge all overload variants of a stub
  function, and check re-exports. :pr:`818`
- Link a type documented in this project to its local entry, even when another project's intersphinx inventory re-exports
  it under a different name. :pr:`819`
- Use the role the linked inventory documents for ``types`` classes, so references resolve against ``docs.python.org/3``
  when building on Python 3.12. :pr:`820`
- Resolve names imported under ``TYPE_CHECKING`` in attrs class fields, fixing a ``NameError`` crash on Python 3.14 and a
  forward-reference warning on older versions. :pr:`822`
- Fix an ``AttributeError`` building man pages for projects that document a function taking a ``type`` alias. :pr:`823`
- Pass the Sphinx config to :confval:`typehints_formatter` when rendering signatures with
  :confval:`typehints_use_signature` or :confval:`typehints_use_signature_return`. :pr:`824`
- Parse type text as inline markup, so list-like text such as an unresolvable ``"* weird"`` annotation stays inline
  instead of producing a list or crashing. :pr:`825`
- Keep a function's other type hints and warn ``forward_reference`` when an annotation names a missing module attribute,
  such as ``typing.TypeIs`` on Python 3.12. :pr:`826`
- Import the submodules a ``.pyi`` stub refers to through ``import pkg.sub`` or ``from . import sub``, so their types are
  no longer dropped. :pr:`827`
- Resolve annotations in the module that defines an object, so re-exported objects with a reassigned ``__module__`` find
  their ``TYPE_CHECKING`` imports. :pr:`828`
- Show a plain-assignment alias documented with ``.. py:type::`` by name only where the annotation writes that name,
  whatever order Sphinx reads the entries in, so ``int`` parameters no longer render as an alias of ``int``. :pr:`829`, :pr:`920`
- Apply documented aliases following Python name lookup, so methods see their module's aliases and unrelated aliases
  elsewhere in the package no longer replace a type. :pr:`830`
- Link a ``type`` alias to its own entry, not to a different documented alias with the same name. :pr:`831`
- Run ``TYPE_CHECKING`` guards written as ``if not TYPE_CHECKING: ... else:`` or combined with ``and``/``or``, so their
  imports resolve. :pr:`833`
- Read ``self.x: T`` annotations nested in ``if``, ``try``, ``with``, loop and ``match`` blocks of ``__init__``, and
  handle a positional-only ``self``. :pr:`834`
- Strip types from the signature of ``functools.cache`` and ``functools.lru_cache`` decorated functions on Python 3.14. :pr:`835`
- With ``napoleon_use_param = False`` or ``napoleon_use_keyword = False``, type the entries of napoleon's combined
  parameter field, add their defaults, and list the parameters the extension adds there instead of in a second list. :pr:`836`, :pr:`886`
- With :confval:`typehints_defaults`, show the default of a parameter typed only in its docstring, whether through a
  ``:type:`` line, a ``:param str c:`` field or napoleon's combined parameter field. :pr:`837`, :pr:`884`
- Keep the annotations in the signatures of ``functools.singledispatch`` implementations, so each registered
  implementation shows the type it dispatches on. :pr:`838`
- With :confval:`typehints_defaults`, render defaults the way the signature does, without memory addresses, with enum
  members by name and with sets in a stable order. :pr:`839`
- Keep backslashes in ``Literal`` values, so ``Literal["\n"]`` renders as written instead of ``Literal['n']``. :pr:`840`
- Render ``tuple[()]`` and ``Tuple[()]`` as the empty tuple instead of a bare ``tuple``. :pr:`841`
- Expand a generic ``type`` alias passed to itself, such as ``Pair[Pair[int]]``, instead of dropping the inner
  arguments. :pr:`842`
- Show the enum of a ``Literal`` member, as ``Literal[Color.RED, Light.RED]`` instead of ``Literal[RED, RED]``. :pr:`843`
- Render subscripted types from :confval:`autodoc_mock_imports` modules, such as ``NDArray[float64]``, instead of a
  garbled name. :pr:`844`
- Render ``Literal`` string values that contain backticks without breaking the surrounding markup. :pr:`845`
- Keep the ``|`` of a union around an :confval:`autodoc_type_aliases` name on Python 3.12 and 3.13 instead of rendering
  ``Optional`` or ``Union``. :pr:`846`
- With ``typehints_defaults = "braces-after"``, put the default at the end of the last plain paragraph of the
  description instead of inside a trailing list, directive or literal block. :pr:`847`
- Treat numpydoc's ``..`` placeholder as no description, so entries without one render as ``x (int)`` instead of
  ``x (int) -- ..``. :pr:`848`
- Keep the numpydoc ``Returns`` description of a function without parameters instead of adding a second one from the
  return annotation's ``Doc()``. :pr:`849`
- Keep the text of a napoleon NumPy-style ``Returns`` section that only describes the value. :pr:`850`
- Replace a multi-line docstring ``:rtype:`` as a whole instead of leaving its continuation lines behind. :pr:`851`
- With ``typehints_use_rtype = False``, add the return type to a ``:returns:`` description that contains ``--``. :pr:`852`
- Add parameters documented through :confval:`always_document_param_types` or ``Doc()`` in signature order among the
  documented ones instead of in a second list at the end of the docstring. :pr:`853`
- Place the return type before Sphinx directives such as ``versionadded``, ``deprecated`` and ``seealso``, as
  before docutils directives like ``note``. :pr:`854`
- Link :confval:`autodoc_type_aliases` targets documented as module data or in a document read later. :pr:`855`
- Link a documented generic ``type`` alias even when the docs have no entry for its arguments, instead of expanding it. :pr:`856`
- Link names that only ``typing_extensions`` provides on the running Python, such as ``TypeIs`` on 3.12 and
  ``Doc``, to ``typing_extensions`` instead of a missing ``typing`` target. :pr:`857`
- Stop hiding ``@overload`` signatures from other Sphinx apps in the same process that do not load the extension. :pr:`858`
- Report warnings about admonition content at the right line in documents that use ``.. include::``. :pr:`859`
- Report an invalid :confval:`typehints_defaults` or :confval:`typehints_formatter` value as a configuration error instead
  of an extension crash with a traceback. :pr:`860`
- Stop warning ``Unparsable type hint comment`` for a lambda assigned with a variable type comment. :pr:`861`
- Keep the name and type of a single numpydoc ``Returns`` entry, rendering ``ratio (float) -- The ratio.``. :pr:`862`
- Stop printing docutils errors for docstrings of members left out of the output, such as imported ones
  under ``undoc-members``. :pr:`863`
- Keep a numpydoc ``Other Parameters`` section under its own heading instead of merging it into ``Parameters``. :pr:`864`
- Keep the star of an unpacked ``*tuple[...]``, rendering it as ``Unpack[tuple[...]]``. :pr:`865`
- Render bounded and defaulted type variables as ``TypeVar(T, bound=int)`` without a gap after the ``=``. :pr:`866`
- Keep the type inside ``InitVar[...]`` instead of rendering a bare ``InitVar``. :pr:`875`
- Leave ``:param:``, ``:returns:`` and ``:yields:`` lines inside literal blocks and directives alone instead of
  treating them as the object's fields. :pr:`876`
- Type ``functools.partial`` objects, ``partialmethod`` and callable instances from the function they call, moving the
  annotations from the signature into the fields. :pr:`877`
- Show an annotation whose evaluation raises any exception, including a ``type`` alias whose value raises, as written
  instead of crashing the build or dropping the object. :pr:`878`, :pr:`897`
- Stop dropping module data and class attributes that hold an annotated callable with
  ``list assignment index out of range``. :pr:`879`
- Drop ``cls`` from the signature of a ``@classmethod`` stacked on another decorator such as ``functools.cache``. :pr:`880`
- Stop the ``cannot cache unpickleable configuration value`` warning for :confval:`typehints_fixup_module_name`, and
  re-read the documents only when that function's source changes instead of on every build. :pr:`881`, :pr:`937`
- Document a class or function that sets ``__signature__``, such as a pydantic model, by that signature with its
  fields typed. :pr:`883`
- With ``typehints_use_rtype = False``, keep the inline return type when the docstring had an ``:rtype:`` field. :pr:`885`
- Leave the location out of warnings about code without a source file, such as the ``__init__`` that dataclasses and
  attrs generate, instead of pointing at a nonexistent ``<string>.rst``. :pr:`887`
- Honor ``autodoc_typehints_format = "fully-qualified"``: :confval:`typehints_fully_qualified` defaults to it, so fields,
  signatures and type parameters show full paths. An explicit :confval:`typehints_fully_qualified` still wins. :pr:`891`
- Link pipe unions of mocked types, such as ``Gen[int] | None`` under :confval:`autodoc_mock_imports`, which rendered as
  unlinked text on Python 3.14 or with ``from __future__ import annotations``. :pr:`892`
- Mock a module that a ``.pyi`` stub imports with a plain ``import`` but that is not installed, so types like
  ``npt.NDArray`` render as cross-references instead of raising a ``forward_reference`` warning. :pr:`893`
- Keep a signature written in the directive, such as ``.. autofunction:: mod.f(x, y=3)``, or read from the docstring
  through :confval:`autodoc_docstring_signature`, when it names other parameters than the object takes, instead of
  replacing it with the object's own. One made of ``*args`` and ``**kwargs`` alone still gets the object's parameters
  (:pr:`903`). :pr:`896`
- Format the stub type of a C attribute (getset or member descriptor) with the intersphinx role and documented ``type``
  aliases that parameter types use, fixing broken cross-references. :pr:`902`
- Reread the pages that use a ``.pyi`` stub when the stub changes, so an incremental build picks up the edit. :pr:`905`
- Place the ``Overloads`` list after a literal block that the summary introduces with ``::``, instead of inside it. :pr:`907`
- Show the positional-only ``/`` and keyword-only ``*`` markers, defaults and the stars of ``*args`` and ``**kwargs`` in
  ``Overloads`` entries. :pr:`910`
- Stop rendering ``bound="None"`` on an unbound ``ParamSpec`` on Python 3.12 and early 3.13 releases. :pr:`911`
- Show a backslash in a parameter default once in the field instead of doubled, in every :confval:`typehints_defaults`
  mode. :pr:`913`
- Fix an ``Explicit markup ends without a blank line`` warning when numpydoc processes a docstring without a
  ``Parameters`` section and the extension adds parameter types. :pr:`914`
- Fix a crash on a generator whose return annotation is unhashable, such as
  ``Annotated[Iterator[int], {"unit": "m"}]``, when its docstring has a ``Yields`` section. :pr:`928`
- Follow the ``__signature__`` a decorator sets on its wrapper, so the signature and the parameter fields list the
  parameters callers pass instead of those of the wrapped function; the signature shows types only under
  :confval:`typehints_use_signature`. :pr:`931`, :pr:`946`
- Unwrap an ``Annotated`` return annotation before checking it, so an ``Annotated`` generator types its ``Yields`` entry
  instead of getting a return type, and ``typehints_document_rtype_none = False`` hides ``Annotated[None, ...]``. :pr:`939`
- Stop unwrapping at a Sphinx mock, which cost about two seconds for each mocked object the extension processed. :pr:`954`
- Run a module's ``if TYPE_CHECKING:`` block without writing to the module, so the names it defines, such as
  ``@overload`` stubs or ``Protocol`` classes, no longer replace runtime bindings or show up as module members. :pr:`960`, :pr:`984`
- Keep the subscript arguments of a class whose ``__class_getitem__`` returns the class itself, such as SQLAlchemy's
  ``TypeEngine[Any]``, in headers, parameter and return fields, signatures, overloads and ``:ivar:`` types. :pr:`963`
- Resolve names that two modules' ``if TYPE_CHECKING:`` blocks import from each other to their guarded types,
  whichever module Sphinx documents first. :pr:`969`
- Leave hand-written reST field lists, such as docutils' ``:Parameters:`` definition lists, alone instead of converting
  them as numpydoc output into empty ``:param :`` fields. :pr:`979`
- Keep the signatures and docstrings of the Sphinx, docutils and napoleon methods the extension patches, so a project
  documenting those libraries shows their own signatures and docstrings. :pr:`980`
- Resolve annotations that reach a type through a module alias imported under ``TYPE_CHECKING``, such as
  ``_t.UriType`` in requests, instead of dropping the type. :pr:`985`
- Link a class that a ``.pyi`` stub defines to the module the stub describes, such as ``ext.Config``, instead of
  rendering it as an unresolved bare ``Config`` when the function is documented through a re-export. :pr:`1011`
- Stop aborting the build on a parameter annotated with the bare ``typing.NewType`` class or ``typing.Annotated``
  form; the field names it as a reference, as the signature does. :pr:`1013`
- Overloads of a class documented with ``.. autofunction::`` no longer list ``self`` and ``-> None``, and overloads of a
  function documented with ``.. autoclass::`` keep their first parameter and return types. :pr:`1014`
- Link a name in the type of a data, attribute or property header the way the fields do, so the builtin ``type`` no
  longer links to an unrelated documented attribute such as ``Event.type``. :pr:`1017`
- Link a type an intersphinx inventory lists under both a ``py:class`` and a ``py:data`` name to the class entry on every
  build, instead of a name that changed with ``PYTHONHASHSEED``. :pr:`1018`
- Documenting a ``NamedTuple``'s ``__new__`` on its own, with ``automethod`` or ``:special-members: __new__``, no
  longer warns that names its fields use, such as ``Path`` or ``int``, are not defined. :pr:`1019`
- An attribute a generic base annotates in ``__init__`` now shows the type a subclass binds, such as ``int`` for
  ``class Child(Base[int])``, in that subclass's ``:ivar:`` fields instead of the bare type parameter. :pr:`1020`
- Document a constructor, property setter or overload decorated by something from ``autodoc_mock_imports`` without
  aborting the build with ``wrapper loop when unwrapping``. :pr:`1022`
- Documenting a function typed only by its stub or by type comments no longer writes those types into the function's
  ``__annotations__``, so the object reads the same after a build as before it. :pr:`1025`
- A :confval:`typehints_formatter` that returns an empty string now hides the type instead of showing raw
  ``:sphinx_autodoc_typehints_type:`` text in docstring fields or an empty annotation such as ``attr:  = 1`` in headers and
  signatures, and drops the ``Return type``, ``Extra items`` and ``Setter accepts`` fields it empties. :pr:`1026`
- Link an alias, whether a ``type`` statement or a module-level ``Count = int``, used by an ``automodule`` member when
  its ``py:type`` comes later on the page, instead of expanding it to its value. :pr:`1027`
- A process running more than one Sphinx build now reads the ``TYPE_CHECKING`` block of each module again in every
  build, so a module edited and imported again between builds renders its new types. :pr:`1030`
- Link an enum member inside ``Literal`` to its enum when the member has no entry of its own, such as a member without a
  docstring under ``:members:``, instead of rendering it unlinked with a ``nitpicky`` warning. :pr:`1035`
- Link ``None``, ``True`` and ``False`` inside ``Literal[...]`` to the Python docs, the same way ``None`` links outside
  it, instead of rendering them as plain text. :pr:`1038`
- A class whose ``__module__`` is ``None`` now renders as its bare name instead of a broken cross-reference to ``None.ClassName``. :pr:`1039`
- Types a ``typehints_formatter`` writes between bare backticks inside an expanded type alias now use the document's
  ``default_role``, as they do outside an alias, instead of rendering as italic text. :pr:`1040`
- Stop importing every module an intersphinx inventory lists at the start of the build; the extension now imports only
  the modules that list a class an annotation names, so mapping the numpy or torch inventory no longer imports them. :pr:`1045`
- Stop replacing napoleon's attribute annotation lookup for every Sphinx project in the process; the extension now turns
  :confval:`napoleon_attr_annotations` off for napoleon in its own project only, so the first build after upgrading
  re-reads every document once. :pr:`1048`
- Warnings that point at a definition list, such as a duplicate label placed before one, now name the line the list
  starts on instead of the line after it. :pr:`1049`
- Stop using the deprecated ``SphinxTransform.app`` when choosing between an alias and its value, so builds that run
  Python with ``-W error::PendingDeprecationWarning`` no longer fail, and the extension keeps working on Sphinx 11. :pr:`1051`
- Type the fields napoleon and numpydoc write when they come after ``sphinx_autodoc_typehints`` in ``extensions``;
  the order the two are listed in no longer matters. :pr:`1052`
- Keep the choices between a type alias and its expanded value per document, so removing or editing a document no longer leaves its choices in the cached environment. The first build after upgrading re-reads every document once. :pr:`1059`
- The return type of a function whose docstring has no `:rtype:` or `:return:` now goes where Sphinx puts the types it
  adds with `autodoc_typehints = "description"`: after the last field of the first list with parameters, else of the last
  field list, else in a new list at the end of the docstring. It no longer sits before a definition list, a doctest block,
  a rubric or a section, nor below a table that follows the parameters, and a warning from a docstring reports its own
  line rather than one counting the lines added above it. :pr:`1060`
- Stop a Sphinx build from hanging on a recursive type alias inside a ``Callable`` parameter list. :pr:`1064`
- Keep a submodule's type binding when a documented alias in its parent package has the same name. :pr:`1065`
- Keep ``napoleon_attr_annotations`` at its configured boolean value for other Sphinx extensions. :pr:`1067`
- Publish the documentation on Read the Docs, with tutorials, how-to guides, a reference and every example rendered live
  by the extension. :pr:`1007`
- Add a typing features gallery that renders every public name of :mod:`typing` with the extension, with controls in each example's ``conf.py`` tab that switch the options it renders with. :pr:`1029`
- Compare both rendered outputs in the README, link the typing examples, and correct the event and return-field descriptions. :pr:`1066`
- Depend on ``typing-extensions>=4.16`` on Python versions before 3.15. :pr:`986`

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
