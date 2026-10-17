##########################
 Typing features gallery
##########################

Each entry below names a feature of Python's type system, the Python version it needs, and shows how the extension
renders a module that uses it. The :mod:`typing` module documents each feature, and the :pep:`PEPs <0>` listed with
them give the details. The extension runs on Python 3.12 and later, so a feature that Python added before 3.12 works on
every version it supports. A feature that needs a later Python often has a backport in `typing_extensions
<https://typing-extensions.readthedocs.io/>`_, a package that brings new :mod:`typing` names to older versions; the
entry says so where one exists.

The examples render while these docs build, on Python 3.15. Each shows its source, the page this extension builds, and
the page Sphinx builds with :confval:`autodoc_typehints = "description" <autodoc_typehints>` alone. The
:ref:`reference:Typing constructs` table lists the rendering of each construct in one place.

The ``conf.py`` button in the corner of each rendered page opens the :doc:`configuration options <reference>` that
change how types render. A choice there applies to every example on the page, shows the ``conf.py`` lines it takes, and
stays for your next visit. The docs build renders each combination ahead of time.

.. live-example-picker::
    :reference: reference

    Names
        Full module paths: typehints_fully_qualified = False, True
    Containers and unions
        Modern spelling: typehints_modernize_annotations = False, True
    Signature
        Parameter types in the signature: typehints_use_signature = False, True
        Return type in the signature: typehints_use_signature_return = False, True
    Defaults
        Default value style: typehints_defaults = None, "comma", "braces", "braces-after"
    Return type
        Document the return type: typehints_document_rtype = True, False
        Document None returns: typehints_document_rtype_none = True, False if typehints_document_rtype
        Return type as its own field: typehints_use_rtype = True, False if typehints_document_rtype
    Parameters and overloads
        Type every parameter: always_document_param_types = False, True
        List overloads: typehints_document_overloads = True, False

***********************
 Containers and unions
***********************

Builtin generics
================

A generic type takes other types in square brackets: ``list[int]`` is a list of integers, ``dict[str, int]`` maps
strings to integers. Since Python 3.9, :pep:`585`, the builtin classes and the abstract classes in
:mod:`collections.abc` take these arguments directly; older code imports :class:`typing.List` and its relatives
instead. A :class:`tuple` lists the type of each position, or one type and ``...`` for any length.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from collections.abc import Mapping, Sequence
    from typing import Dict, List


    def tally(words: Sequence[str], weights: Mapping[str, float]) -> dict[str, list[float]]:
        """
        Group the weights by word.

        :param words: the words to count
        :param weights: the weight of each word
        """
        return {}


    def corners(point: tuple[int, int], rest: tuple[int, ...], empty: tuple[()]) -> set[frozenset[int]]:
        """
        Collect the corners.

        :param point: one pair of coordinates
        :param rest: any number of coordinates
        :param empty: a tuple with no items
        """
        return set()


    def legacy(groups: Dict[str, List[int]]) -> List[int]:
        """Combine groups of numbers.

        :param groups: numbers by group
        """
        return [number for numbers in groups.values() for number in numbers]

Unions and ``Optional``
=======================

A union accepts a value of any of its types. Python 3.10, :pep:`604`, writes it with a pipe, ``int | str``; ``X |
None`` is the usual way to mark a value that may be missing. Older code spells the same types :obj:`Union[int, str]
<typing.Union>` and :data:`Optional[X] <typing.Optional>`. Since Python 3.14 both spellings build the same object, so
the extension renders each with pipes; on earlier versions it keeps the spelling the code uses, unless
:confval:`always_use_bars_union` is on.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import Optional, Union


    def find(name: str | None, limit: int | float) -> Optional[str]:
        """
        Find a record.

        :param name: the name to look for, or ``None`` for any
        :param limit: the most records to read
        """
        return None


    def parse(value: Union[str, bytes, None]) -> Union[int, float]:
        """
        Parse a number.

        :param value: the text to parse
        """
        return 0

``type[...]``
=============

:class:`type[C] <type>` is the class ``C`` itself or one of its subclasses, rather than an instance of it. It's
available on every Python the extension supports.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    class Animal:
        """An animal."""


    def build(kind: type[Animal], kinds: list[type[Animal]] | type[int]) -> Animal:
        """
        Create an animal.

        :param kind: the class to create
        :param kinds: the classes to choose from
        """
        return kind()

``Any`` and ``object``
======================

:data:`~typing.Any` turns type checking off for a value: the checker accepts any value and any use of it.
:class:`object` also accepts any value, but allows only what every object supports. Both exist on every Python the
extension supports.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import Any


    def dump(value: Any, fallback: object) -> dict[str, Any]:
        """
        Serialize a value.

        :param value: the value to serialize
        :param fallback: the value to use when serializing fails
        """
        return {}

File objects
============

:class:`~typing.IO` is the generic type of a file object, :class:`IO[str] <typing.IO>` for text and :class:`IO[bytes]
<typing.IO>` for binary data. :class:`~typing.TextIO` and :class:`~typing.BinaryIO` name those two cases. All three
exist on every Python the extension supports.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import IO, BinaryIO, TextIO


    def copy(source: IO[bytes], log: TextIO, target: BinaryIO) -> int:
        """
        Copy a stream.

        :param source: where to read from
        :param log: where to report progress
        :param target: where to write to
        """
        return 0

****************
 Literal values
****************

``Literal``
===========

:data:`~typing.Literal`, :pep:`586`, accepts only the exact values it lists, such as a string or a number. It may also
list the members of an :class:`~enum.Enum`, which the extension links to the member's class. ``Literal`` exists on every
Python the extension supports.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from enum import Enum
    from typing import Literal


    class Color(Enum):
        """A color."""

        RED = 1
        GREEN = 2


    def paint(mode: Literal["fill", "stroke"], color: Literal[Color.RED], size: Literal[1, 2, 3] | None) -> None:
        """
        Paint a shape.

        :param mode: how to paint
        :param color: the color to paint with
        :param size: the size of the brush
        """

``LiteralString``
=================

:data:`~typing.LiteralString`, :pep:`675`, accepts a string written in the source code, or one built only from such
strings. An API that runs SQL or shell commands uses it to reject text a user typed. It needs Python 3.11.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import LiteralString


    def run_query(sql: LiteralString, *params: str) -> list[tuple[str, ...]]:
        """
        Run a query with bound parameters.

        :param sql: the query, written in the code
        :param params: the values to bind
        """
        return []

********************
 Annotated metadata
********************

``Annotated``
=============

:data:`~typing.Annotated`, :pep:`593`, attaches extra values to a type, such as validation rules for a library to read.
Type checkers see only the first argument. By default the extension also drops the metadata; see
:ref:`how-to:Show selected Annotated metadata` to display values of selected metadata types. ``Annotated`` exists on
every Python the extension supports.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import Annotated


    def resize(width: Annotated[int, "pixels"], ratio: Annotated[float, range(0, 1)] = 0.5) -> None:
        """
        Resize the window.

        :param width: the new width
        :param ratio: the height divided by the width
        """

``Doc``
=======

``Doc`` from typing_extensions or `annotated-doc <https://github.com/fastapi/annotated-doc>`__ holds a description
inside :data:`~typing.Annotated` metadata. The extension writes it as the parameter or return description, so the
docstring can leave those fields out. :pep:`727` proposed adding ``Doc`` to the standard library but was withdrawn;
both third-party packages provide it on supported Python versions.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import Annotated

    from typing_extensions import Doc


    def greet(
        name: Annotated[str, Doc("who to greet")],
        times: Annotated[int, Doc("how often to repeat it")] = 1,
    ) -> Annotated[str, Doc("the greeting")]:
        """Build a greeting."""
        return f"Hello {name}" * times

The same example works with ``from annotated_doc import Doc`` in place of ``from typing_extensions import Doc``.

Other metadata classes can supply descriptions through :confval:`typehints_annotated_description`. The
:ref:`Pydantic Field example <how-to:Read descriptions from Annotated metadata>` shows a callback for
``Field(description=...)``; ``Doc`` still takes precedence when both occur on one annotation.

***********
 Callables
***********

``Callable``
============

:class:`collections.abc.Callable` describes a function by its parameter types and its return type:
``Callable[[int, str], bool]`` takes an integer and a string and returns a boolean, and ``Callable[..., bool]`` takes
any arguments. :data:`typing.Callable` is an alias of the same class. Both exist on every Python the extension
supports.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    import typing
    from collections.abc import Callable


    def retry(action: Callable[[int, str], bool], log: Callable[..., None], done: typing.Callable[[], None]) -> None:
        """
        Run an action until it succeeds.

        :param action: the action, given the attempt and a reason
        :param log: where to write messages
        :param done: called once the action succeeds
        """

``ParamSpec``
=============

A :class:`~typing.ParamSpec`, :pep:`612`, stands for the full parameter list of a callable. A decorator uses one to say
that the function it returns takes the same arguments as the function it wraps. It needs Python 3.10, and Python 3.12
adds the ``**P`` syntax of :pep:`695` to declare one in the function's brackets. ``P.args`` and ``P.kwargs`` type the
``*args`` and ``**kwargs`` of such a function; at runtime they are :class:`~typing.ParamSpecArgs` and
:class:`~typing.ParamSpecKwargs` objects. A parameter specification the signature doesn't declare renders as
``ParamSpec(P)`` and its parts as ``ParamSpecArgs(P)``, :issue:`1032`.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from collections.abc import Callable
    from typing import ParamSpec

    P = ParamSpec("P")


    def logged[R](func: Callable[P, R]) -> Callable[P, R]:
        """
        Log each call of a function.

        :param func: the function to log
        """
        return func


    def call(func: Callable[P, int], *args: P.args, **kwargs: P.kwargs) -> int:
        """
        Call a function.

        :param func: the function to call
        :param args: its positional arguments
        :param kwargs: its keyword arguments
        """
        return func(*args, **kwargs)


    def timed[**Q, R](func: Callable[Q, R], *args: Q.args, **kwargs: Q.kwargs) -> R:
        """
        Time one call of a function.

        :param func: the function to call
        :param args: its positional arguments
        :param kwargs: its keyword arguments
        """
        return func(*args, **kwargs)

``Concatenate``
===============

:data:`~typing.Concatenate`, :pep:`612`, adds parameters in front of a :class:`~typing.ParamSpec`. A decorator that
supplies the first argument itself, such as a database connection, uses it to describe the function it accepts. It
needs Python 3.10.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from collections.abc import Callable
    from typing import Concatenate


    class Connection:
        """A database connection."""


    def with_connection[**P, R](func: Callable[Concatenate[Connection, P], R]) -> Callable[P, R]:
        """
        Pass a connection as the first argument.

        :param func: the function that needs a connection
        """
        raise NotImplementedError

******************************
 Type variables and generics
******************************

``TypeVar``
===========

A :class:`~typing.TypeVar` is a placeholder that a use of a function or class fills with a concrete type, so
``first(items: list[T]) -> T`` returns the type the list holds. A bound, ``bound=Sized``, limits it to subclasses of a
type, and constraints, ``TypeVar("S", str, bytes)``, limit it to exactly the types listed. Before Python 3.12, a generic
class subclasses :class:`~typing.Generic` to declare its type variables. A type variable no signature declares, as
``longest`` and ``join`` below use it, renders with its bound or constraints, such as ``TypeVar(B, bound=Sized)``,
:issue:`1032`.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from collections.abc import Sized
    from typing import Generic, TypeVar

    T = TypeVar("T")
    B = TypeVar("B", bound=Sized)
    S = TypeVar("S", str, bytes)


    def longest(items: list[B]) -> B:
        """
        Pick the longest item.

        :param items: the items to compare
        """
        return max(items, key=len)


    def join(parts: list[S], sep: S) -> S:
        """
        Join the parts.

        :param parts: the parts to join
        :param sep: what goes between them
        """
        return sep.join(parts)


    class Box(Generic[T]):
        """A box holding one item."""

        def get(self) -> T:
            """Take the item out."""
            raise NotImplementedError

Type parameter syntax
=====================

Python 3.12, :pep:`695`, declares type parameters in square brackets after the name of a function or class, so neither
:class:`~typing.TypeVar` nor :class:`~typing.Generic` needs an import. ``[T: Sized]`` gives a bound and ``[S: (str,
bytes)]`` gives constraints.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from collections.abc import Sized


    def longest[T: Sized](items: list[T]) -> T:
        """
        Pick the longest item.

        :param items: the items to compare
        """
        return max(items, key=len)


    def join[S: (str, bytes)](parts: list[S], sep: S) -> S:
        """
        Join the parts.

        :param parts: the parts to join
        :param sep: what goes between them
        """
        return sep.join(parts)


    class Box[T]:
        """A box holding one item."""

        def put(self, item: T) -> None:
            """
            Put an item in.

            :param item: the item
            """

Type parameter defaults
=======================

Python 3.13, :pep:`696`, lets a type parameter name the type it takes when a use leaves it out, as ``[T = str]`` or
``TypeVar("T", default=str)``. On older versions the ``TypeVar`` of typing_extensions accepts ``default=``.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import Generic, TypeVar

    K = TypeVar("K", default=str)


    class Cache[V = bytes]:
        """A cache of values."""

        def get(self, key: str) -> V | None:
            """
            Look a value up.

            :param key: the key to look up
            """
            return None


    class Index(Generic[K]):
        """An index of keys."""

        def add(self, key: K) -> None:
            """
            Add a key.

            :param key: the key
            """


    def first[T = int](items: list[T]) -> T:
        """
        Take the first item.

        :param items: the items
        """
        return items[0]

``TypeVarTuple`` and ``Unpack``
===============================

A :class:`~typing.TypeVarTuple`, :pep:`646`, stands for any number of types, so a function can keep the type of each
position of a tuple. ``*Ts`` unpacks it inside brackets, as does :data:`Unpack[Ts] <typing.Unpack>` on older versions,
and ``*tuple[int, ...]`` unpacks a tuple type into the arguments of another. It needs Python 3.11, and Python 3.12
declares one in brackets as ``[*Ts]``. The extension renders each star as :data:`Unpack[...] <typing.Unpack>`,
:issue:`1031`, and a type variable tuple the signature doesn't declare as ``TypeVarTuple(Ts)``, :issue:`1032`.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import TypeVarTuple, Unpack

    Ts = TypeVarTuple("Ts")


    def shift(values: tuple[int, *Ts]) -> tuple[*Ts, int]:
        """
        Move the first value to the end.

        :param values: the values
        """
        return (*values[1:], values[0])


    def drop(values: tuple[int, Unpack[Ts]]) -> tuple[Unpack[Ts]]:
        """
        Drop the first value.

        :param values: the values
        """
        return values[1:]


    def call[*Us](*args: *Us) -> tuple[*Us]:
        """
        Collect the arguments.

        :param args: the arguments
        """
        return args


    def head(values: tuple[str, *tuple[int, ...]]) -> str:
        """
        Take the label.

        :param values: a label followed by any number of integers
        """
        return values[0]

``AnyStr``
==========

:data:`~typing.AnyStr` is a predefined :class:`~typing.TypeVar` constrained to :class:`str` and :class:`bytes`, so a
function taking two of them accepts two strings or two byte strings but not one of each. Python 3.13 deprecates it, to
be removed in 3.18, in favor of the type parameter syntax ``[S: (str, bytes)]``. Unlike a type variable the module
defines, it renders by its name.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import AnyStr


    def concat(left: AnyStr, right: AnyStr) -> AnyStr:
        """
        Join two strings of the same kind.

        :param left: the first part
        :param right: the second part
        """
        return left + right

**************
 Type aliases
**************

The ``type`` statement
======================

Python 3.12, :pep:`695`, names a type with ``type Vector = list[float]``. The name is a
:class:`~typing.TypeAliasType`, and Python evaluates its value only when something asks for it, so the value can refer
to names defined further down. An alias may take type parameters, ``type Pairs[K] = dict[K, K]``. An alias the docs
document renders by its name and links to its entry; :ref:`how-to:Link type aliases` covers the other cases.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    type Vector = list[float]
    """Coordinates along each axis."""

    type Pairs[K] = dict[K, K]
    """A mapping from keys to keys of the same type."""

    type Tree = dict[str, Tree] | Leaf
    """A tree of named branches."""


    class Leaf:
        """The end of a branch."""


    def scale(vector: Vector, pairs: Pairs[int], tree: Tree) -> Vector:
        """
        Scale a vector.

        :param vector: the vector to scale
        :param pairs: which axes to swap
        :param tree: where to store the result
        """
        return vector

``TypeAliasType``
=================

:class:`~typing.TypeAliasType` builds the same object as the ``type`` statement, called as a function. Code that must
run on Python versions before 3.12 imports it from typing_extensions; :mod:`typing` has it since 3.12.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import TypeAliasType, TypeVar

    T = TypeVar("T")

    Matrix = TypeAliasType("Matrix", list[list[float]])
    """Rows of numbers."""

    Grid = TypeAliasType("Grid", list[list[T]], type_params=(T,))
    """Rows of cells."""


    def transpose(matrix: Matrix, grid: Grid[int]) -> Matrix:
        """
        Swap rows and columns.

        :param matrix: the matrix
        :param grid: a grid of the same shape
        """
        return matrix

``TypeAlias``
=============

:data:`~typing.TypeAlias`, :pep:`613`, marks an assignment such as ``Vector: TypeAlias = list[float]`` as a type alias
rather than a variable. It needs Python 3.10. At runtime the name holds the value itself, so annotations that use it
render the value. Python 3.12 deprecates it in favor of the ``type`` statement.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import TypeAlias

    Vector: TypeAlias = list[float]
    """Coordinates along each axis."""


    def norm(vector: Vector) -> float:
        """
        Compute the length of a vector.

        :param vector: the vector
        """
        return sum(x * x for x in vector) ** 0.5

``NewType``
===========

:class:`~typing.NewType` makes a distinct type from an existing one, so a type checker tells a ``UserId`` from any
other :class:`int`; at runtime the value stays an :class:`int`. The extension shows the type it wraps next to its name.
It exists on every Python the extension supports.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import NewType

    UserId = NewType("UserId", int)


    def load(user: UserId, others: list[UserId]) -> str:
        """
        Load a user's name.

        :param user: the user
        :param others: users to load along with it
        """
        return ""

*********************
 Classes and members
*********************

``Protocol``
============

A :class:`~typing.Protocol`, :pep:`544`, describes the methods and attributes a type must have, and any class that has
them matches, without inheriting from it. :func:`@runtime_checkable <typing.runtime_checkable>` also lets
:func:`isinstance` test for the protocol. Both exist on every Python the extension supports.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import Protocol, runtime_checkable


    @runtime_checkable
    class Closable(Protocol):
        """Something that can be closed."""

        def close(self, force: bool) -> None:
            """
            Close it.

            :param force: close even when busy
            """


    def shutdown(resources: list[Closable]) -> int:
        """
        Close every resource.

        :param resources: the resources to close
        """
        return len(resources)

Protocols for special methods
=============================

:mod:`typing` defines a :class:`~typing.Protocol` for each of several special methods: :class:`~typing.SupportsAbs`
(``__abs__``), :class:`~typing.SupportsBytes`, :class:`~typing.SupportsComplex`, :class:`~typing.SupportsFloat`,
:class:`~typing.SupportsIndex`, :class:`~typing.SupportsInt` and :class:`~typing.SupportsRound` (``__round__``). A
parameter typed with one accepts any object with that method. All exist on every Python the extension supports.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import (
        SupportsAbs,
        SupportsBytes,
        SupportsComplex,
        SupportsFloat,
        SupportsIndex,
        SupportsInt,
        SupportsRound,
    )


    def magnitude(value: SupportsAbs[float], digits: SupportsIndex) -> SupportsRound[float]:
        """
        Measure a value.

        :param value: the value to measure
        :param digits: how many digits to keep
        """
        return abs(value)


    def convert(
        whole: SupportsInt, real: SupportsFloat, plane: SupportsComplex, raw: SupportsBytes
    ) -> tuple[int, float, complex, bytes]:
        """
        Convert values to builtin numbers and bytes.

        :param whole: converted with ``int()``
        :param real: converted with ``float()``
        :param plane: converted with ``complex()``
        :param raw: converted with ``bytes()``
        """
        return int(whole), float(real), complex(plane), bytes(raw)

``Self``
========

:data:`~typing.Self`, :pep:`673`, is the class a method is called on, so a method that returns its own instance keeps
the subclass's type. It needs Python 3.11.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import Self


    class Query:
        """A database query."""

        def where(self, condition: str) -> Self:
            """
            Add a condition.

            :param condition: the condition to add
            """
            return self

        def merge(self, other: Self) -> Self:
            """
            Combine two queries.

            :param other: the other query
            """
            return self

``Final`` and ``ClassVar``
==========================

:data:`~typing.Final`, :pep:`591`, marks a name a type checker won't let code assign again. :data:`~typing.ClassVar`
marks an attribute that belongs to the class rather than to each instance. Both exist on every Python the extension
supports. The extension shows the type each holds.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import ClassVar, Final

    LIMIT: Final[int] = 10
    """The most retries."""


    class Client:
        """
        A network client.

        :cvar instances: how many clients exist
        :ivar timeout: seconds to wait
        """

        instances: ClassVar[int] = 0
        timeout: Final[float]

        def __init__(self) -> None:
            self.timeout = 1.0

``NamedTuple``
==============

A :class:`~typing.NamedTuple` is a tuple whose positions have names and types, declared like a class. It exists on
every Python the extension supports.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import NamedTuple


    class Point(NamedTuple):
        """A point on a plane."""

        x: float
        """The horizontal position."""
        y: float = 0.0
        """The vertical position."""


    def distance(start: Point, end: Point) -> float:
        """
        Measure a distance.

        :param start: where to start
        :param end: where to end
        """
        return 0.0

Dataclasses
===========

:func:`@dataclass <dataclasses.dataclass>` writes an ``__init__`` and other methods from the annotated fields of a
class. Each field documented with a docstring gets its type, and the generated ``__init__`` takes them in order.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from dataclasses import InitVar, dataclass, field


    @dataclass(frozen=True)
    class Order:
        """An order."""

        item: str
        """What was ordered."""
        quantity: int = 1
        """How many."""
        tags: list[str] = field(default_factory=list)
        """Labels for the order."""
        discount: InitVar[float] = 0.0
        """The discount, used only while building the order."""

attrs classes
=============

The :doc:`attrs <attrs:index>` library builds classes from annotated fields as dataclasses do. The extension reads each
field's type from attrs' metadata.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    import attrs


    @attrs.define
    class Order:
        """An order."""

        item: str
        """What was ordered."""
        quantity: int = 1
        """How many."""
        tags: list[str] = attrs.field(factory=list)
        """Labels for the order."""

``disjoint_base``
=================

:func:`@disjoint_base <typing.disjoint_base>`, :pep:`800`, marks a class that can't share a subclass with another
disjoint base, as two builtin classes such as :class:`int` and :class:`str` can't. A type checker uses it to tell that
a value can't be both. It needs Python 3.15, or typing_extensions on older versions, and changes nothing the extension
renders.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import disjoint_base


    @disjoint_base
    class Record:
        """A record with a fixed memory layout."""

        __slots__ = ("key",)

        def __init__(self, key: str) -> None:
            self.key = key

***************
 ``TypedDict``
***************

``Required`` and ``NotRequired``
================================

A :class:`~typing.TypedDict`, :pep:`589`, gives the type of each key of a dictionary. :data:`~typing.NotRequired`,
:pep:`655`, marks a key the dictionary may lack, and :data:`~typing.Required` marks one it must have inside a
``total=False`` class, whose keys are otherwise optional. Both need Python 3.11.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import NotRequired, Required, TypedDict


    class Movie(TypedDict):
        """A movie."""

        title: str
        """The title."""
        year: NotRequired[int]
        """The year it came out."""


    class Filter(TypedDict, total=False):
        """A search filter."""

        field: Required[str]
        """The field to match."""
        value: str
        """The value to match."""

``ReadOnly``
============

:data:`~typing.ReadOnly`, :pep:`705`, marks a key that code may read but not change. It needs Python 3.13, or
typing_extensions on older versions.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import NotRequired, ReadOnly, TypedDict


    class Account(TypedDict):
        """An account."""

        id: ReadOnly[int]
        """The account number."""
        nickname: ReadOnly[NotRequired[str]]
        """A name the owner chose."""
        balance: float
        """The money in the account."""

Closed ``TypedDict`` and extra items
====================================

A :class:`~typing.TypedDict` accepts keys beyond those it lists. :pep:`728` restricts that: ``closed=True`` allows no
other key, and ``extra_items=int`` allows any other key with an :class:`int` value. It needs Python 3.15, or
typing_extensions on older versions. The extension lists the extra items in a field; a closed class shows
:data:`~typing.Never` there, the type no value has.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import TypedDict


    class Point(TypedDict, closed=True):
        """A point and nothing else."""

        x: int
        """The horizontal position."""
        y: int
        """The vertical position."""


    class Scores(TypedDict, extra_items=float):
        """Scores by player, with the total."""

        total: float
        """The sum of the scores."""

``**kwargs`` typed with ``Unpack``
==================================

``**kwargs: Unpack[Options]``, :pep:`692`, types each keyword argument by the matching key of a
:class:`~typing.TypedDict`, where ``**kwargs: int`` gives every one the same type. Type checkers accept it from Python
3.12. The extension gives each keyword argument the docstring names the type of its key, see
:ref:`kwargs-unpack`.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import NotRequired, TypedDict, Unpack


    class Options(TypedDict):
        """Options for a connection."""

        host: str
        """The server to connect to."""
        port: NotRequired[int]
        """The port, 80 when left out."""


    def connect(**kwargs: Unpack[Options]) -> None:
        """
        Open a connection.

        :keyword host: the server
        :keyword port: the port
        """

*************************
 Narrowing and no-return
*************************

``TypeGuard`` and ``TypeIs``
============================

A function returning :data:`~typing.TypeGuard`, :pep:`647`, or :data:`~typing.TypeIs`, :pep:`742`, returns a boolean
that tells a type checker the type of its argument when it's true. ``TypeIs`` also narrows the argument when the
function returns false, which ``TypeGuard`` doesn't. ``TypeGuard`` needs Python 3.10, ``TypeIs`` Python 3.13 or
typing_extensions.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import TypeGuard, TypeIs


    def all_strings(values: list[object]) -> TypeGuard[list[str]]:
        """
        Check that every value is a string.

        :param values: the values to check
        """
        return all(isinstance(value, str) for value in values)


    def is_number(value: object) -> TypeIs[int | float]:
        """
        Check that a value is a number.

        :param value: the value to check
        """
        return isinstance(value, int | float)

``Never`` and ``NoReturn``
==========================

:data:`~typing.Never` is the type with no values. As a return type it means the function never returns, as one that
always raises; :data:`~typing.NoReturn` says the same and is the older spelling. As a parameter type it means no call is
valid, which :func:`~typing.assert_never` uses to check that code handles every case. ``NoReturn`` exists on every
Python the extension supports, ``Never`` needs Python 3.11.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import Never, NoReturn


    def fail(message: str) -> NoReturn:
        """
        Stop with an error.

        :param message: the error message
        """
        raise RuntimeError(message)


    def unreachable(value: Never) -> Never:
        """
        Mark a branch no value reaches.

        :param value: the value that reached it
        """
        raise AssertionError(value)

``TypeForm``
============

:data:`~typing.TypeForm`, :pep:`747`, is the type of a value that is itself a type expression, such as ``int | None``
passed to a function that validates data against it. :class:`type[C] <type>` only covers classes, so it can't describe
a union or a :data:`~typing.Literal`. It needs Python 3.15, or typing_extensions on older versions.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import TypeForm


    def validate[T](schema: TypeForm[T], data: object) -> T:
        """
        Check data against a type.

        :param schema: the type the data must match, such as ``int | None``
        :param data: the data to check
        """
        raise NotImplementedError

************
 Decorators
************

``overload``
============

:func:`@overload <typing.overload>` declares the signatures a function accepts, when its return type depends on the
argument types. Type checkers read the declarations; the function defined after them runs. The extension lists the
declared signatures in an ``Overloads`` field, see :ref:`how-to:Document overloads`. It exists on every Python the
extension supports.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import overload


    @overload
    def parse(value: str) -> int: ...


    @overload
    def parse(value: bytes, encoding: str) -> str: ...


    def parse(value: str | bytes, encoding: str = "utf-8") -> int | str:
        """
        Parse a value.

        :param value: the value to parse
        :param encoding: how bytes are encoded
        """
        return 0

``override``
============

:func:`@override <typing.override>`, :pep:`698`, marks a method that replaces one in a base class, so a type checker
reports it when the base class no longer has that method. It needs Python 3.12, or typing_extensions. The extension
adds an ``Overrides`` field that links the replaced method.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import override


    class Shape:
        """A shape."""

        def area(self) -> float:
            """Compute the area."""
            return 0.0


    class Square(Shape):
        """A square."""

        @override
        def area(self) -> float:
            """Compute the area of the square."""
            return 1.0

``deprecated``
==============

:func:`@warnings.deprecated <warnings.deprecated>`, :pep:`702`, marks a function, method, class or overload as
deprecated: type checkers report its uses, and calling it emits a :exc:`DeprecationWarning`. It needs Python 3.13, or
``typing_extensions.deprecated`` on older versions. The extension adds the message below the summary.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from warnings import deprecated


    @deprecated("Use fetch() instead.")
    def get(url: str) -> bytes:
        """
        Download a page.

        :param url: the page to download
        """
        return b""

************************
 Generators and async
************************

Generators and iterators
========================

A :class:`~collections.abc.Generator` annotation gives three types: what the function yields, what callers can send in,
and what it returns at the end. :class:`~collections.abc.Iterator` and :class:`~collections.abc.Iterable` describe a
generator that only yields. When the docstring has a yields field, the extension puts the yielded type there instead of
a return type.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from collections.abc import Generator, Iterator


    def count(start: int) -> Iterator[int]:
        """
        Count up forever.

        :param start: the first number
        :yields: the numbers
        """
        while True:
            yield start
            start += 1


    def running_total() -> Generator[float, float, str]:
        """
        Add up the numbers sent in.

        :yields: the total so far
        :returns: a summary once the caller closes it
        """
        total = 0.0
        while True:
            total += yield total


    def lines(path: str) -> Generator[str]:
        """
        Read lines.

        :param path: the file to read
        """
        yield path

``Generator[str]`` leaves out the send and return types, which default to ``None`` from Python 3.13, :pep:`696`.

Coroutines and async iterators
==============================

An ``async def`` function returns a coroutine; its annotation names the value the coroutine produces, and the extension
renders that type. :class:`~collections.abc.Awaitable` describes any object ``await`` accepts, and
:class:`~collections.abc.AsyncIterator` and :class:`~collections.abc.AsyncGenerator` describe what ``async for`` loops
over.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Coroutine


    async def fetch(url: str) -> bytes:
        """
        Download a page.

        :param url: the page to download
        """
        return b""


    async def first(pending: Awaitable[int], later: Coroutine[None, None, str]) -> int:
        """
        Wait for a value.

        :param pending: the value to wait for
        :param later: a coroutine to run afterwards
        """
        return await pending


    async def ticks(count: int) -> AsyncIterator[int]:
        """
        Produce ticks.

        :param count: how many
        :yields: the tick number
        """
        for tick in range(count):
            yield tick


    async def echo() -> AsyncGenerator[str, str]:
        """Repeat what the caller sends."""
        received = ""
        while True:
            received = yield received

*************************
 When annotations resolve
*************************

``TYPE_CHECKING`` imports
=========================

Code in an :data:`if TYPE_CHECKING: <typing.TYPE_CHECKING>` block runs only for type checkers, so an import there
costs nothing at runtime and can't create an import cycle. The annotations that use those names then fail to resolve at
runtime; the extension runs the block itself to resolve and link them. :ref:`type-checking` covers the details.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from __future__ import annotations

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from decimal import Decimal
        from fractions import Fraction


    def ratio(amount: Decimal, part: Fraction) -> Decimal:
        """
        Apply a ratio.

        :param amount: the amount
        :param part: the share to take
        """
        raise NotImplementedError

Forward references
==================

An annotation written as a string, ``"Node"``, is a forward reference: Python keeps the text and resolves it later, so
it can name a class defined further down or the class being defined. The extension resolves it against the module and
renders the type.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    class Node:
        """A node in a tree."""

        def add(self, child: "Node", label: "Label | None") -> "list[Node]":
            """
            Attach a child.

            :param child: the node to attach
            :param label: a label for the edge
            """
            return []


    class Label:
        """A label."""

``from __future__ import annotations``
======================================

:pep:`563`, enabled per module with ``from __future__ import annotations``, keeps every annotation in the module as a
string, so each acts as a forward reference. It works on every Python the extension supports. The extension evaluates
the strings and renders the types as it would without the import.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from __future__ import annotations


    class Node:
        """A node in a tree."""

        def add(self, child: Node, weight: int | None = None) -> list[Node]:
            """
            Attach a child.

            :param child: the node to attach
            :param weight: the weight of the edge
            """
            return []

Lazy annotations
================

From Python 3.14, :pep:`649` and :pep:`749`, Python evaluates annotations only when code reads them, so an annotation
can name a class defined further down without quotes or a ``__future__`` import. The :mod:`annotationlib` module reads
them in several formats, including as strings. The extension reads them as it reads any other annotation.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    class Node:
        """A node in a tree."""

        def add(self, child: Node, label: Label | None) -> list[Node]:
            """
            Attach a child.

            :param child: the node to attach
            :param label: a label for the edge
            """
            return []


    class Label:
        """A label."""

***********
 Sentinels
***********

``sentinel``
============

A sentinel is a unique marker value, such as ``MISSING``, that stands for an argument left out where ``None`` is a
valid value. Python 3.15, :pep:`661`, adds the builtin :class:`sentinel` to create one, which an annotation can use as
its own type. Older versions get it as ``typing_extensions.Sentinel``.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    MISSING = sentinel("MISSING")
    """The marker for an argument left out."""


    def lookup(key: str, default: int | None | MISSING = MISSING) -> int | None:
        """
        Look a key up.

        :param key: the key to look up
        :param default: the value to return when the key is absent
        """
        return None

********************
 Deprecated aliases
********************

Before Python 3.9, a type annotation couldn't subscript the builtin classes or the abstract classes of
:mod:`collections.abc`, so :mod:`typing` defined a subscriptable alias for each. :pep:`585` made the originals
subscriptable and deprecated the aliases in Python 3.9; no release date for removing them is set, except where an entry
says so. Each alias still works, and the extension links it to its :mod:`typing` entry.

Builtin collections
===================

:class:`~typing.List`, :class:`~typing.Dict`, :class:`~typing.Set`, :class:`~typing.FrozenSet`, :data:`~typing.Tuple`
and :class:`~typing.Type` stand for :class:`list`, :class:`dict`, :class:`set`, :class:`frozenset`, :class:`tuple` and
:class:`type`. :class:`~typing.DefaultDict`, :class:`~typing.OrderedDict`, :class:`~typing.Counter`,
:class:`~typing.ChainMap` and :class:`~typing.Deque` stand for :class:`~collections.defaultdict`,
:class:`~collections.OrderedDict`, :class:`~collections.Counter`, :class:`~collections.ChainMap` and
:class:`~collections.deque`. All are deprecated since Python 3.9.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import ChainMap, Counter, DefaultDict, Deque, Dict, FrozenSet, List, OrderedDict, Set, Tuple, Type


    def index(
        words: List[str],
        seen: Set[str],
        stop: FrozenSet[str],
        pairs: Tuple[int, str],
        kind: Type[Exception],
    ) -> Dict[str, int]:
        """
        Index words.

        :param words: the words
        :param seen: words already indexed
        :param stop: words to skip
        :param pairs: a position and a word
        :param kind: the error to raise
        """
        return {}


    def group(
        by_key: DefaultDict[str, list[int]],
        ordered: OrderedDict[str, int],
        counts: Counter[str],
        layers: ChainMap[str, int],
        queue: Deque[int],
    ) -> None:
        """
        Group values.

        :param by_key: values by key
        :param ordered: values in insertion order
        :param counts: how often each key occurs
        :param layers: settings looked up in order
        :param queue: values waiting
        """

Abstract collections and callables
==================================

These aliases stand for the class of the same name in :mod:`collections.abc`: :class:`~typing.Container`,
:class:`~typing.Collection`, :class:`~typing.Iterable`, :class:`~typing.Iterator`, :class:`~typing.Reversible`,
:class:`~typing.Sequence`, :class:`~typing.MutableSequence`, :class:`~typing.Mapping`, :class:`~typing.MutableMapping`,
:class:`~typing.MutableSet`, :class:`~typing.MappingView`, :class:`~typing.KeysView`, :class:`~typing.ItemsView`,
:class:`~typing.ValuesView`, :class:`~typing.Generator`, :class:`~typing.Awaitable`, :class:`~typing.Coroutine`,
:class:`~typing.AsyncIterable`, :class:`~typing.AsyncIterator`, :class:`~typing.AsyncGenerator` and
:data:`~typing.Callable`, all deprecated since Python 3.9. :class:`~typing.AbstractSet` stands for
:class:`collections.abc.Set`, also since 3.9. :class:`~typing.Hashable` and :class:`~typing.Sized` are deprecated since
Python 3.12.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import (
        AbstractSet,
        Collection,
        Container,
        Hashable,
        ItemsView,
        Iterable,
        Iterator,
        KeysView,
        Mapping,
        MappingView,
        MutableMapping,
        MutableSequence,
        MutableSet,
        Reversible,
        Sequence,
        Sized,
        ValuesView,
    )


    def inspect(
        box: Container[int],
        bag: Collection[int],
        items: Iterable[str],
        cursor: Iterator[str],
        back: Reversible[str],
        rows: Sequence[str],
        stack: MutableSequence[str],
        table: Mapping[str, int],
        cache: MutableMapping[str, int],
        tags: AbstractSet[str],
        pending: MutableSet[str],
    ) -> Hashable | Sized:
        """
        Inspect collections.

        :param box: supports ``in``
        :param bag: has a size and supports ``in`` and iteration
        :param items: supports iteration
        :param cursor: returns the next item
        :param back: supports ``reversed()``
        :param rows: supports indexing
        :param stack: supports indexing and changes
        :param table: maps keys to values
        :param cache: maps keys to values and changes
        :param tags: a set that doesn't change
        :param pending: a set that changes
        """
        return 0


    def views(any_view: MappingView, keys: KeysView[str], pairs: ItemsView[str, int], values: ValuesView[int]) -> None:
        """
        Look at the views of a mapping.

        :param any_view: any view
        :param keys: the keys
        :param pairs: the pairs
        :param values: the values
        """

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import (
        AsyncGenerator,
        AsyncIterable,
        AsyncIterator,
        Awaitable,
        Callable,
        Coroutine,
        Generator,
    )


    async def pump(
        source: AsyncIterable[bytes],
        cursor: AsyncIterator[bytes],
        stream: AsyncGenerator[bytes, None],
        ready: Awaitable[None],
        task: Coroutine[None, None, int],
        lines: Generator[str, None, None],
        on_chunk: Callable[[bytes], None],
    ) -> int:
        """
        Move data from a source to a callback.

        :param source: the data
        :param cursor: a position in the data
        :param stream: a generator of data
        :param ready: resolves when the target is ready
        :param task: a coroutine to run at the end
        :param lines: a log of the transfer
        :param on_chunk: called with each chunk
        """
        return 0

Context managers
================

:class:`~typing.ContextManager` and :class:`~typing.AsyncContextManager` stand for
:class:`contextlib.AbstractContextManager` and :class:`contextlib.AbstractAsyncContextManager`, deprecated since
Python 3.9. Python 3.13 gave each a second type parameter, the type ``__exit__`` returns, with a default. A subscript
that leaves it out renders as written, without the default.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import AsyncContextManager, ContextManager


    def hold(lock: ContextManager[None], session: AsyncContextManager[str]) -> None:
        """
        Hold a lock.

        :param lock: entered with ``with``
        :param session: entered with ``async with``
        """

Regular expressions
===================

:class:`~typing.Pattern` and :class:`~typing.Match` stand for :class:`re.Pattern` and :class:`re.Match`, deprecated
since Python 3.9.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import Match, Pattern


    def search(pattern: Pattern[str], text: str) -> Match[str] | None:
        """
        Find a match.

        :param pattern: the compiled pattern
        :param text: the text to search
        """
        return pattern.search(text)

``Text`` and ``ByteString``
===========================

:class:`~typing.Text` is :class:`str`, kept for code that ran on Python 2; Python 3.11 deprecates it. Since it's the
same object as :class:`str`, it renders as ``str``. :class:`~typing.ByteString` stood for :class:`bytes`,
:class:`bytearray` and :class:`memoryview`, but type checkers never treated it that way. Deprecated since Python 3.9,
it left ``typing.__all__`` in 3.15, warns when imported, and is due for removal in 3.17;
:class:`collections.abc.Buffer` or a union such as ``bytes | bytearray`` replaces it.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import ByteString, Text


    def decode(raw: ByteString, encoding: Text) -> Text:
        """
        Decode bytes.

        :param raw: the bytes to decode
        :param encoding: the encoding
        """
        return ""

*****************
 Runtime helpers
*****************

``final``, ``no_type_check`` and ``dataclass_transform``
=========================================================

:func:`@final <typing.final>`, :pep:`591`, marks a class that can't be subclassed or a method that can't be
overridden. Autodoc writes ``final`` in front of the entry. :func:`@no_type_check <typing.no_type_check>` tells type
checkers to skip a function's annotations; :func:`~typing.get_type_hints` then returns none, but the extension still
reads and renders them. :func:`@dataclass_transform <typing.dataclass_transform>`, :pep:`681`, marks a decorator,
base class or metaclass that creates dataclass-like classes, so type checkers treat its classes as dataclasses; it
changes nothing on the page. All three exist on every Python the extension supports.
``typing.no_type_check_decorator``, which made a decorator act like ``@no_type_check``, was deprecated in Python 3.13
and removed in 3.15.

.. live-example::

    extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]
    ---
    from typing import dataclass_transform, final, no_type_check


    @final
    class Token:
        """A token no class can extend."""

        @final
        def value(self) -> str:
            """The text of the token."""
            return ""


    @no_type_check
    def legacy(count: int, name: "str | None") -> list[str]:
        """
        Code type checkers skip.

        :param count: how many
        :param name: a name
        """
        return []


    @dataclass_transform()
    class ModelBase:
        """A base class for models that type checkers treat as dataclasses."""

Functions without a rendering
=============================

The rest of :mod:`typing` works at runtime or only for type checkers, and never appears in an annotation, so none of
it has a rendering of its own:

- :func:`~typing.cast` returns its value unchanged and tells a type checker to treat it as the given type.
- :func:`~typing.assert_type` asks a type checker to confirm a value's type; :func:`~typing.reveal_type` asks it to
  print the type. :func:`~typing.assert_never`, Python 3.11, fails when a branch a type checker considers unreachable
  runs.
- :func:`~typing.get_type_hints` evaluates an object's annotations; the extension calls it to read them.
  :func:`~typing.get_origin` and :func:`~typing.get_args` split a subscripted type, as ``dict[str, int]`` into
  :class:`dict` and ``(str, int)``; the extension uses both to walk a type.
- :func:`~typing.get_overloads`, Python 3.11, returns the :func:`@overload <typing.overload>` declarations of a
  function, which the extension lists; :func:`~typing.clear_overloads` empties that registry, after which the extension
  falls back to reading them from the source.
- :func:`~typing.is_protocol` and :func:`~typing.get_protocol_members`, Python 3.13, and :func:`~typing.is_typeddict`
  inspect a class at runtime. The extension doesn't call them.
- :class:`~typing.ForwardRef` is the object Python builds for an annotation it can't evaluate yet, and
  :func:`~typing.evaluate_forward_ref`, Python 3.14, evaluates one. The extension uses it to resolve a string
  annotation on 3.14 and later.
- :data:`~typing.NoDefault`, Python 3.13, is the value of ``__default__`` on a type parameter without a default.
  :data:`~typing.NoExtraItems`, Python 3.15, is the ``extra_items`` value of a :class:`~typing.TypedDict` that sets
  none; the extension reads it to decide whether to write an ``Extra items`` field.
- :data:`~typing.TYPE_CHECKING` has its own entry, :ref:`typing:\`\`TYPE_CHECKING\`\` imports`.
