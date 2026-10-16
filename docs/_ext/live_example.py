# ruff:ignore[implicit-namespace-package]  # Sphinx loads this extension from a path conf.py puts on sys.path
"""
The `live-example` directive: build an example module while the docs build, with and without this extension.

After a `live-example-picker` directive, the examples of the page also render under each combination of the options it
lists, and the `conf.py` tab of each holds the controls that pick the combination every example shows.
"""

from __future__ import annotations

from hashlib import sha256
from html import escape
from json import dumps, loads
from os import environ, sep
from pathlib import Path
from re import sub
from shutil import copyfile
from subprocess import PIPE, STDOUT, CalledProcessError, run  # ruff:ignore[suspicious-subprocess-import]  # runs Sphinx
from sys import executable, version
from tempfile import TemporaryDirectory
from textwrap import dedent, indent
from typing import TYPE_CHECKING, Final
from zlib import compress, decompress

import live_example_variants
from docutils.nodes import Text, raw
from docutils.parsers.rst import directives
from live_example_selector import describe, selector
from live_example_variants import VariantBuildError, Variants, combination_key, parse_options, render_variants
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers.python import PythonLexer
from sphinx import __display_version__
from sphinx.ext.intersphinx import InventoryAdapter
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from sphinx.util.osutil import relative_uri

from sphinx_autodoc_typehints import __file__ as extension_init

if TYPE_CHECKING:
    from docutils.nodes import Node, document
    from live_example_variants import Option
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.util.typing import ExtensionMetadata, OptionSpec

_SEPARATOR: Final[str] = "---"
_EXTENSION: Final[str] = "sphinx_autodoc_typehints"
_EXTENSION_FILES: Final[tuple[Path, ...]] = tuple(sorted(Path(extension_init).parent.rglob("*.py")))
# an edit to the extension changes what an example renders, so it has to miss the cache
_EXTENSION_DIGEST: Final[str] = sha256(b"".join(path.read_bytes() for path in _EXTENSION_FILES)).hexdigest()
# so does an edit to the code rendering the variants of a picker
_RENDERER_DIGEST: Final[str] = sha256(Path(live_example_variants.__file__).read_bytes()).hexdigest()
_CONF_HEADER: Final[str] = f'extensions = ["sphinx.ext.autodoc", "{_EXTENSION}"]\n'
# the options of this extension stay in the namespace, where Sphinx alone ignores them
_BUILTIN_CONF: Final[str] = dedent(f"""\
    extensions = [name for name in extensions if name != "{_EXTENSION}"]
    autodoc_typehints = "description"
""")
_MODULE: Final[str] = "demo"
_INDEX: Final[str] = f".. automodule:: {_MODULE}\n   :members:\n"
_INVENTORIES: Final[str] = "inventories"
_CONF_TAB: Final[str] = dedent("""\
        .. tab-item:: conf.py

            .. code-block:: python

    {conf}

""")
_LAYOUT: Final[str] = dedent("""\
    .. tab-set::
        :class: live-example

    {conf_tab}    .. tab-item:: demo.py

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

_PICKER: Final[str] = "live_example_picker"
_LOGGER: Final[logging.SphinxLoggerAdapter] = logging.getLogger(__name__)

type Inventories = dict[str, tuple[str, str]]


class LiveExample(SphinxDirective):
    """
    Build a module `demo` with `.. automodule:: demo`, and show its `conf.py`, its source and two rendered pages.

    The content holds the `conf.py` lines, a `---` line, then the source of the module. One page renders with this
    extension, the other with Sphinx's `autodoc_typehints = "description"` alone. The nested builds link the types
    through the inventories this build loaded. After a `live-example-picker`, a `conf.py` button in the corner of
    this extension's page opens its controls in place of the `conf.py` tab.
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
        conf_tab = _CONF_TAB.format(conf=indent(conf, " " * 12))
        if (picker := self.env.current_document.get(_PICKER)) is not None:
            picker["examples"].append((conf, source))
            at = len(picker["examples"]) - 1
            # the controls open in the corner of the page they change, so a reader sees each choice take effect
            described = selector(picker["options"], _highlight(conf), picker["descriptions"], picker["reference"], at)
            rendered = (
                '<div class="lep-box"><details class="lep-details"><summary><span class="lep-toggle">conf.py</span>'
                '<span class="lep-hint">These options apply to every example on this page.</span></summary>'
                f"{described}</details>"
                f'<div class="live-example-output" data-live-example="{at}">{_marker(at)}</div></div>'
            )
            conf_tab = ""
        else:
            try:
                rendered = _render(cache, conf, source, inventories)
            except CalledProcessError as exc:
                msg = f"the example fails to build:\n{exc.stdout}"
                raise self.error(msg) from exc
        try:
            builtin = _render(cache, f"{conf}\n{_BUILTIN_CONF}", source, inventories)
        except CalledProcessError as exc:
            builtin = _failure(exc.stdout)
        texts = {"source": source, "rendered": rendered, "builtin": builtin}
        return self.parse_text_to_nodes(
            _LAYOUT.format(conf_tab=conf_tab, **{name: indent(text, " " * 12) for name, text in texts.items()})
        )


class LiveExamplePicker(SphinxDirective):
    """
    Render the live examples after it on the page under each combination of the options its content lists.

    The content names a group on each unindented line, and lists its options on the indented lines below, each as
    `Label: name = default, other, ...`, ending with `if other_option` to vary only while that option holds a true
    value. The `reference` option names the page whose `.. confval::` entries describe the options. The examples share
    one `conf.py`, and a `conf.py` button in the corner of each rendered page opens the controls, whose choice every
    example on the page follows.
    One Sphinx application renders all the variants.
    """

    has_content = True
    option_spec: OptionSpec = {"reference": directives.unchanged_required}  # ruff:ignore[mutable-class-default]  # docutils declares it an instance attribute

    def run(self) -> list[Node]:
        """Leave a placeholder for the options and the script, filled in once the page's examples are known."""
        reference = self.options["reference"]
        self.env.note_dependency(str(path := self.env.doc2path(reference)))
        descriptions = describe(path.read_text(encoding="utf-8"))
        options = parse_options(self.content)
        for option in options:
            if option.name not in descriptions:
                _LOGGER.warning(
                    "no confval entry of %s describes %s", reference, option.name, location=self.get_location()
                )
        self.env.current_document[_PICKER] = {
            "options": options,
            "descriptions": descriptions,
            # the HTML builders name a page `<docname>.html`, and `env.app` is gone in Sphinx 11
            "reference": relative_uri(f"{self.env.docname}.html", f"{reference}.html"),
            "examples": [],
        }
        return [raw("", _marker("picker"), format="html")]


def _marker(name: object) -> str:
    return f"<!--live-example-{name}-->"


def _highlight(code: str) -> str:
    return highlight(code, PythonLexer(), HtmlFormatter(nowrap=True))


def _fill_picker(app: Sphinx, doctree: document) -> None:
    if (picker := app.env.current_document.get(_PICKER)) is None:
        return
    options: list[Option] = picker["options"]
    if len(confs := {conf for conf, _ in picker["examples"]}) != 1:
        _LOGGER.warning("the examples under a live-example-picker need one conf.py they all share", location=doctree)
        return
    conf = confs.pop()
    try:
        variants = _render_variants(app.env, conf, options, [source for _, source in picker["examples"]])
    except VariantBuildError as exc:
        _LOGGER.warning("the examples fail to build:\n%s", exc, location=doctree)
        return
    data = f"liveExamplePicker.receive({dumps(variants._asdict())});\n"
    stored = Path(app.env.doctreedir) / "live-examples" / "pickers" / f"{sha256(data.encode()).hexdigest()}.js"
    stored.parent.mkdir(parents=True, exist_ok=True)
    stored.write_text(data, encoding="utf-8")
    static = f"{'../' * app.env.docname.count('/')}_static/"
    about = {
        "options": [
            {
                "name": option.name,
                "values": option.values,
                "dependsOn": option.depends_on,
                "lines": [_highlight(f"{option.name} = {value!r}") for value in option.values],
            }
            for option in options
        ],
        "conf": _highlight(conf),
        "data": f"{static}live-examples/{stored.name}",
    }
    panel = (
        f'<script type="application/json" id="live-example-picker">{dumps(about).replace("</", "<\\/")}</script>'
        f'<script src="{static}live-example-picker.js" defer></script>'
    )
    for node in doctree.findall(raw):
        text = node.astext()
        if text == _marker("picker"):
            text, node["live_example_data"] = panel, str(stored)
        for at, mapping in enumerate(variants.examples):
            text = text.replace(_marker(at), variants.bodies[mapping[combination_key((0,) * len(options))]])
        node.replace(node[0], Text(text))


def _render_variants(env: BuildEnvironment, conf: str, options: list[Option], sources: list[str]) -> Variants:
    inventories = _inventories(env)
    hashes = {name: sha256(Path(path).read_bytes()).hexdigest() for name, (_, path) in inventories.items()}
    key = (_EXTENSION_DIGEST, _RENDERER_DIGEST, version, __display_version__, conf, options, sources, hashes)
    cached = Path(env.doctreedir) / "live-examples" / "variants" / f"{sha256(repr(key).encode()).hexdigest()}.json.z"
    if not cached.exists():
        with TemporaryDirectory() as scratch:
            variants = render_variants(_project(Path(scratch), conf, inventories), options, sources, _MODULE)
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(compress(dumps(variants._asdict()).encode()))
    return Variants(**loads(decompress(cached.read_bytes())))


def _copy_picker_data(
    app: Sphinx, _pagename: str, _template: str, _context: dict[str, object], doctree: document | None
) -> None:
    for node in doctree.findall(raw) if doctree is not None else ():
        if stored := node.get("live_example_data"):
            (target := Path(app.outdir) / "_static" / "live-examples" / Path(stored).name).parent.mkdir(
                parents=True, exist_ok=True
            )
            copyfile(stored, target)


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
        # every example documents a module named demo, so its anchors need a prefix to stay unique on the page
        unique = sub(r'\b(id="|href="#)', rf"\g<1>{digest[:12]}-", body)
        cached.write_text(f'<div class="live-example-output">{unique}</div>', encoding="utf-8")
    return cached.read_text(encoding="utf-8")


def _build(conf: str, source: str, inventories: Inventories) -> str:
    with TemporaryDirectory() as scratch:
        project = _project(Path(scratch), conf, inventories)
        (project / f"{_MODULE}.py").write_text(f"{source}\n", encoding="utf-8")
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


def _project(scratch: Path, conf: str, inventories: Inventories) -> Path:
    (project := scratch / "project").mkdir()
    intersphinx = f'extensions = [*extensions, "sphinx.ext.intersphinx"]\nintersphinx_mapping = {inventories!r}\n'
    (project / "conf.py").write_text(f"{_CONF_HEADER}{conf}\n{intersphinx}", encoding="utf-8")
    return project


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
    """Register the `live-example` and `live-example-picker` directives and the tabs they lay their output out in."""
    app.setup_extension("sphinx_design")
    app.add_directive("live-example", LiveExample)
    app.add_directive("live-example-picker", LiveExamplePicker)
    app.connect("env-before-read-docs", _write_inventories)
    app.connect("doctree-read", _fill_picker)
    app.connect("html-page-context", _copy_picker_data)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
