"""Module without deferred annotations to test the globals-scanning path."""

from typing import Any, Union

UserId = Union[int, str]
RequestData = dict[str, Any]
Count = int


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
