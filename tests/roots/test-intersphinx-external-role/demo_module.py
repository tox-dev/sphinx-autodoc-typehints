from __future__ import annotations


def probe(x: int, flag: bool) -> int:
    """
    Summarize.

    :param x: see :external+demo:doc:`the demo docs <index>`.
    :param flag: a flag whose type renders as a role.
    """
    return x if flag else -x
