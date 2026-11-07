from __future__ import annotations


def probe(value: int, flag: bool) -> int:
    """
    Summarize.

    :param value: see :external+demo:doc:`the demo docs <index>`.
    :param flag: a flag whose type renders as a role.
    """
    return value if flag else -value
