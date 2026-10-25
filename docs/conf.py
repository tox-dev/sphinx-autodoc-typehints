# ruff:ignore[implicit-namespace-package]  # Sphinx runs this file by path, it is not part of a package
"""Configuration for Sphinx."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from importlib.metadata import version as package_version
from pathlib import Path
from typing import TYPE_CHECKING, Final

from docutils import nodes

if TYPE_CHECKING:
    from sphinx.application import Sphinx

_HERE: Final[Path] = Path(__file__).parent
sys.path.insert(0, str(_HERE / "_ext"))

project, company = "sphinx-autodoc-typehints", "tox-dev"
now = datetime.now(tz=UTC)
release = package_version(project)
version = ".".join(release.split(".")[:2])
copyright = f"2016-{now.date().year}, {company}"  # ruff:ignore[builtin-variable-shadowing]  # the name Sphinx reads
extensions = [
    "live_example",
    "option_reference",
    "sphinx_llm.txt",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_sitemap",
    "sphinxcontrib.mermaid",
    "sphinxcontrib.towncrier.ext",
    "sphinxext.opengraph",
]
# raw output lets the browser render the diagrams, so they follow furo's light and dark toggle; neutral pairs grays with
# the semantic tints docs/_static/custom.css applies
mermaid_output_format = "raw"
mermaid_light_theme = "neutral"
# the default fixed 500px height pads a wide diagram with empty bands, let each keep its own aspect ratio
mermaid_height = "auto"

towncrier_draft_autoversion_mode = "draft"
# keep the build green right after a release, when no fragments remain
towncrier_draft_include_empty = True
towncrier_draft_working_directory = _HERE.parent

# build the markdown for llms.txt after the HTML, from the same doctrees, so the live examples render once
llms_txt_build_parallel = False

copybutton_prompt_is_regexp = True
copybutton_prompt_text = r">>> |\.\.\. |\$ "

# Read the Docs serves pages under /<language>/<version>/, a bare domain would point the canonical link, og:url and
# sitemap at pages that 404
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "https://sphinx-autodoc-typehints.readthedocs.io/en/stable/")
sitemap_url_scheme = "{link}"

ogp_site_url = html_baseurl
ogp_social_cards = {"enable": False}
ogp_description_length = 200
ogp_image = f"{html_baseurl}_static/icon-tile.svg"

html_theme = "furo"
html_logo, html_favicon = "_static/icon.svg", "_static/favicon.svg"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_title, html_last_updated_fmt = project, now.isoformat()
pygments_style, pygments_dark_style = "sphinx", "monokai"
autosectionlabel_prefix_document = True

intersphinx_mapping = {
    "attrs": ("https://www.attrs.org/en/stable", None),
    "numpydoc": ("https://numpydoc.readthedocs.io/en/latest", None),
    "python": ("https://docs.python.org/3", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master", None),
}
nitpicky = True
# towncrier news fragments are rST snippets folded into changelog.rst at release, not standalone pages
exclude_patterns = ["changelog/*"]
extlinks = {
    "issue": ("https://github.com/tox-dev/sphinx-autodoc-typehints/issues/%s", "issue #%s"),
    "pr": ("https://github.com/tox-dev/sphinx-autodoc-typehints/pull/%s", "PR #%s"),
    "user": ("https://github.com/%s", "@%s"),
}


def setup(app: Sphinx) -> None:
    """Keep event links and repeated release labels resolvable."""
    app.add_object_type("event", "event")
    app.connect("doctree-read", _label_release_categories, priority=400)


def _label_release_categories(app: Sphinx, document: nodes.document) -> None:
    if app.env.current_document.docname != "changelog":
        return
    for section in document.findall(nodes.section):
        if section[0].astext() not in {
            "Added",
            "Changes",
            "Fixed",
            "Documentation",
            "Breaking changes",
            "Security",
            "Performance",
            "Deprecated",
            "Removed",
            "Packaging",
        }:
            continue
        if anchor := next((identifier for identifier in section["ids"] if identifier.startswith("release-")), None):
            section["ids"] = [anchor]
            section[0].rawsource = anchor
