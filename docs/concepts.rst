##############
 How it works
##############

This page explains what the extension does during a build, in the order Sphinx calls it, and why a type shows where it
does, then compares the result with Sphinx's built-in type hints. The :doc:`how-to` show how to change the result, and
the :doc:`reference` lists the options.

****************
 The event flow
****************

On a rendered page the signature lists the parameter names alone, and each field below it carries a type. The
extension produces that at four points of a build. Sphinx announces each step of a build as an :doc:`event
<sphinx:extdev/event_callbacks>`, and an extension registers functions to run on the ones it cares about. Autodoc adds
events of its own around each object it documents, and the extension changes the signature and the docstring there.
For each object, Sphinx calls the extension at three points. Once every document is read, a post-transform, a pass
over the parsed documents before Sphinx writes them out, makes the last choice:

.. list-table::
    :header-rows: 1
    :widths: 35 65

    * - Hook
      - What the extension does
    * - :event:`autodoc-process-signature`
      - strip the annotations from the signature, keep them with :confval:`typehints_use_signature`
    * - :event:`autodoc-process-docstring`
      - evaluate the annotations, write the types into the docstring's fields
    * - :event:`object-description-transform`
      - add the type parameters after the name, render the header's type again
    * - post-transform
      - choose between each type alias and the type it stands for

.. mermaid::

    sequenceDiagram
        box rgba(230, 81, 0, 0.08) Sphinx
            participant sphinx_autodoc as autodoc
            participant sphinx_docstrings as napoleon or numpydoc
        end
        box rgba(46, 125, 50, 0.08) sphinx-autodoc-typehints
            participant extension_handlers as extension
        end
        Note over sphinx_autodoc,extension_handlers: for each documented object
        sphinx_autodoc->>+extension_handlers: autodoc-process-signature
        extension_handlers-->>-sphinx_autodoc: signature without types, or one line per overload
        sphinx_autodoc->>sphinx_docstrings: autodoc-process-docstring
        sphinx_docstrings-->>sphinx_autodoc: Google and NumPy sections as reST fields
        sphinx_autodoc->>+extension_handlers: autodoc-process-docstring
        extension_handlers-->>-sphinx_autodoc: fields with the types, defaults and overloads
        sphinx_autodoc->>+extension_handlers: object-description-transform
        extension_handlers-->>-sphinx_autodoc: header with type parameters and the data's type
        Note over sphinx_autodoc,extension_handlers: after every document is read
        sphinx_autodoc->>+extension_handlers: post-transform
        extension_handlers-->>-sphinx_autodoc: link to the alias or its expanded value

The docstring handler runs after :doc:`napoleon <sphinx:usage/extensions/napoleon>` and :doc:`numpydoc
<numpydoc:index>` wherever :confval:`extensions` lists them: the extension types the reST fields they write as it
types the ones you write yourself.

*******************************
 Signatures you write yourself
*******************************

A signature you write yourself, in the directive as ``.. autofunction:: mod.f(x, y=3)`` or on the docstring's first line
with :confval:`autodoc_docstring_signature`, stays as written when it names other parameters than the object takes. The
extension replaces one with the same parameters, differing only in defaults or types, with the object's own, and does
the same for one made of ``*args`` and ``**kwargs`` alone, which autodoc falls back to when it can't see a class's
parameters. A class takes the parameters autodoc reads for it, those of its metaclass's :meth:`~object.__call__` ahead
of :meth:`~object.__new__` and :meth:`~object.__init__`, unless that :meth:`~object.__call__` only passes ``*args`` and
``**kwargs`` on.

.. mermaid::

    flowchart LR
        written["signature written in the directive<br/>or the docstring's first line"]
        same{"same parameters<br/>as the object?"}
        star{"only *args and **kwargs?"}
        keep["kept as written"]
        replace["replaced with the object's own signature"]
        written --> same
        same -- yes --> replace
        same -- no --> star
        star -- yes --> replace
        star -- no --> keep
        class written source
        class same,star extension
        class replace,keep output

*********************
 Types in the header
*********************

The header of a module variable, an attribute or a property shows its type after the name, ``RATE: Decimal``. Autodoc
writes that type itself, evaluating the annotation before any event runs, so a name imported under
:data:`~typing.TYPE_CHECKING`, the block only type checkers run, resolves there only when documenting something else
imported it first. The extension
renders that type again once Sphinx builds the header, the way it renders a field's type, with the type aliases,
:confval:`typehints_fully_qualified` and the :data:`~typing.TYPE_CHECKING` imports applied.
``RATE: decimal.Decimal`` therefore shows as ``RATE: Decimal``, as in the field, and a class from a module in
:confval:`autodoc_mock_imports` shows by its name.

***************************************
 Classes whose subscription is a no-op
***************************************

A class whose subscription hands back the class itself, as SQLAlchemy's ``TypeEngine`` does, evaluates
``TypeEngine[_T]`` to a bare ``TypeEngine``. The extension evaluates such an annotation again from its source, keeping
the arguments, so the header, the signature, the fields and the overloads show ``TypeEngine[_T]``, with ``TypeEngine``
still linked. The :meth:`~object.__init__` a :mod:`dataclass <dataclasses>` or :doc:`attrs <attrs:index>` class
generates has no source of its own, so its parameters take the annotations its fields write. A name that the branches of
an ``if`` annotate with different types keeps the bare class, as the source doesn't tell which branch ran.

*****************
 Type parameters
*****************

A generic function or class works with any type its caller picks, and names that type with a type parameter, ``T``.
Autodoc leaves the type parameters out of the signature, so the rendered ``first(items: T)`` doesn't say what ``T`` is.
The extension adds them after the name, each with its bound or constraints and its default, the way :pep:`695` writes
them, as in
``def first[T: Sized](items: T)``, ``class Stack[T]`` and ``type Pairs[K] = dict[K, K]``. A class made generic by
subclassing :class:`Generic[T] <typing.Generic>` shows its parameters the same way. An overload declaring its own,
``def get[S: str](self, key: S)``, renders them by name in its ``Overloads`` entry. A signature written by hand, such
as ``.. py:function:: first(items)``, shows only the type parameters it writes.

***************************************
 Members inherited from a generic base
***************************************

A member inherited from a generic base and documented under a subclass that binds the base's type parameters, as
``:inherited-members:`` lists it or ``.. automethod:: mod.Child.get`` names it, shows the arguments the subclass gives
them. With ``class Child(Base[int])``, ``Base.get(self) -> T`` documents as returning ``int`` under ``Child``, while
``Base.get`` keeps ``T``. The binding follows the bases through each level, so ``class C(B[int])`` over
``class B(A[list[U]])`` turns ``A``'s ``T`` into ``list[int]`` under ``C``:

.. mermaid::

    flowchart LR
        A["class A[T]<br/>def get(self) -> T"]
        B["class B[U](A[list[U]])<br/>T = list[U]"]
        C["class C(B[int])<br/>U = int"]
        R["C.get documents as<br/>get(self) -> list[int]"]
        A --> B --> C --> R
        class A,B,C source
        class R output

It covers the parameters and return types of methods and constructors, their overloads, the header of an attribute or
property, and the ``:vartype:`` a class-body annotation gives an ``:ivar:``. A :class:`~typing.TypedDict` binds the same
way, so ``class IntOptions(Options[int])`` shows the keys it inherits with ``int``, as does ``**kwargs:
Unpack[Options[int]]``. A type parameter the subclass leaves unbound, ``class Child(Base)``, stays as it is, and one it
passes on, ``class Child[U](Base[U])``, renders by name.

*******************************************
 Compared with Sphinx's built-in type hints
*******************************************

Autodoc reads annotations on its own. Its :confval:`autodoc_typehints` setting puts them in the signature
(``"signature"``, the default), in the description (``"description"``), in both, or nowhere (``"none"``).
:confval:`autodoc_typehints_description_target` picks the parameters that get a description field,
:confval:`autodoc_typehints_format` shows types by name or with their module, :confval:`autodoc_type_aliases` keeps
alias names, :confval:`autodoc_preserve_defaults` keeps defaults as written, :confval:`autodoc_use_type_comments` reads
:pep:`484` type comments, and :confval:`python_display_short_literal_types` shortens :data:`~typing.Literal`. Each part
of a type it writes is a cross-reference, and napoleon docstrings get their types as Sphinx-style fields do. When the
code imports every annotated name at runtime and the docstrings use Sphinx fields or napoleon, the built-in setting is
enough.

The table lists what changes when this extension takes over the description, each row checked by building one module
both ways, with ``autodoc_typehints = "description"`` alone and with this extension loaded.

.. list-table::
    :header-rows: 1
    :widths: 24 38 38

    * - Capability
      - ``autodoc_typehints = "description"``
      - This extension
    * - :ref:`Names imported under TYPE_CHECKING <type-checking>`
      - shows ``Decimal``, linked to the bare name, which resolves nowhere
      - links :class:`decimal.Decimal`
    * - :ref:`.pyi stubs <pyi-stubs>`
      - no types for a function the stub annotates
      - takes the types from the stub
    * - :ref:`how-to:Document overloads`
      - one signature line per overload, types in the signature
      - an ``Overloads`` field, or one signature line each with :confval:`typehints_use_signature`
    * - :ref:`how-to:Show default values`
      - in the signature only
      - also next to the type, with :confval:`typehints_defaults`
    * - :ref:`kwargs-unpack`
      - keyword fields without a type
      - each keyword typed from its :class:`~typing.TypedDict` entry, ``NotRequired[int]``
    * - :ref:`how-to:Use with numpydoc`
      - a second ``Parameters`` list holding the types
      - the types in numpydoc's own list
    * - :ref:`how-to:Control return types`
      - a ``Return type`` field, left out with ``autodoc_typehints_description_target = "documented"`` when nothing
        documents the return
      - also inside the ``Returns`` text, dropped, or dropped for ``None``
    * - :ref:`how-to:Write a custom formatter`
      - no hook; :confval:`autodoc_type_aliases` renames aliases only
      - :confval:`typehints_formatter` renders any annotation
    * - :ref:`Module rewriting <how-to:Qualify or rewrite module names>`
      - links the runtime path, ``pkg._impl.Window``
      - :confval:`typehints_fixup_module_name` rewrites it to ``pkg.Window``
    * - :ref:`how-to:Fix standard library cross-references`
      - ``_thread._local`` and ``concurrent.futures._base.Executor`` stay unresolved with intersphinx
      - links :class:`threading.local` and :class:`concurrent.futures.Executor`
    * - :ref:`reference:Deprecations`
      - nothing
      - a notice with the :func:`@deprecated <warnings.deprecated>` message
    * - :ref:`reference:Overrides`
      - nothing
      - an ``Overrides`` field linking the base class method
    * - :ref:`reference:Property setters`
      - the setter's type left out
      - a ``Setter accepts`` field with the setter's type
    * - ``Annotated[str, Doc("...")]``
      - the whole :data:`Annotated[...] <typing.Annotated>` as the type
      - ``str``, with the ``Doc`` text as the description
    * - :ref:`concepts:Type parameters`
      - left out of the signature
      - ``first[T: Sized]``, ``class Stack[T]``
    * - :ref:`Dataclass and attrs factories <how-to:Show default values>`
      - ``items=<factory>``
      - ``items=list()``

Both render :data:`Optional[str] <typing.Optional>` and :obj:`Union[int, str] <typing.Union>` with pipes on Python 3.14
and later, and the built-in setting does so on earlier versions too, where this extension needs
:confval:`always_use_bars_union`. Type comments, napoleon docstrings, ``autodoc_typehints_format = "fully-qualified"``
and an attribute annotated in :meth:`~object.__init__` come out the same either way.

Loaded next to this extension, the built-in setting at ``"description"`` or ``"both"`` adds the parameters a docstring
leaves out with types of its own; :ref:`how-to:Choose where types appear` shows how to leave the fields to this
extension.

The examples below show three of the rows. In each, the *sphinx-autodoc-typehints* tab renders the module with this
extension and the *Sphinx built-in* tab renders it with ``autodoc_typehints = "description"`` alone.

Overloads
=========

.. live-example::

    # load autodoc first, then this extension
    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import overload


    @overload
    def parse(text: str) -> int: ...
    @overload
    def parse(text: bytes) -> str: ...
    def parse(text: str | bytes) -> int | str:
        """
        Parse the text.

        :param text: the text
        """
        return 0 if isinstance(text, str) else ""

Keyword arguments from a ``TypedDict``
======================================

.. live-example::

    # load autodoc first, then this extension
    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import TypedDict, Unpack


    class Options(TypedDict, total=False):
        """The options of a run."""

        verbose: bool
        level: int


    def configure(**kwargs: Unpack[Options]) -> None:
        """
        Configure the run.

        :keyword verbose: print every step
        :keyword level: how much to print
        """

numpydoc docstrings
===================

.. live-example::

    # numpydoc writes the sections this extension types
    extensions = ["sphinx.ext.autodoc", "numpydoc", "sphinx_autodoc_typehints"]
    ---
    def format_unit(value: float, unit: str) -> str:
        """
        Format a value with its unit.

        Parameters
        ----------
        value
            a numeric value
        unit
            the unit, such as kg or m
        """
        return f"{value} {unit}"
