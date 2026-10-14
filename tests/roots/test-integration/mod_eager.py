"""Module without deferred annotations to test the globals-scanning path."""

from collections.abc import Generator
from typing import Annotated, Any, Generic, NewType, TypeVar, Union

from typing_extensions import Doc

UserId = Union[int, str]
RequestData = dict[str, Any]
Count = int
T = TypeVar("T")
Described = Annotated[int, Doc("an int value")]
Counter = Generator[int, None, str]
Ticket = NewType("Ticket", int)


def get_user_eager(user_id: UserId) -> str:
    """
    Get a user by ID.

    Args:
        user_id: The user identifier
    """
    return f"User {user_id}"


def count_eager(amount: Count, limit: int) -> None:
    """
    Count up to a limit.

    Args:
        amount: The amount
        limit: The limit
    """


class Users:
    """A user registry."""

    def get(self, user_id: UserId) -> str:
        """
        Get a user by ID.

        Args:
            user_id: The user identifier
        """
        return f"{type(self).__name__} {user_id}"

    @property
    def size(self) -> Count:
        """The number of users."""
        return 0


class Special:
    """A class a formatter renders."""


def describe(value: Described) -> None:
    """Describe a value."""


def take_special(value: Special) -> None:
    """
    Take a special value.

    Args:
        value: The value
    """


def count_up() -> Counter:
    """
    Count up.

    Yields:
        numbers

    Returns:
        a name
    """
    yield 1
    return "done"


def take_ticket(number: Ticket) -> None:
    """
    Take a ticket.

    Args:
        number: The number
    """


class Base(Generic[T]):
    """A base."""

    def echo(self, value: T) -> T:
        """
        Echo a value.

        Args:
            value: The value
        """
        return value


class Sub(Base[int]):
    """A subclass binding the type parameter."""
