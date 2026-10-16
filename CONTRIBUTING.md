# Contributing to sphinx-autodoc-typehints

Thank you for your interest in contributing. This guide covers how to set up a development environment, how the
extension is laid out, and what a pull request needs before it can merge.

## Code of Conduct

Be respectful and constructive in all interactions. We aim to keep a welcoming environment for every contributor.

## Getting Started

The project runs every development task through [tox](https://tox.wiki). Install it with its uv plugin, then list the
environments:

```bash
uv tool install tox --with tox-uv
tox list
```

## Development Workflow

### Running Tests

Run the suite on one interpreter with `tox r -e 3.14`, or on several with `tox r -e 3.12,3.15`. Each run measures
coverage and fails below 100%, and `diff-cover` holds the lines your branch changes against `origin/main` to 100% too.
Point it at another base with the `DIFF_AGAINST` environment variable, for example `DIFF_AGAINST=upstream/main`.

To run a single test file while you work, use the interpreter tox created:
`.tox/3.14/bin/python -m pytest tests/_render`.

### Code Quality Checks

`tox r -e fix` runs pre-commit, which formats and lints with ruff, formats Markdown with mdformat, and checks the import
layers with import-linter (see [Architecture](#architecture)). `tox r -e type` type checks the package and the tests
with [ty](https://github.com/astral-sh/ty).

### Package Metadata

`tox r -e pkg_meta` builds the sdist and wheel, then checks the long description with twine and the wheel layout with
check-wheel-contents.

### Development Environment

`tox r -e dev` creates `.tox/dev/` with an editable install and every development dependency, for your editor to use.

## Architecture

The extension hooks into Sphinx autodoc: it reads the annotations of each object autodoc documents and writes them into
the signature, the docstring fields and the header of the entry. Everything lives under `src/sphinx_autodoc_typehints/`,
split into layered packages.

### Layers

Each layer imports only from the layers below it. import-linter enforces the order from `pyproject.toml`, so an import
pointing up fails `tox r -e fix`.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"fontFamily": "sans-serif", "lineColor": "#768390", "primaryTextColor": "#1f2328"}}}%%
flowchart TB
    extension["_extension<br/>setup, event wiring"]
    config["_config<br/>options, validation"]
    patches["_patches<br/>autodoc, napoleon, docutils patches"]
    docstring["_docstring<br/>docstring fields"]
    signature["_signature<br/>signatures and headers"]
    documented["_documented<br/>the documented object"]
    render["_render<br/>types to reST"]
    resolve["_resolve<br/>annotations to types"]
    foundation["foundation<br/>_objects, _refs, _state, _warnings, _private_imports, _types"]

    extension --> config & patches
    config --> docstring & signature
    patches --> docstring & signature
    docstring --> documented
    signature --> documented
    documented --> render & resolve
    render --> foundation
    resolve --> foundation

    linkStyle default stroke:#768390,stroke-width:1.5px
    classDef wiring fill:#cfe4ff,stroke:#1f6feb,color:#0b1f3a
    classDef handler fill:#ffe3a3,stroke:#d29200,color:#3a2c00
    classDef model fill:#e8dcff,stroke:#8250df,color:#2a0f5c
    classDef engine fill:#d5f5d0,stroke:#2da44e,color:#0d2b12
    classDef base fill:#e6e9ed,stroke:#6e7781,color:#1f2328
    class extension,config,patches wiring
    class docstring,signature handler
    class documented model
    class render,resolve engine
    class foundation base
```

Packages on the same level, such as `_render` and `_resolve`, don't import each other. When rendering needs something
from resolution, `_documented` passes it in, for example the guard binder typed by the `GuardBinder` protocol in
`_render/context.py`. Every package `__init__.py` exports through `__all__` only the names another layer imports, and
every module opens with a docstring stating what it owns.

### Folder layout

| Path                  | Responsibility                                                                                                                                                                                                       |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_extension.py`       | `setup`: registers the options, roles, directive and post-transform, connects the event handlers and installs the patches                                                                                            |
| `_config.py`          | The configuration options and their validation                                                                                                                                                                       |
| `_patches/`           | Monkeypatches to autodoc, napoleon and docutils                                                                                                                                                                      |
| `_docstring/`         | The `autodoc-process-docstring` handler, which writes parameter, return, attribute and other fields                                                                                                                  |
| `_docstring/formats/` | One subpackage per docstring style the extension edits: `field_list` (reST field lists), `napoleon` output and `numpydoc` sections                                                                                   |
| `_signature/`         | The `autodoc-process-signature` handler, and `header/`, which rewrites the header Sphinx builds: overload lines, type parameters and the type of data                                                                |
| `_documented/`        | What the extension works out about the documented object: its hints, overloads, members and render scope                                                                                                             |
| `_render/`            | Turning types into reST cross-references; `annotation/` walks one annotation, `deferred.py` chooses alias links once every document is read                                                                          |
| `_resolve/`           | Turning annotations into types: `evaluate/` evaluates them, `guards/` runs `if TYPE_CHECKING:` blocks into an overlay, `backfill/` reads type comments and `.pyi` stubs                                              |
| foundation modules    | Helpers every layer may use: `_objects` (unwrapping, owners), `_refs`, `_state` (environment records), `_warnings`, `_private_imports` (every private name read from a dependency or the standard library), `_types` |

Tests mirror this tree: tests for `src/sphinx_autodoc_typehints/_resolve/guards/run.py` live in
`tests/_resolve/guards/test_run.py`, and `src/sphinx_autodoc_typehints/_config.py` maps to `tests/test__config.py`.
Sphinx projects that tests build live in `tests/roots/`.

### Event flow

Sphinx calls the extension at fixed points of a build. The handlers run in this order for each documented object, and
the deferred alias choice runs once every document is read:

```mermaid
%%{init: {"theme": "base", "themeVariables": {"fontFamily": "sans-serif", "actorBkg": "#cfe4ff", "actorBorder": "#1f6feb", "actorTextColor": "#0b1f3a", "actorLineColor": "#768390", "signalColor": "#768390", "signalTextColor": "#768390", "activationBkgColor": "#ffe3a3", "activationBorderColor": "#d29200", "noteBkgColor": "#e8dcff", "noteBorderColor": "#8250df", "noteTextColor": "#2a0f5c"}}}%%
sequenceDiagram
    participant S as Sphinx / autodoc
    participant Sig as _signature.handler
    participant D as _docstring.handler
    participant N as napoleon
    participant H as _signature.header
    participant R as _render.deferred

    Note over S,H: for each documented object
    S->>+Sig: autodoc-process-signature
    Sig-->>-S: types kept or stripped, one line per overload
    S->>+D: autodoc-process-docstring, priority 499
    D-->>-S: napoleon's input noted
    S->>+N: autodoc-process-docstring, priority 500
    N-->>-S: Google and NumPy sections as reST fields
    S->>+D: autodoc-process-docstring, priority 500
    D-->>-S: docstring lines with type fields
    S->>+H: object-description-transform
    H-->>-S: header with type parameters and data types
    Note over S,R: after every document is read
    S->>+R: post-transform DeferAliasChoice
    R-->>-S: link to the alias or its expanded value
```

### From annotation to rendered type

A docstring field and a signature line both go through the same resolution and rendering:

```mermaid
%%{init: {"theme": "base", "themeVariables": {"fontFamily": "sans-serif", "lineColor": "#768390", "primaryTextColor": "#1f2328"}}}%%
flowchart LR
    obj["documented object"] --> resolve
    subgraph resolve["_resolve"]
        direction TB
        guards["guards<br/>TYPE_CHECKING overlay"]
        evaluate["evaluate<br/>get_type_hints, source"]
        backfill["backfill<br/>type comments, stubs"]
        guards --> evaluate
        backfill --> evaluate
    end
    resolve --> hints["hints and aliases<br/>(_documented)"]
    hints --> render["_render.annotation<br/>reST role markup"]
    render --> field["docstring field<br/>(_docstring)"]
    render --> sig["signature or header<br/>(_signature)"]

    linkStyle default stroke:#768390,stroke-width:1.5px
    style resolve fill:#eef6ee,stroke:#2da44e,color:#0d2b12
    classDef input fill:#cfe4ff,stroke:#1f6feb,color:#0b1f3a
    classDef engine fill:#d5f5d0,stroke:#2da44e,color:#0d2b12
    classDef model fill:#e8dcff,stroke:#8250df,color:#2a0f5c
    classDef output fill:#ffe3a3,stroke:#d29200,color:#3a2c00
    class obj input
    class guards,evaluate,backfill,render engine
    class hints model
    class field,sig output
```

## Making Changes

### Fork and Branch

Fork the repository on GitHub, clone your fork, and create a branch from `main` with a descriptive name such as
`fix-overload-headers`.

### Code Style

Follow the patterns in the code around your change. `tox r -e fix` must pass, and every function, test and fixture
carries type annotations that `tox r -e type` accepts. A few conventions the linters don't catch:

- Keep functions between 20 and 50 lines, and pull a part into its own function only when two places call it.
- Comments explain why, never what. Private functions carry no docstrings.
- Quote code in comments and docstrings with single backticks.
- Write multi-line strings as triple-quoted `textwrap.dedent` text rather than `"\n"` escapes.
- Every `noqa` or `ty: ignore` names its code and gives the reason inline; a ty gap links the upstream
  [ty issue](https://github.com/astral-sh/ty/issues).

### Testing

Add a test for every bug fix and feature, in the test file that mirrors the module you change. The test must fail
without your change. Test through each package's exported names, parametrize near-duplicate cases with readable ids, and
mock only true boundaries such as the network.

### Documentation

The README is the documentation. Update it for any user-visible change; `tests/test_readme.py` builds its examples and
checks its option and warning tables against the code, so a stale example fails the suite. Format it with
`mdformat --wrap 120`, which `tox r -e fix` also runs.

## Submitting Changes

### Commit Messages

Follow Commitizen conventions with a gitmoji, `<emoji> <type>(<scope>): <summary>`, and an optional body explaining the
motivation. For example:

```
🐛 fix(overloads): keep an overload's ... default as written

An overload's default of ... means "has a default", so showing the
implementation's value there contradicted the overload's own annotation.
```

### Pull Requests

Make sure `tox r -e fix,type,3.12,3.15` passes, push to your fork and open a pull request against `main`. Describe the
problem and the change, and show the rendered output before and after where it changed. CI runs every supported Python
version, including the free-threaded builds.

## Getting Help

Check the existing [issues](https://github.com/tox-dev/sphinx-autodoc-typehints/issues) and the
[README](https://github.com/tox-dev/sphinx-autodoc-typehints#readme) before asking, then open an issue for bugs or
feature requests.

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.
