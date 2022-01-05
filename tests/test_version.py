from __future__ import annotations


def test_version() -> None:
    from sphinx_autodoc_typehints import __version__

    assert __version__
