from __future__ import annotations

from re import findall
from shutil import copytree
from textwrap import dedent
from threading import local
from typing import TYPE_CHECKING
from zlib import compress

from pytest import fixture, mark, param

from sphinx_autodoc_typehints._render import format_annotation, keep_type_mapping
from sphinx_autodoc_typehints._render.intersphinx import type_mapping

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from conftest import BuildText
    from sphinx.config import Config
    from sphinx.environment import BuildEnvironment
    from sphinx.testing.util import SphinxTestApp


@mark.parametrize(
    ("entries", "expected"),
    [
        param("threading.local py:class 1 - -", {"_thread._local": "threading.local"}, id="documented-elsewhere"),
        param(
            dedent("""\
                threading.local py:class 1 - -
                _thread._local py:class 1 - -
            """),
            {},
            id="documented-under-its-own-name",
        ),
        param(
            dedent("""\
                dict py:class 1 - -
                wsgiref.types.WSGIEnvironment py:data 1 - -
            """),
            {},
            id="builtin-alias",
        ),
        param("nonexistent_module.SomeClass py:class 1 - -", {}, id="unimportable"),
        param("threading.NoSuchAttribute py:class 1 - -", {}, id="missing-attribute"),
        param("render_inventory_targets.THING py:data 1 - -", {}, id="no-qualified-name"),
        param("render_inventory_targets.UnionClass py:class 1 - -", {}, id="union-class"),
        param("render_inventory_targets.UnionAlias py:data 1 - -", {}, id="typing-union"),
    ],
)
def test_keep_type_mapping(
    config: Config, inventory_env: Callable[[str], BuildEnvironment], entries: str, expected: dict[str, str]
) -> None:
    keep_type_mapping(config, inventory_env(entries))
    assert type_mapping(config) == expected


@fixture(name="inventory_env")
def inventory_env_fixture(
    make_app: Callable[..., SphinxTestApp], rootdir: Path, tmp_path: Path
) -> Callable[[str], BuildEnvironment]:
    def load(entries: str) -> BuildEnvironment:
        (inventory := tmp_path / "objects.inv").write_bytes(
            dedent("""\
                # Sphinx inventory version 2
                # Project: docs
                # Version: 1
                # The remainder of this file is compressed using zlib.
            """).encode()
            + compress(entries.encode())
        )
        srcdir = copytree(rootdir / "test-render-intersphinx", tmp_path / "src")
        mapping = {"docs": ("https://example.org/", str(inventory))}
        return make_app("html", srcdir=srcdir, confoverrides={"intersphinx_mapping": mapping}).env

    return load


@mark.sphinx("html", testroot="render-types")
def test_keep_type_mapping_without_intersphinx_drops_the_kept_one(
    app: SphinxTestApp, config: Config, inventory_env: Callable[[str], BuildEnvironment]
) -> None:
    keep_type_mapping(config, inventory_env("threading.local py:class 1 - -"))
    keep_type_mapping(config, app.env)
    assert type_mapping(config) == {}


def test_type_mapping_before_a_build(config: Config) -> None:
    assert type_mapping(config) == {}


def test_keep_type_mapping_renders_the_documented_name(
    config: Config, inventory_env: Callable[[str], BuildEnvironment]
) -> None:
    keep_type_mapping(config, inventory_env("threading.local py:class 1 - -"))
    assert format_annotation(local, config) == ":py:class:`~threading.local`"


@mark.sphinx("html", testroot="pyi-stubs")
def test_stub_types_link_to_the_inventory(build_text: BuildText) -> None:
    assert set(findall(r'href="(https://docs[^"]*)"', build_text(".. autofunction:: stub_mod.transform"))) == {
        "https://docs.python.org/3/library/stdtypes.html#list",
        "https://docs.python.org/3/library/stdtypes.html#str",
    }
