###############
 How-to guides
###############

Each guide changes one thing about the rendered docs and assumes you loaded the extension, as the :doc:`tutorials`
show. Each example documents a module ``demo`` with ``.. automodule:: demo`` and shows, in its tabs, the page this
extension renders and the page Sphinx renders without it. The :doc:`reference` lists every option, and :doc:`concepts`
explains what the extension does during a build.

***************************
 Choose where types appear
***************************

By default the types go into the fields below the signature, and the signature lists the names alone. Two options keep
them in the signature as well.

.. live-example::

    # keep the parameter types in the signature
    typehints_use_signature = True
    # keep the return type in the signature
    typehints_use_signature_return = True
    ---
    def format_unit(value: float, unit: str) -> str:
        """
        Format a value with its unit.

        :param value: a numeric value
        :param unit: the unit, such as kg or m
        """
        return f"{value} {unit}"

:confval:`typehints_formatter`, :confval:`typehints_fixup_module_name`, :confval:`typehints_fully_qualified` and
documented type aliases apply to the kept types as they do to the fields. Python's own spelling decides the rest. A
:class:`~typing.NewType`, a distinct name for an existing type, shows by its name, ``UserId`` where the field reads
``UserId (int)``. A :class:`~typing.TypeVar`, the placeholder a generic function fills with a concrete type, shows as
``~module.T`` when no signature declares it.

Sphinx's own :confval:`autodoc_typehints` setting, at ``"description"`` or ``"both"``, adds the parameters a docstring
leaves out, with types of its own, next to the ones this extension writes. Set it to ``"none"`` to leave the fields to
this extension; :ref:`concepts:Compared with Sphinx's built-in type hints` compares the two.

With :confval:`autoclass_content = "both" <autoclass_content>`, or the ``:class-doc-from: both`` option of an
:rst:dir:`autoclass` directive, Sphinx joins the class and constructor docstrings. A parameter either of them documents
gets its type there, and :confval:`always_document_param_types` adds the rest once, under the constructor docstring. The
constructor's overloads, the keys of ``**kwargs: Unpack[...]`` and a :pep:`727` ``Doc()`` description go there too,
while a :func:`@deprecated <warnings.deprecated>` notice heads the class docstring.

A class created inside a function can be documented when the module exports it:

.. code-block:: python

    def make_widget():
        class Widget:
            def resize(self, width: int) -> None:
                """Resize the widget."""

        return Widget

    Widget = make_widget()

The extension uses the exported ``Widget`` to identify ``resize`` as a method and leave ``self`` out of its signature.

*******************
 Use with napoleon
*******************

:doc:`sphinx.ext.napoleon <sphinx:usage/extensions/napoleon>` turns Google and NumPy style sections, such as ``Args:``
and ``Returns:``, into the fields Sphinx renders. The extension adds the types to those fields after napoleon writes
them, whichever order :confval:`extensions` lists the two in.

.. live-example::

    # napoleon writes the fields this extension types
    extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx_autodoc_typehints"]
    ---
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

Napoleon and this extension share one return type, and napoleon's ``:rtype:`` gives way to the annotation. Setting
:confval:`napoleon_use_rtype = False <napoleon_use_rtype>` makes napoleon put the docstring's type into the ``Returns``
text, so set :confval:`typehints_use_rtype = False <typehints_use_rtype>` as well, or the type shows twice; a type the
``Returns`` section writes then stays in place of the annotation's.

Turning :confval:`napoleon_use_param` or :confval:`napoleon_use_keyword` off makes napoleon list the parameters or the
keyword arguments in one combined field, and the types go in parentheses after each name. A type the docstring writes
there stays. The types napoleon's ``Attributes`` section would read from annotations come from this extension, see
:ref:`reference:Attributes`. ``napoleon_attr_annotations`` remains available at its configured boolean value to other
extensions.

*******************
 Use with numpydoc
*******************

:doc:`numpydoc <numpydoc:index>` renders NumPy style docstrings with its own section layout. The extension types the
``Parameters`` and ``Returns`` entries numpydoc writes rather than adding a second list, whichever order
:confval:`extensions` lists the two in.

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

        Returns
        -------
        str
            the value followed by its unit
        """
        return f"{value} {unit}"

The extension turns the ``Parameters``, ``Other Parameters``, ``Returns``, ``Yields`` and ``Raises`` sections numpydoc
writes into field lists first, then types them as it types Sphinx-style fields. An entry naming several parameters,
``a, b : int``, splits into one per name, and a type the docstring writes stays for a parameter without an annotation.
A ``:Parameters:`` field list written by hand, as docutils writes its own docstrings, stays as written, since numpydoc
sets each parameter name in bold and the extension takes a field without that markup for one written by hand.
A hand-written ``:Returns:`` field with a prose description stays as written too; use a NumPy ``Returns`` section when
the first indented line names a type.

**************************
 Document every parameter
**************************

A parameter the docstring doesn't mention gets no field, so its type shows nowhere.
:confval:`always_document_param_types` adds a field for each such parameter, holding its type.

.. live-example::

    # add a field for each parameter the docstring leaves out
    always_document_param_types = True
    ---
    def format_unit(value: float, unit: str, precision: int = 2) -> str:
        """
        Format a value with its unit.

        :param value: a numeric value
        """
        return f"{value:.{precision}f} {unit}"

The added fields follow the signature's order, next to the documented ones. With napoleon's combined ``Parameters`` or
``Keyword Arguments`` field, they join that field.

*********************
 Show default values
*********************

A default value shows in the signature only. :confval:`typehints_defaults` also writes it next to the parameter's
type in the field.

.. live-example::

    # show the default inside the parentheses that hold the type
    typehints_defaults = "braces"
    ---
    def format_unit(value: float, unit: str = "kg") -> str:
        """
        Format a value with its unit.

        :param value: a numeric value
        :param unit: the unit
        """
        return f"{value} {unit}"

``"comma"`` writes ``unit (str, default: 'kg')`` instead, and ``"braces-after"`` puts ``(default: 'kg')`` at the end
of the description, closing its last plain paragraph; a list, a directive or a literal block ending the description
stays as written. Both ``None``, the default, and ``False`` leave the defaults out of the docs. A parameter typed in
its docstring, by a ``:type:`` field, as ``:param int x:`` or in napoleon's combined field, gets its default next to
that type.

A :mod:`dataclass <dataclasses>` field declared with :func:`field(default_factory=list) <dataclasses.field>`, or an
attrs one with :func:`attrs.field(factory=list) <attrs.field>`, shows the call that builds its default, ``list()``, in
the signature and in the field. An attrs factory taking the instance reads ``make(self)``. A lambda keeps the
``<factory>`` placeholder, as the extension can't recover its source from the :meth:`~object.__init__` dataclasses
generate.

**********************
 Control return types
**********************

By default the return annotation becomes a *Return type* field after the parameter fields.
:confval:`typehints_use_rtype` moves it into the ``:return:`` text instead.

.. live-example::

    # write the return type into the Returns text instead of its own field
    typehints_use_rtype = False
    ---
    def format_unit(value: float, unit: str) -> str:
        """
        Format a value with its unit.

        :param value: a numeric value
        :param unit: the unit
        :return: the value followed by its unit
        """
        return f"{value} {unit}"

:confval:`typehints_document_rtype = False <typehints_document_rtype>` drops the return type, and
:confval:`typehints_document_rtype_none = False <typehints_document_rtype_none>` drops it only when it's ``None``.
:ref:`reference:How the return options combine` covers the cases these settings meet.

***************************
 Control how unions render
***************************

A union is a type that accepts any of several types. One written with the pipe, ``str | int``, renders that way. One
written as :obj:`Union[str, int] <typing.Union>` or :data:`Optional[str] <typing.Optional>` renders as written before
Python 3.14, unless :confval:`always_use_bars_union` is on.

.. live-example::

    # render Union[...] and Optional[...] with pipes
    always_use_bars_union = True
    ---
    from typing import Optional


    def find(name: Optional[str]) -> int:
        """
        Find a record.

        :param name: the name to look for
        """
        return 0

Python 3.14 merged :obj:`~typing.Union` with the pipe syntax, so there every union renders with pipes, whatever the
setting says. Before 3.14, a pipe next to a typing construct, ``Literal["a"] | None``, builds the object
:data:`Optional[...] <typing.Optional>` builds, so it renders like one unless :confval:`always_use_bars_union` is on.
:confval:`simplify_optional_unions`, on by default, flattens ``Optional[Union[A, B]]`` to ``Union[A, B, None]``; turned
off, a :obj:`Union[...] <typing.Union>` holding ``None`` shows as :data:`Optional[...] <typing.Optional>`. It has no
effect on Python 3.14, or on a union written with pipes.

*********************************
 Qualify or rewrite module names
*********************************

The extension shows a type by its name, ``Decimal``, linked to its full path, :class:`decimal.Decimal`.
:confval:`typehints_fully_qualified` shows the full path instead.

.. live-example::

    # show each type with its module
    typehints_fully_qualified = True
    ---
    from decimal import Decimal


    def total(prices: list[Decimal]) -> Decimal:
        """
        Add the prices up.

        :param prices: the prices
        """
        return sum(prices, Decimal())

The option follows Sphinx's :confval:`autodoc_typehints_format` unless you set it, so
``autodoc_typehints_format = "fully-qualified"`` turns it on.

Some libraries define a type under one module and document it under another. GTK's ``gi.repository.Gtk.Window`` appears
as ``Gtk.Window`` in its docs, so a link to the runtime path finds no target in the inventory :doc:`intersphinx
<sphinx:usage/extensions/intersphinx>`, the Sphinx extension that resolves references against another project's docs,
loads for GTK. :confval:`typehints_fixup_module_name` rewrites the module before the extension builds the link.

.. code-block:: python

    # link gi.repository.Gtk.Window to Gtk.Window
    def fixup_module_name(module: str) -> str:
        return module.removeprefix("gi.repository.")


    typehints_fixup_module_name = fixup_module_name

Sphinx can't store a function in its cached environment, so the extension compares the function's source to tell an edit
apart; editing it re-reads every document on the next incremental build. A change to a helper the function calls, or to
data it reads, goes unseen, so run ``sphinx-build -E`` after one. A :func:`functools.partial` or a callable instance has
no source to compare, so each build re-reads every document; assign a plain function to keep builds incremental.

**************************
 Write a custom formatter
**************************

To show a type other than the extension would, such as a project-specific name for a common type, set
:confval:`typehints_formatter`. It receives each annotation and the Sphinx :class:`~sphinx.config.Config`, and returns
the :doc:`reStructuredText <sphinx:usage/restructuredtext/index>` to show, or ``None`` to fall back to the default
rendering. The text may use :doc:`roles <sphinx:usage/restructuredtext/roles>`, reST's markup for a cross-reference,
such as ``:class:`bool```.

.. live-example::

    # show bool as a plain word
    def format_bool(annotation, config):
        return "boolean" if annotation is bool else None


    typehints_formatter = format_bool
    ---
    def toggle(flag: bool, times: int) -> bool:
        """
        Flip the flag.

        :param flag: the flag
        :param times: how often to flip it
        """
        return flag ^ (times % 2 == 1)

With :confval:`typehints_use_signature` or :confval:`typehints_use_signature_return`, the formatter decides the types
kept in the signature too, where a role becomes the name it refers to, so ``:class:`bool``` turns into ``bool``.
Set :confval:`typehints_formatter_pass_context` when the same type needs different wording in a parameter and a return
field. The formatter then receives a third argument naming the kind of field:

.. live-example::

    typehints_formatter_pass_context = True

    def format_str(annotation, config, kind=None):
        if annotation is str and kind == "parameter":
            return "input text"
        if annotation is str and kind == "return":
            return "result text"
        return None

    typehints_formatter = format_str
    ---
    def normalize(value: str) -> str:
        """Normalize text.

        :param value: the text to normalize
        """

Changing the formatter rereads the documents in an incremental build. A value that is not callable stops the build
with a :class:`~sphinx.errors.ConfigError`.

*******************
 Link type aliases
*******************

A type alias gives a type a name, as the :pep:`695` ``type`` statement ``type Vector = list[float]`` does. An alias with
a :rst:dir:`py:type` entry in the docs, which :rst:dir:`automodule` writes for one it documents, renders by its name and
links to that entry. Without the entry the annotation expands to the type it stands for.

.. live-example::

    # the defaults cover this
    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    type Vector = list[float]
    """Coordinates along each axis."""


    def scale(vector: Vector, factor: float) -> Vector:
        """
        Scale a vector.

        :param vector: the vector
        :param factor: the factor
        """
        return [item * factor for item in vector]

The entry has to name the alias where the annotation looks it up. ``.. py:type:: pkg.Vector`` serves the functions of
``pkg``, and an alias documented in a submodule such as ``pkg.compat`` does not. The extension picks between the alias
and the type it stands for once Sphinx has read every document, so the entry may come after the function or sit in
another document, and ``-j`` doesn't change the result. Sphinx writes a signature that
:confval:`typehints_use_signature` keeps while it still reads documents, so that signature names the alias only when
Sphinx read the entry first.

A submodule's own ``Vector`` takes precedence over an alias with that name documented in its parent package. If the
submodule's alias has no entry, its type appears instead. This also applies when an ``if TYPE_CHECKING:`` block binds
the name only for annotations. Import the parent's alias into the submodule when its functions should link to the
parent's entry.

A plain assignment, ``Count = int``, evaluates to the type it names, so without ``from __future__ import annotations``
the extension reads the function's source to tell ``limit: Count`` from ``limit: int``. A function without source, such
as a generated one, shows the type the alias names. An alias in :confval:`autodoc_type_aliases` renders by its name and
links to the target it names when the docs document that target; otherwise the name shows as plain text, so the value
may be a display string too.

A recursive alias, ``type Json = dict[str, Json] | list[Json] | str``, renders its self-reference as a link to its
name. This also works when the alias appears in a callable's parameter list, such as
``type Callback = Callable[[Callback], None]``. A generic alias used with arguments, ``Pairs[int]``, expands with the
arguments in place, or shows by name when they don't fit its parameters.

.. _kwargs-unpack:

**************************************************
 Document ``**kwargs`` with ``Unpack[TypedDict]``
**************************************************

A :class:`~typing.TypedDict` declares the keys of a dictionary and the type of each. Annotating ``**kwargs`` with
:data:`Unpack[Options] <typing.Unpack>` says the function takes those keys as keyword arguments (:pep:`692`). Without
help, the keyword fields show no type. The extension gives each keyword argument the docstring names the type of its
:class:`~typing.TypedDict` entry.

.. live-example::

    # napoleon gives the keyword arguments a section of their own
    extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon", "sphinx_autodoc_typehints"]
    # add a keyword field for each TypedDict entry the docstring leaves out
    always_document_param_types = True
    ---
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

A caller may leave ``level`` out, so it reads ``NotRequired[int]``, and a :data:`~typing.ReadOnly` entry keeps its
:data:`ReadOnly[...] <typing.ReadOnly>`. An entry described through ``Annotated[..., Doc(...)]`` gets a keyword field of
its own without the setting.

********************
 Document overloads
********************

An :func:`@overload <typing.overload>` declares one signature of a function for type checkers, such as ``str`` in,
``int`` out; the undecorated definition after the overloads is the one that runs. Autodoc shows that definition, whose
``str | bytes`` parameter hides which input gives which result. The extension lists the overloads in an ``Overloads``
field.

.. live-example::

    # on by default, False drops the Overloads field
    typehints_document_overloads = True
    ---
    from typing import overload


    @overload
    def parse(text: str, /, *, strict: bool = ...) -> int: ...
    @overload
    def parse(text: bytes) -> str: ...
    def parse(text: str | bytes, /, *, strict: bool = False) -> int | str:
        """Parse the text."""
        return 0 if isinstance(text, str) else ""

Each overload reads like its signature, with its ``/`` and ``*`` markers, the stars of ``*args`` and ``**kwargs``, and
its defaults as written; an overload taking nothing shows as ``()``. The field leaves out ``self`` and ``cls`` and goes
right after the summary paragraph, so :doc:`autosummary <sphinx:usage/extensions/autosummary>` still picks the summary
up. A function documented through its overloads gets no return type, as each overload states its own. A class lists
the overloads of its :meth:`~object.__init__` or :meth:`~object.__new__`, whichever directive documents it.

Write ``:no-overloads:`` in a docstring to drop the field for that function alone; the extension strips the marker
from the output, also with :confval:`typehints_document_overloads` off.

With :confval:`typehints_use_signature = True <typehints_use_signature>` the overloads replace the signature instead,
one line each, and the field goes away. Each line shows its return type, as that's what tells overloads apart, except
for a class, whose lines list its constructor's parameters. A default an overload writes as ``...`` stays ``...``: it
marks the parameter optional, while the implementation's default may be a value the overload's type rules out, as
``True`` for ``flag: Literal[False] = ...``. Only the first line is the link target. A signature written in the
directive, ``.. autofunction:: f(x)``, stays as written and keeps the overloads in the field, while ``:no-overloads:``
keeps the implementation's signature.

.. _type-checking:

****************************************************
 Document code that imports under ``TYPE_CHECKING``
****************************************************

:data:`~typing.TYPE_CHECKING` is ``False`` when the code runs and ``True`` for a type checker, so an import under
``if TYPE_CHECKING:`` costs nothing at runtime. The imported name doesn't exist when Sphinx evaluates the annotation, so
it shows as plain text, and Sphinx's :confval:`nitpicky` mode warns about it. The extension runs the module's
:data:`~typing.TYPE_CHECKING` blocks during the build, so annotations naming what they import resolve and link.

.. live-example::

    # silence the warning a guarded import that fails raises
    suppress_warnings = ["sphinx_autodoc_typehints.guarded_import"]
    ---
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

Two modules that import each other's types work the same way. Guard the import, and add :mod:`from __future__ import
annotations <__future__>` so Python keeps each annotation as a string, a forward reference, rather than evaluating it at
import time.

Any module-level guard counts, whether it names :data:`~typing.TYPE_CHECKING` or ``t.TYPE_CHECKING``, takes the ``else``
branch of ``if not TYPE_CHECKING:``, or joins the test to others with ``and`` or ``or``. Annotations read the names as a
type checker does, so with ``else: ArrayLike = Any`` they show the guarded ``ArrayLike``. The module itself stays as it
is at runtime. The fallback stays for your code and for autodoc, and a name only the block binds, such as a
:class:`~typing.Protocol` defined there, doesn't become a member :rst:dir:`automodule` lists.
An ``and False`` guard skips its body even when ``TYPE_CHECKING`` is true.

When the block imports a dependency the docs environment lacks, the extension mocks it the way
:confval:`autodoc_mock_imports` would, so its types still render as references; install it when you want those
references to resolve. An import that fails for another reason, such as a dependency that raises on import, warns under
``sphinx_autodoc_typehints.guarded_import``. When the module's source does not parse as a whole, as with one a custom
loader compiles from another language, the extension reads each guard on its own, and a guard that doesn't parse warns
too. A guarded statement only a type checker accepts, and that imports nothing, goes by without a warning, and the
names it would define still work in annotations.

.. _pyi-stubs:

*******************************************
 Document C extensions with ``.pyi`` stubs
*******************************************

A function from a compiled C extension carries no annotations, so its fields show no types. A `.pyi stub file
<https://typing.python.org/en/latest/spec/distributing.html#stub-files>`_ holds the signatures and annotations of such a
module for type checkers, and the extension reads it. Place one next to the ``.so`` or ``.pyd`` file, or as
``__init__.pyi`` in the package directory, and functions without annotations take their types from it.

- A function a package re-exports from a native submodule, ``pkg._native.parse`` exposed as ``pkg.parse``, takes its
  types from the package's ``__init__.pyi``. A native submodule without a :attr:`~module.__file__`, as PyO3 builds them,
  finds its stub too.
- A function whose stub imports it from another stub, as ``attrs/__init__.pyi`` does with ``from attr import asdict as
  asdict``, takes its types from that stub.
- The :func:`@overload <typing.overload>` variants of a stub combine into a union, unless the stub also gives the
  implementation's signature.
- The extension follows ``if sys.version_info`` and ``if sys.platform`` branches for the running interpreter.
- A name only the stub defines, including a :data:`~typing.TypeAlias` or ``type`` alias, renders as a reference.
- A module the stub imports that isn't installed, ``import numpy.typing as npt`` without numpy, gets mocked as
  :confval:`autodoc_mock_imports` would, so ``npt.NDArray`` still renders as a reference.
- A C attribute, a getset or member descriptor, takes its type from the stub's :class:`@property <property>` or class
  annotation.
- Editing a stub re-reads the pages documenting what it describes on the next incremental build.
- Looking for a stub reads a package's attributes without running its :pep:`562` ``__getattr__``, so a package that
  imports on first access, or renames what it hands out as anyio does, stays as autodoc found it.

***************************
 Use PEP 484 type comments
***************************

A function without annotations can carry its types in a :pep:`type comment <484#type-comments>`, the ``# type:``
syntax from before Python 3 supported annotations everywhere.

.. live-example::

    # the defaults cover this
    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    def scale(value, factor):
        # type: (float, int) -> float
        """
        Scale a value.

        :param value: the value
        :param factor: the factor
        """
        return value * factor

The per-argument form, a ``# type:`` comment after each parameter, works too, and the comment may leave out ``self`` or
``cls``. A comment that doesn't parse warns under ``sphinx_autodoc_typehints.comment``.

***************************************
 Fix standard library cross-references
***************************************

A link to some standard library classes leads nowhere, because the class reports a module other than the one its docs
use. :class:`threading.local` reports its module as ``_thread._local``, and :class:`concurrent.futures.Executor` reports
``concurrent.futures._base.Executor`` as its path. A link built from those paths finds no target. Load :doc:`intersphinx
<sphinx:usage/extensions/intersphinx>` and the extension maps each runtime path to the documented one, read from the
inventories intersphinx loads.

The extension imports a module an inventory lists only when an annotation names a class an entry in that module shares
its name with, so mapping the inventory of a large library such as numpy doesn't import the library. A class the docs
list under another name, such as ``threading.local`` for ``_thread._local``, maps once its documented module is
imported, which the code annotating with it has usually done already.

.. code-block:: python

    # load intersphinx so the extension can read the documented paths
    extensions = ["sphinx.ext.autodoc", "sphinx.ext.intersphinx", "sphinx_autodoc_typehints"]
    # the inventory of the Python docs
    intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

Without intersphinx the extension still relocates the classes Sphinx itself knows about, such as :class:`pathlib.Path`,
which lives in ``pathlib._local`` from Python 3.13 on.

*******************
 Silence a warning
*******************

Name the warning's category in Sphinx's :confval:`suppress_warnings`:

.. code-block:: python

    # silence every warning this extension raises
    suppress_warnings = ["sphinx_autodoc_typehints"]

:ref:`reference:Warnings` lists each category with its cause and fix.
