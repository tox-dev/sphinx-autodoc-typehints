###########
 Reference
###########

***********************
 Configuration options
***********************

Set these in ``conf.py``. Sphinx re-reads every document when an option whose *Rebuild* is ``env`` changes; a change
to an option without a *Rebuild* field leaves the cached documents as they are.

.. confval:: always_document_param_types
    :default: ``False``
    :rebuild: ``env``

    Add a field for each parameter the docstring leaves out. See :ref:`how-to:Document every parameter`.

.. confval:: always_use_bars_union
    :default: ``False``
    :rebuild: ``env``

    Render :obj:`~typing.Union` and :data:`~typing.Optional` with pipes; Python 3.14 does so regardless. See
    :ref:`how-to:Control how unions render`.

.. confval:: simplify_optional_unions
    :default: ``True``
    :rebuild: ``env``

    Flatten ``Optional[Union[A, B]]`` to ``Union[A, B, None]`` before Python 3.14. See :ref:`how-to:Control how unions
    render`.

.. confval:: typehints_defaults
    :default: ``None``
    :rebuild: ``env``

    Show defaults in the ``"comma"``, ``"braces"`` or ``"braces-after"`` style; ``None`` or ``False`` hides them. See
    :ref:`how-to:Show default values`.

.. confval:: typehints_document_overloads
    :default: ``True``
    :rebuild: ``env``

    List the :func:`@overload <typing.overload>` signatures a function declares for type checkers in an ``Overloads``
    field. See :ref:`how-to:Document overloads`.

.. confval:: typehints_document_rtype
    :default: ``True``
    :rebuild: ``env``

    Add the return type to the output. See :ref:`how-to:Control return types`.

.. confval:: typehints_document_rtype_none
    :default: ``True``
    :rebuild: ``env``

    Add the return type when it's ``None``; :ref:`reference:How the return options combine` lists the cases.

.. confval:: typehints_fixup_module_name
    :default: ``None``
    :rebuild: ``env``

    Rewrite a module path before the extension builds a link. See :ref:`how-to:Qualify or rewrite module names`.

.. confval:: typehints_formatter
    :default: ``None``

    Called with each annotation and the Sphinx config, it returns the reST to show, or ``None`` to render the
    annotation as the extension would without it. An empty string hides the type: docstring fields leave it out, a
    field that holds only the type, such as ``Return type``, is dropped, and signatures and headers show the name
    without an annotation. See :ref:`how-to:Write a custom formatter`.

    The ``annotation`` a formatter receives is a class or :mod:`typing` construct, a :class:`~typing.NewType`, a
    :class:`~typing.TypeAliasType`, a :class:`~typing.ForwardRef` or a string for an annotation that failed to
    evaluate, the placeholder Sphinx makes for a name in :confval:`autodoc_type_aliases`, ``None``, or a list or
    tuple of these, as the parameters of a :class:`~collections.abc.Callable` are.

.. confval:: typehints_fully_qualified
    :default: ``False``
    :rebuild: ``env``

    Show each type with its module; follows :confval:`autodoc_typehints_format` unless set. See :ref:`how-to:Qualify
    or rewrite module names`.

.. confval:: typehints_use_rtype
    :default: ``True``
    :rebuild: ``env``

    Give the return type its own field; ``False`` writes it into the ``:return:`` text. See :ref:`how-to:Control return
    types`.

.. confval:: typehints_use_signature
    :default: ``False``
    :rebuild: ``env``

    Keep the parameter types in the signature. See :ref:`how-to:Choose where types appear`.

.. confval:: typehints_use_signature_return
    :default: ``False``
    :rebuild: ``env``

    Keep the return type in the signature. See :ref:`how-to:Choose where types appear`.

A :confval:`typehints_defaults` outside ``"comma"``, ``"braces"``, ``"braces-after"``, ``None`` and ``False``, or a
:confval:`typehints_formatter` that isn't callable, stops the build with a :class:`~sphinx.errors.ConfigError` before
Sphinx reads any document.

**********
 Warnings
**********

Every warning carries the type ``sphinx_autodoc_typehints`` and a subtype; :confval:`suppress_warnings` takes either. A
guarded import is one inside an ``if TYPE_CHECKING:`` block, which only type checkers run, and a forward reference is
an annotation Python keeps as a string to evaluate later.

.. list-table::
    :header-rows: 1
    :widths: 30 45 25

    * - Category
      - Cause
      - Fix
    * - ``sphinx_autodoc_typehints``
      - Any of the warnings below
      - Suppress it to silence them all
    * - ``sphinx_autodoc_typehints.comment``
      - A type comment doesn't parse, or lists fewer types than the function has parameters
      - Correct the comment, or replace it with annotations
    * - ``sphinx_autodoc_typehints.forward_reference``
      - An annotation names something undefined or isn't valid Python; it shows as written
      - Define or import the name, under :data:`~typing.TYPE_CHECKING` if need be
    * - ``sphinx_autodoc_typehints.guarded_import``
      - A :data:`~typing.TYPE_CHECKING` import fails for a reason other than an absent dependency, or a guard doesn't
        parse
      - Fix the docs environment so the import runs
    * - ``sphinx_autodoc_typehints.local_function``
      - The extension can't process a method of a class defined inside a function
      - Wrap a decorator's wrapper with :func:`functools.wraps`
    * - ``sphinx_autodoc_typehints.multiple_ast_nodes``
      - The source of a function without annotations parses to more than one definition, so its type comment can't be
        read
      - Define the function with ``def`` on lines of its own

*******************
 Typing constructs
*******************

The table shows how a field renders each annotation, every name linked to its documentation. A generic type, such as
``list[T]``, takes type parameters: placeholders such as :class:`~typing.TypeVar` ``T`` that a use fills with a concrete
type. A sentinel, :pep:`661`, is a unique marker value such as ``MISSING`` that stands for an argument left out. The
:doc:`typing` renders a module for each feature. The table evaluates the annotations in this namespace:

.. code-block:: python

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
        TypedDict,
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


    class Options(TypedDict):
        verbose: bool


    type Vector = list[float]
    type Pairs[K] = dict[K, K]

.. list-table::
    :header-rows: 1
    :widths: 34 26 30 10

    * - Construct
      - Annotation
      - Rendered
      - Python
    * - union written with pipes
      - ``int | None``
      - ``int | None``
      -
    * - :data:`~typing.Optional`
      - ``Optional[int]``
      - ``Optional[int]``
      - ``<3.14``
    * - :data:`~typing.Optional`
      - ``Optional[int]``
      - ``int | None``
      - ``3.14+``
    * - :obj:`~typing.Union`
      - ``Union[int, str]``
      - ``Union[int, str]``
      - ``<3.14``
    * - :obj:`~typing.Union`
      - ``Union[int, str]``
      - ``int | str``
      - ``3.14+``
    * - pipe next to a typing construct
      - ``Literal["a"] | None``
      - ``Optional[Literal['a']]``
      - ``<3.14``
    * - pipe next to a typing construct
      - ``Literal["a"] | None``
      - ``Literal['a'] | None``
      - ``3.14+``
    * - :data:`~typing.Literal`
      - ``Literal["a", "b"]``
      - ``Literal['a', 'b']``
      -
    * - :data:`~typing.Literal` of an :class:`~enum.Enum` member, linked to the member, or to its enum when the member
        has no entry
      - ``Literal[Color.RED]``
      - ``Literal[Color.RED]``
      -
    * - :class:`~collections.abc.Callable`
      - ``Callable[[int, str], bool]``
      - ``Callable[[int, str], bool]``
      -
    * - :class:`~collections.abc.Callable` taking any arguments
      - ``Callable[..., bool]``
      - ``Callable[..., bool]``
      -
    * - :class:`~typing.ParamSpec`
      - ``Callable[P, int]``
      - ``Callable[P, int]``
      -
    * - :data:`~typing.Concatenate`
      - ``Callable[Concatenate[int, P], int]``
      - ``Callable[Concatenate[int, P], int]``
      -
    * - :class:`~typing.ParamSpec` components
      - ``P.args``
      - ``P.args``
      -
    * - :class:`~typing.TypeVar` no signature declares
      - ``T``
      - ``T``
      -
    * - :class:`~typing.TypeVar` with a bound, which its own entry shows
      - ``B``
      - ``B``
      -
    * - :class:`~typing.TypeVar` with constraints, which its own entry shows
      - ``C``
      - ``C``
      -
    * - :class:`~typing.TypeVarTuple`
      - ``tuple[*Ts]``
      - ``tuple[*Ts]``
      -
    * - :data:`~typing.Unpack` of a :class:`~typing.TypeVarTuple`, the same object as ``*Ts``
      - ``Unpack[Ts]``
      - ``*Ts``
      -
    * - unpacked tuple
      - ``tuple[int, *tuple[str, ...]]``
      - ``tuple[int, *tuple[str, ...]]``
      -
    * - :data:`~typing.Unpack` of a :class:`~typing.TypedDict`, for ``**kwargs``, which has no star form
      - ``Unpack[Options]``
      - ``Unpack[Options]``
      -
    * - :class:`~typing.NewType`, with the type it wraps
      - ``UserId``
      - ``UserId (int)``
      -
    * - :data:`~typing.Annotated`, metadata dropped
      - ``Annotated[int, "meta"]``
      - ``int``
      -
    * - empty tuple
      - ``tuple[()]``
      - ``tuple[()]``
      -
    * - variable-length tuple
      - ``tuple[int, ...]``
      - ``tuple[int, ...]``
      -
    * - :class:`~types.NoneType`
      - ``type(None)``
      - ``None``
      -
    * - class from the :mod:`types` module
      - ``ModuleType``
      - ``ModuleType``
      -
    * - dataclass :class:`~dataclasses.InitVar`
      - ``InitVar[int]``
      - ``InitVar[int]``
      -
    * - :class:`~typing.TypedDict` qualifier
      - ``NotRequired[int]``
      - ``NotRequired[int]``
      -
    * - ``typing_extensions`` backport, linked to ``typing``
      - ``Self``
      - ``Self``
      -
    * - :pep:`661` sentinel, linked as module data
      - ``MISSING``
      - ``MISSING``
      -
    * - ``type`` alias without a :rst:dir:`py:type` entry
      - ``Vector``
      - ``list[float]``
      -
    * - generic ``type`` alias with arguments
      - ``Pairs[int]``
      - ``dict[int, int]``
      -

A name shows without its module unless :confval:`typehints_fully_qualified` is on. A type parameter a signature
declares, as ``def first[T: Sized](items: T)`` or ``class Box(Generic[T])`` does, renders by name, ``T``, with its bound
in the signature, and ``P.args`` renders as ``P.args``. A type variable defined at module level, as
``T = TypeVar("T")``, renders by name too, linked to its own entry when the docs document it, which shows its bound or
constraints, and so does ``P`` in ``P.args``. A ``Doc(...)`` in :data:`~typing.Annotated` metadata becomes the
parameter's description. Sphinx's :confval:`python_display_short_literal_types` renders ``Literal["a", "b"]`` as
``'a' | 'b'``. A class from a module in :confval:`autodoc_mock_imports`, subscripted or not, renders by its name.
Trailing arguments equal to their type parameter's :pep:`696` default are left out, so ``typing.ContextManager[None]``
renders as written, though from Python 3.13 it carries its second argument's default. An argument written out that
equals its default goes too, ``Generator[int, None, None]`` rendering as ``Generator[int]``, as type checkers read the
two the same.

The same rendering applies to the header autodoc writes for data, an attribute or a property, so
``count: Annotated[int, ...]`` shows as ``count: int`` there. A header written by hand, such as ``.. py:data:: demo.x``
with a ``:type:`` option, keeps its type as written. Each type the extension adds sits in an inline element with the
CSS class ``sphinx_autodoc_typehints-type``, for a theme or stylesheet to target.

A value the extension writes, such as ``'fill'`` of ``Literal["fill", 1, None]``, a default, or ``None`` in ``int |
None`` or a return type, takes the colors of the project's :confval:`pygments_style`, and of ``pygments_dark_style`` for
a theme such as furo that has one, the way a code block does. Each value sits in an inline element with the CSS classes
``highlight`` and ``sphinx_autodoc_typehints-value``, and each of its tokens carries the Pygments class a code block
would give it, as ``s1`` for a string or ``kc`` for ``None``. The stylesheet ``sphinx_autodoc_typehints.css`` the
extension adds keeps the block background, border and padding of ``.highlight`` off these values and sets no color of
its own.

*****************
 Object features
*****************

Beyond parameters and return types, the extension adds fields for decorators and properties, for
:class:`~typing.TypedDict` classes and :mod:`dataclasses`, and for attributes.

.. live-example::

    # the defaults cover this
    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
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

Deprecations
============

A function, method or class decorated with :func:`@warnings.deprecated <warnings.deprecated>`, :pep:`702`, or its
`typing_extensions <https://typing-extensions.readthedocs.io/>`_ backport, gets a notice below its summary, styled like
Sphinx's :rst:dir:`deprecated` directive. The message shows as written, without markup, since it's the text the object
warns with at runtime. A docstring with a ``.. deprecated::`` directive of its own, which can name the version, gets no
second notice, and the extension doesn't mark a subclass of a deprecated class.

Overrides
=========

A method or property marked with :func:`@typing.override <typing.override>` gets an ``Overrides`` field linking the
member it replaces, in the nearest base class that defines it. A method no base class defines gets no field. Listed
under a subclass with ``:inherited-members:``, the method still links what it overrides in its own class's bases, and
the link goes through :confval:`typehints_fixup_module_name` like any other.

Property setters
================

Autodoc puts the type a property's getter returns in its header. When the setter's value parameter has another
annotation, the property gets a ``Setter accepts`` field with it. A :class:`property` without a setter, such as a
:func:`functools.cached_property`, a setter annotated with the getter's type, or one without an annotation gets no
field, and a docstring with a ``:Setter accepts:`` field of its own keeps it.

.. _typeddict-classes:

``TypedDict`` classes
=====================

A :class:`~typing.TypedDict` documented with ``:members:`` lists its keys as attributes; keys without a docstring need
``:undoc-members:``. Keys a caller may leave out show as :data:`NotRequired[...] <typing.NotRequired>`, also when the
class's ``total=False`` makes them so, and keys a caller must pass show their type alone, also when written as
:data:`Required[...] <typing.Required>`. A :pep:`705` :data:`~typing.ReadOnly` entry keeps its :data:`ReadOnly[...]
<typing.ReadOnly>`, inside :data:`NotRequired[...] <typing.NotRequired>` as the typing spec nests them. The items a
:pep:`728` :class:`~typing.TypedDict` accepts beyond its keys show in an ``Extra items`` field; a ``closed=True`` class,
or one inheriting from it, shows :data:`~typing.Never`, its equivalent. A docstring with its own ``:Extra items:`` field
keeps it.

Attributes
==========

An attribute annotated in the class body, or where :meth:`~object.__init__` assigns it, gets its type in the ``:ivar:``,
``:cvar:`` or ``:var:`` field that documents it. A :data:`ClassVar[...] <typing.ClassVar>` or :data:`Final[...]
<typing.Final>` shows the type it holds, and where both declare an attribute, the :meth:`~object.__init__` annotation
wins. Assignments inside ``if``, ``try`` and ``with`` blocks count, ones in nested functions don't, and an ``:ivar int
retries:`` or a ``:vartype retries:`` of its own stays as written.

With napoleon, the extension types the entries of an ``Attributes`` section the same way. That covers a class's
attributes annotated in the class body or where :meth:`~object.__init__` assigns them, and a module's annotated at
module level, whether napoleon writes them as ``:ivar:`` fields or, with :confval:`napoleon_use_ivar` off, as ``..
attribute::`` entries. A type the docstring writes itself, such as the ``int`` of ``count (int): ...``, takes precedence
over the annotation. With :confval:`napoleon_attr_annotations` off, napoleon's entries take no type from annotations, as
napoleon would give them none; an attribute annotated where :meth:`~object.__init__` assigns it still gets its type in
napoleon's ``:ivar:`` fields, and so does an ``:ivar:`` field or ``.. attribute::`` entry the docstring writes itself.

The extension takes the annotations of :doc:`attrs <attrs:index>` fields from attrs' metadata, and those of
:mod:`dataclass <dataclasses>` fields from the class body. Autodoc skips a field without a docstring unless the
directive has ``:undoc-members:``.

Generators
==========

A function annotated to return a :class:`~collections.abc.Generator`, :class:`~collections.abc.Iterator`,
:class:`~collections.abc.AsyncGenerator` or :class:`~collections.abc.AsyncIterator` whose docstring
has a ``Yields`` section, ``:Yields:``, ``:yields:`` or ``:yield:`` as napoleon and numpydoc write it, gets no return
type. The yielded type goes into that section instead, unless it states one. A generator that also hands back a value
with ``return``, ``Generator[int, None, bool]``, and documents it in a ``Returns`` section gets that value's type,
``bool``, as its return type. Wrapping the annotation in :data:`~typing.Annotated` changes none of this.

**************************
 Parameter matching rules
**************************

The extension adds a type to the parameters that already have a field in the docstring. A parameter whose annotation
carries a ``Doc(...)`` description gets a field of its own, the entries of napoleon's combined parameter field get
their types in place, and :confval:`always_document_param_types` adds the rest.

The extension reads parameters from the ``:param``, ``:parameter``, ``:arg``, ``:argument``, ``:keyword``, ``:kwarg``
and ``:kwparam`` fields. A field may name ``*args`` and ``**kwargs`` bare or with escaped stars, as ``args`` or
``\*args``. Only a field that starts a line counts, and one indented into a literal block, a code block or a directive
such as a note stays as written. A type in the field, ``:param int x:``, and a ``:type x:`` field give way to the
annotation, and a parameter without one keeps its docstring type. A keyword argument napoleon writes as a
``:keyword:`` field gets a ``:paramtype:`` next to it, and a ``:kwtype:`` napoleon wrote from the docstring counts as a
type the docstring states.

Some objects take their annotations from another object:

- a decorated function, from its ``__wrapped__``
- a class or function stating its signature in ``__signature__``, as a pydantic model does, from that signature
- a :func:`functools.partial` or :class:`~functools.partialmethod`, from the function it calls, without the bound
  arguments
- a callable instance documented as a function or method, from its :meth:`~object.__call__`

A :func:`@typing.no_type_check <typing.no_type_check>` function still gets its types. A data or attribute entry holding
a callable gets no parameter or return types, as it documents a value. An annotation that fails to evaluate shows as
written, whatever its own code raises; it warns under ``sphinx_autodoc_typehints.forward_reference`` only when it names
something undefined or isn't valid Python.

********************************
 How the return options combine
********************************

.. list-table::
    :header-rows: 1
    :widths: 25 25 50

    * - :confval:`typehints_document_rtype`
      - :confval:`typehints_use_rtype`
      - Result
    * - ``True``
      - ``True``
      - The return type gets its own field after the parameter fields
    * - ``True``
      - ``False``
      - The return type opens the ``:return:`` text, or gets its own field when there's no ``:return:``
    * - ``False``
      - either
      - No return type from the annotation; an ``:rtype:`` the docstring writes stays

:confval:`typehints_document_rtype_none = False <typehints_document_rtype_none>` hides a ``None`` return type in each
of these, and ``Annotated[None, Doc(...)]`` keeps its description without the type. With
:confval:`typehints_use_rtype = False <typehints_use_rtype>`, a ``:return:`` that already states its type, such as
napoleon's ``*int* -- the value``, stays as it is; a description that only contains a ``--``, such as ``the value --
or None when missing``, still gets the type. Next to an ``:rtype:`` field, which the annotation replaces, the
``:return:`` text counts as a description.

Classes and constructors get no return type, and a property shows its type in its header. An ``:rtype:`` the docstring
writes, over one line or several, gives way to the annotation. The separate field goes after the parameter fields,
before the first directive or other block that follows them, or at the end. A return annotation carrying a
``Doc(...)`` description adds a ``:return:`` field when the docstring has none.
