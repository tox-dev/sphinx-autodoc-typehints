# ruff:ignore[implicit-namespace-package]  # Sphinx loads this extension from a path conf.py puts on sys.path
"""The `live-example` directive: build an example module while the docs build, with and without this extension."""

from __future__ import annotations

from hashlib import sha256
from html import escape
from json import loads
from os import environ, sep
from pathlib import Path
from re import sub
from subprocess import PIPE, STDOUT, CalledProcessError, run  # ruff:ignore[suspicious-subprocess-import]  # runs Sphinx
from sys import executable, version
from tempfile import TemporaryDirectory
from textwrap import dedent, indent
from typing import TYPE_CHECKING, Final
from zlib import compress

from sphinx import __display_version__
from sphinx.ext.intersphinx import InventoryAdapter
from sphinx.util.docutils import SphinxDirective

from sphinx_autodoc_typehints import __file__ as extension_init

if TYPE_CHECKING:
    from docutils.nodes import Node
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import ExtensionMetadata

_SEPARATOR: Final[str] = "---"
_EXTENSION: Final[str] = "sphinx_autodoc_typehints"
_EXTENSION_FILES: Final[tuple[Path, ...]] = tuple(sorted(Path(extension_init).parent.rglob("*.py")))
# an edit to the extension changes what an example renders, so it has to miss the cache
_EXTENSION_DIGEST: Final[str] = sha256(b"".join(path.read_bytes() for path in _EXTENSION_FILES)).hexdigest()
_CONF_HEADER: Final[str] = f'extensions = ["sphinx.ext.autodoc", "{_EXTENSION}"]\n'
# the options of this extension stay in the namespace, where Sphinx alone ignores them
_BUILTIN_CONF: Final[str] = dedent(f"""\
    extensions = [name for name in extensions if name != "{_EXTENSION}"]
    autodoc_typehints = "description"
""")
_INDEX: Final[str] = ".. automodule:: mod\n   :members:\n"
_INVENTORIES: Final[str] = "inventories"
_LAYOUT: Final[str] = dedent("""\
    .. tab-set::
        :class: live-example

        .. tab-item:: conf.py

            .. code-block:: python

    {conf}

        .. tab-item:: mod.py

            .. code-block:: python

    {source}

        .. tab-item:: sphinx-autodoc-typehints
            :selected:

            .. raw:: html

    {rendered}

        .. tab-item:: Sphinx built-in

            .. raw:: html

    {builtin}
""")

type Inventories = dict[str, tuple[str, str]]


class LiveExample(SphinxDirective):
    """
    Build a module `mod` with `.. automodule:: mod`, and show its `conf.py`, its source and two rendered pages.

    The content holds the `conf.py` lines, a `---` line, then the source of the module. One page renders with this
    extension, the other with Sphinx's `autodoc_typehints = "description"` alone. The nested builds link the types
    through the inventories this build loaded.
    """

    has_content = True

    def run(self) -> list[Node]:
        """Lay out the `conf.py`, the source and both rendered pages as tabs, this extension's page in front."""
        if _SEPARATOR not in (lines := list(self.content)):
            msg = f"separate the conf.py lines from the module source with a {_SEPARATOR!r} line"
            raise self.error(msg)
        conf, source = "\n".join(lines[: (at := lines.index(_SEPARATOR))]), "\n".join(lines[at + 1 :])
        for path in _EXTENSION_FILES:
            self.env.note_dependency(str(path))
        cache = Path(self.env.doctreedir) / "live-examples"
        inventories = _inventories(self.env)
        try:
            rendered = _render(cache, conf, source, inventories)
        except CalledProcessError as exc:
            msg = f"the example fails to build:\n{exc.stdout}"
            raise self.error(msg) from exc
        try:
            builtin = _render(cache, f"{conf}\n{_BUILTIN_CONF}", source, inventories)
        except CalledProcessError as exc:
            builtin = _failure(exc.stdout)
        return self.parse_text_to_nodes(
            _LAYOUT.format(**{
                name: indent(text, " " * 12)
                for name, text in {"conf": conf, "source": source, "rendered": rendered, "builtin": builtin}.items()
            })
        )


def _inventories(env: BuildEnvironment) -> Inventories:
    folder = Path(env.doctreedir) / "live-examples" / _INVENTORIES
    return {name: (uri, str(folder / f"{name}.inv")) for uri, (name, _, _) in InventoryAdapter(env).cache.items()}


def _render(cache: Path, conf: str, source: str, inventories: Inventories) -> str:
    hashes = {name: sha256(Path(path).read_bytes()).hexdigest() for name, (_, path) in inventories.items()}
    key = (_EXTENSION_DIGEST, version, __display_version__, conf, source, hashes)
    digest = sha256(repr(key).encode()).hexdigest()
    if not (cached := cache / f"{digest}.html").exists():
        body = _build(conf, source, inventories)
        cache.mkdir(parents=True, exist_ok=True)
        # every example documents a module named mod, so its anchors need a prefix to stay unique on the page
        unique = sub(r'\b(id="|href="#)', rf"\g<1>{digest[:12]}-", body)
        cached.write_text(f'<div class="live-example-output">{unique}</div>', encoding="utf-8")
    return cached.read_text(encoding="utf-8")


def _build(conf: str, source: str, inventories: Inventories) -> str:
    with TemporaryDirectory() as scratch:
        (project := Path(scratch) / "project").mkdir()
        intersphinx = f'extensions = [*extensions, "sphinx.ext.intersphinx"]\nintersphinx_mapping = {inventories!r}\n'
        (project / "conf.py").write_text(f"{_CONF_HEADER}{conf}\n{intersphinx}", encoding="utf-8")
        (project / "mod.py").write_text(f"{source}\n", encoding="utf-8")
        (project / "index.rst").write_text(_INDEX, encoding="utf-8")
        try:
            run(  # ruff:ignore[subprocess-without-shell-equals-true]  # this interpreter running Sphinx on our files
                [executable, "-m", "sphinx", "-b", "json", "-W", "-q", str(project), str(project / "_build")],
                check=True,
                stdout=PIPE,
                stderr=STDOUT,
                text=True,
                env={**environ, "PYTHONPATH": str(project)},
            )
        except CalledProcessError as exc:
            # the scratch folder changes with every build, a cached page shows the path from the project instead
            exc.stdout = exc.stdout.replace(f"{project}{sep}", "")
            raise
        return loads((project / "_build" / "index.fjson").read_text(encoding="utf-8"))["body"]


def _failure(output: str) -> str:
    return (
        '<div class="live-example-output live-example-failure">'
        "<p>Sphinx alone fails to build this example with <code>-W</code>:</p>"
        f"<pre>{escape(output.strip())}</pre></div>"
    )


def _write_inventories(_app: Sphinx, env: BuildEnvironment, _docnames: list[str]) -> None:
    # the nested builds read the inventories this build downloaded, rather than each downloading them again
    for name, (uri, path) in _inventories(env).items():
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        # intersphinx joined each location to the project's address, the nested build joins it again
        base = f"{uri.rstrip('/')}/"
        items = [
            (entry, role, item)
            for role, objects in InventoryAdapter(env).named_inventory[name].items()
            for entry, item in objects.items()
        ]
        body = "".join(
            sorted(
                f"{entry} {role} 1 {item.uri.removeprefix(base)} {item.display_name}\n" for entry, role, item in items
            )
        )
        about = items[0][2]
        header = (
            f"# Sphinx inventory version 2\n# Project: {about.project_name}\n# Version: {about.project_version}\n"
            "# The remainder of this file is compressed using zlib.\n"
        )
        Path(path).write_bytes(header.encode() + compress(body.encode()))


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the `live-example` directive and the tabs it lays its output out in."""
    app.setup_extension("sphinx_design")
    app.add_directive("live-example", LiveExample)
    app.connect("env-before-read-docs", _write_inventories)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
