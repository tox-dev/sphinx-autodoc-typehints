"""Patch to napoleon that keeps it from typing attributes from their annotations, so the extension types them itself."""

from __future__ import annotations

from functools import wraps

from sphinx.ext.napoleon.docstring import GoogleDocstring


def patch_lookup_annotation() -> None:
    """
    Keep napoleon from typing the attributes of a class or module from their annotations (#308).

    The extension types them itself, rendered like its other fields, where napoleon's own lookup gave the
    parameters of a constructor the wrong types too.
    """
    GoogleDocstring._lookup_annotation = _no_annotation  # ty: ignore[invalid-assignment]  # wraps returns a _Wrapped


@wraps(GoogleDocstring._lookup_annotation)
def _no_annotation(*_args: object) -> str:
    return ""


__all__ = [
    "patch_lookup_annotation",
]
