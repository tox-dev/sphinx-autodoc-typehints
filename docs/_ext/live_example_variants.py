# ruff:ignore[implicit-namespace-package]  # Sphinx loads this extension from a path conf.py puts on sys.path
"""Render live examples under each combination of a set of options, all in one Sphinx application in this process."""

from __future__ import annotations

from ast import literal_eval
from contextlib import contextmanager
from hashlib import sha256
from io import StringIO
from itertools import product
from logging import getLogger
from re import compile as compile_regex
from re import sub
from sys import modules, path
from typing import TYPE_CHECKING, Final, NamedTuple
from uuid import uuid4

from docutils.parsers.rst import directives, roles
from sphinx.application import Sphinx

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable
    from pathlib import Path

    from docutils.nodes import document
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment
    from sphinx.util.tags import Tags

# each example documents a module of its own, whose name its rendered pages replace
_MODULE: Final[str] = "live_example_module"
# every variant of an example documents the same objects, so all but one are duplicates of another variant's
_DUPLICATE: Final = compile_regex(r"duplicate (?:object|module) description of ")
# a link to an object of another variant of the same example points at the variant shown, so it stays on the page
_OTHER_PAGE: Final = compile_regex(r'href="(?![a-z][a-z0-9+.-]*:)[^"#]*#')

# how many options at once a probe moves away from their defaults
_PROBED: Final[int] = 2

_TEMPLATES: Final[str] = "_templates"
_BODY: Final[str] = "body.html"

type Combination = tuple[int, ...]


class Option(NamedTuple):
    """
    An option to pick: its name, the values it offers with its default first, and the option it needs switched on.

    `label` names it for a reader in a few words, and `group` is the heading it shows under.
    """

    name: str
    values: tuple[object, ...]
    depends_on: str
    label: str
    group: str


class Variants(NamedTuple):
    """
    What each example renders as under each combination of the options.

    `relevant` lists, for each example, the options that change it. `examples` maps, for each example, the key of a
    combination of only those options to the index of the page in `bodies`, which holds each distinct page once.
    """

    bodies: list[str]
    relevant: list[list[int]]
    examples: list[dict[str, int]]


class VariantBuildError(Exception):
    """Sphinx warned while building a variant, with the warnings as the message."""


def parse_options(lines: Iterable[str]) -> list[Option]:
    """
    Read the options from lines naming a group, each followed by its options indented below it.

    An option line reads `Label: name = default, other, ...`, and may end with `if other_option`.
    """
    options, group = [], ""
    for line in filter(str.strip, lines):
        if not line.startswith(" "):
            group = line.strip()
            continue
        label, _, setting = line.strip().partition(": ")
        name, _, rest = setting.partition(" = ")
        values, _, depends_on = rest.partition(" if ")
        options.append(Option(name.strip(), literal_eval(f"({values},)"), depends_on.strip(), label, group))
    return options


def combination_key(combination: Combination) -> str:
    """Name a combination by the index of the value it picks for each option."""
    return "".join(map(str, combination))


def render_variants(project: Path, options: list[Option], sources: list[str], module: str) -> Variants:
    """
    Render each example of `sources` under each combination of `options` that changes it.

    `project` holds the `conf.py` every variant shares. One Sphinx application documents each pair of combination and
    example as a page of its own, switching its configuration to the combination of the page it reads or writes. A
    first round renders each example with up to two options away from their defaults, which tells the options that
    change the example, alone or next to another; a second round renders the combinations of those. The pages show the
    module as `module`.
    """
    # a name of its own keeps the modules apart from those of any other render in this process
    prefix = f"{_MODULE}_{uuid4().hex}"
    for at, source in enumerate(sources):
        (project / f"{prefix}_{at}.py").write_text(f"{source}\n", encoding="utf-8")
    (project / "index.rst").write_text("", encoding="utf-8")
    probes = _probes(options)
    with _isolated(), _importable(project, prefix):
        nested = _application(
            project, options, lambda body, at: _rewrite(body, f"{prefix}_{at}", f"{at}{sources[at]}", module)
        )
        pages = _build(nested, prefix, {(probe, at) for probe in probes for at in range(len(sources))}, fresh=True)
        relevant = [
            [
                index
                for index in range(len(options))
                if any(
                    pages[probe, at] != pages[_canonical(options, _reset(probe, index)), at]
                    for probe in probes
                    if probe[index]
                )
            ]
            for at in range(len(sources))
        ]
        wanted = {
            (combination, at) for at in range(len(sources)) for combination in _combinations(options, relevant[at])
        }
        pages |= _build(nested, prefix, wanted - pages.keys(), fresh=False)
    bodies: dict[str, int] = {}
    examples = [
        {
            combination_key(combination): bodies.setdefault(pages[combination, at], len(bodies))
            for combination in _combinations(options, relevant[at])
        }
        for at in range(len(sources))
    ]
    return Variants(list(bodies), relevant, examples)


def _probes(options: list[Option]) -> list[Combination]:
    # an option may change an example only next to another one, as a return type shows only without the overloads
    ranges = [range(len(option.values)) for option in options]
    return sorted({_canonical(options, picked) for picked in product(*ranges) if sum(map(bool, picked)) <= _PROBED})


def _reset(combination: Combination, index: int) -> Combination:
    return tuple(0 if at == index else value for at, value in enumerate(combination))


def _combinations(options: list[Option], relevant: list[int]) -> list[Combination]:
    ranges = [range(len(option.values)) if index in relevant else range(1) for index, option in enumerate(options)]
    return sorted({_canonical(options, combination) for combination in product(*ranges)})


def _canonical(options: list[Option], combination: Combination) -> Combination:
    # an option needing another one that is switched off changes nothing, so it keeps its default
    names = [option.name for option in options]
    return tuple(
        0
        if option.depends_on
        and not options[names.index(option.depends_on)].values[combination[names.index(option.depends_on)]]
        else at
        for option, at in zip(options, combination, strict=True)
    )


@contextmanager
def _isolated() -> Generator[None]:
    # an application points the process-wide sphinx logger at its own streams and registers its directives and roles
    # with docutils, where the outer build registered its own; each build gets back what it had
    logger = getLogger("sphinx")
    handlers, filters, level, propagate = list(logger.handlers), list(logger.filters), logger.level, logger.propagate
    registered = directives._directives, roles._roles  # ruff:ignore[private-member-access]  # docutils has no API
    directives._directives, roles._roles = {}, {}  # ruff:ignore[private-member-access]  # docutils has no API
    try:
        yield
    finally:
        logger.handlers[:], logger.filters[:] = handlers, filters
        logger.setLevel(level)
        logger.propagate = propagate
        directives._directives, roles._roles = registered  # ruff:ignore[private-member-access]  # docutils has no API


@contextmanager
def _importable(project: Path, prefix: str) -> Generator[None]:
    path.insert(0, str(project))
    try:
        yield
    finally:
        path.remove(str(project))
        for name in [name for name in modules if name.startswith(prefix)]:
            del modules[name]


class _Nested(NamedTuple):
    app: Sphinx
    warnings: StringIO
    bodies: dict[str, str]


def _application(project: Path, options: list[Option], rewrite: Callable[[str, int], str]) -> _Nested:
    warnings, bodies = StringIO(), {}
    # the outer build registered the node classes already, so registering them again only overrides their visitors
    overrides = {"suppress_warnings": ["app.add_node"], "templates_path": [_TEMPLATES]}
    (project / _TEMPLATES).mkdir()
    (project / _TEMPLATES / _BODY).write_text("{{ body }}", encoding="utf-8")
    app = Sphinx(
        project,
        project,
        project / "_build",
        project / "_doctrees",
        "html",
        confoverrides=overrides,
        status=None,
        warning=warnings,
    )
    _switch_config(app, options)

    # the body is all a variant needs, so each page renders through a template holding nothing else; the links of a
    # variant depend on which variant the domain registered an object for last, so they compare only once rewritten
    def keep_body(_app: Sphinx, pagename: str, _template: str, context: dict[str, object], _doctree: object) -> str:
        if pagename.startswith("v"):
            bodies[pagename] = rewrite(str(context["body"]), int(pagename.rsplit("/", 1)[1]))
        return _BODY

    app.connect("html-page-context", keep_body)
    return _Nested(app, warnings, bodies)


def _switch_config(app: Sphinx, options: list[Option]) -> None:
    def apply(docname: str | None) -> None:
        picked = (
            tuple(map(int, docname.split("/", 1)[0][1:]))
            if docname and docname.startswith("v")
            else (0,) * len(options)
        )
        for option, at in zip(options, picked, strict=True):
            setattr(app.config, option.name, option.values[at])

    resolve = app.env.get_and_resolve_doctree

    # the post-transforms, which choose how an alias links, read the configuration while the page is written
    def get_and_resolve_doctree(docname: str, builder: Builder, *, tags: Tags) -> document:
        apply(docname)
        try:
            return resolve(docname, builder, tags=tags)
        finally:
            apply(None)

    def install(_app: Sphinx, env: BuildEnvironment) -> None:
        # set once the environment is pickled, which a function local to this one cannot be
        env.get_and_resolve_doctree = get_and_resolve_doctree  # ty: ignore[invalid-assignment]  # same signature

    def uninstall(_app: Sphinx, _exception: Exception | None) -> None:
        del app.env.get_and_resolve_doctree

    app.connect("source-read", lambda _app, docname, _source: apply(docname))
    app.connect("doctree-read", lambda _app, _doctree: apply(None))
    app.connect("env-check-consistency", install)
    app.connect("build-finished", uninstall)


def _build(
    nested: _Nested, prefix: str, pairs: Iterable[tuple[Combination, int]], *, fresh: bool
) -> dict[tuple[Combination, int], str]:
    app, warnings = nested.app, nested.warnings
    paths = {}
    for combination, at in pairs:
        (page := app.srcdir / f"v{combination_key(combination)}" / f"{at}.rst").parent.mkdir(exist_ok=True)
        page.write_text(f":orphan:\n\n.. automodule:: {prefix}_{at}\n   :members:\n", encoding="utf-8")
        paths[combination, at] = page
    if not paths:
        return {}
    # a first build writes every page, so a later one adding pages finds the search index it extends
    app.build(force_all=fresh, filenames=[] if fresh else list(paths.values()))
    if problems := [line for line in warnings.getvalue().splitlines() if line.strip() and not _DUPLICATE.search(line)]:
        raise VariantBuildError("\n".join(problems))
    return {(combination, at): nested.bodies[f"v{combination_key(combination)}/{at}"] for combination, at in paths}


def _rewrite(body: str, documented: str, example: str, module: str) -> str:
    named = _OTHER_PAGE.sub('href="#', sub(rf"\b{documented}\b", module, body))
    # the variants of an example share one prefix for their anchors, as only one of them shows at a time
    return sub(r'\b(id="|href="#)', rf"\g<1>{sha256(example.encode()).hexdigest()[:12]}-", named)


__all__ = [
    "Option",
    "VariantBuildError",
    "Variants",
    "combination_key",
    "parse_options",
    "render_variants",
]
