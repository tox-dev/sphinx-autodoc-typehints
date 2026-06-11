"""Module without deferred annotations to test the globals-scanning path."""

from typing import Any, Union

UserId = Union[int, str]
RequestData = dict[str, Any]


def get_user_eager(user_id: UserId) -> str:
    """
    Get a user by ID.

    Args:
        user_id: The user identifier
    """
    return f"User {user_id}"
