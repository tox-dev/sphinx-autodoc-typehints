"""Module whose annotations stay strings until the extension resolves them."""

from __future__ import annotations

from typing import Any, Union

UserId = Union[int, str]
RequestData = dict[str, Any]


def get_user(user_id: UserId) -> str:
    """
    Get a user by ID.

    Args:
        user_id: The user identifier
    """
    return f"User {user_id}"


def process_request(data: RequestData) -> bool:
    """
    Process a request.

    Args:
        data: The request data
    """
    return bool(data)
