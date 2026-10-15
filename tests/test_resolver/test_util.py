from __future__ import annotations

import dataclasses
import importlib
import re
from operator import attrgetter
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from sphinx import addnodes
from sphinx.environment import BuildEnvironment

from sphinx_autodoc_typehints._annotations import MyTypeAliasForwardRef
from sphinx_autodoc_typehints._resolver._util import collect_documented_type_aliases, get_obj_location

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.testing.util import SphinxTestApp


def _typed_func(x: int, y: str) -> bool: ...


class _BackfillClass:
    def method(self, x: int) -> str: ...


def test_get_obj_location_with_function() -> None:
    location = get_obj_location(_typed_func)
    assert location is not None
    assert location.endswith(".py:" + str(_typed_func.__code__.co_firstlineno))
    assert "test_util.py" in location


def test_get_obj_location_with_class() -> None:
    location = get_obj_location(_BackfillClass)
    assert location is not None
    assert "test_util.py" in location


def test_get_obj_location_non_inspectable() -> None:
    assert get_obj_location(42) is None


def test_get_obj_location_of_generated_code() -> None:
    @dataclasses.dataclass
    class Generated:
        value: int

    assert get_obj_location(Generated.__init__) is None


def test_get_obj_location_no_source_lines() -> None:
    with patch("sphinx_autodoc_typehints._resolver._util.inspect.getsourcelines", side_effect=OSError):
        location = get_obj_location(_typed_func)
    assert location is not None
    assert location.endswith(".py")
    assert ":" not in location.rsplit("/", 1)[-1]


def _make_env_with_types(type_names: list[str]) -> Any:
    obj_info = MagicMock()
    obj_info.objtype = "type"
    py_objects = dict.fromkeys(type_names, obj_info)
    domain = MagicMock()
    domain.objects = py_objects
    env = create_autospec(BuildEnvironment, instance=True)
    env.get_domain.return_value = domain
    return env


def test_collect_documented_type_aliases_no_annotations() -> None:
    env = _make_env_with_types(["mymod.EncoderHook", "mymod.TagHook"])
    obj = MagicMock(spec=[])
    deferred, eager = collect_documented_type_aliases(obj, "mymod", env)
    assert "EncoderHook" in deferred
    assert "TagHook" in deferred
    assert isinstance(deferred["EncoderHook"], MyTypeAliasForwardRef)
    assert eager == {}


@pytest.mark.parametrize(
    "attr",
    [
        pytest.param("func", id="written-as-the-type"),
        pytest.param("lam", id="lambda"),
        pytest.param("Point.__init__", id="generated-without-source"),
    ],
)
def test_collect_documented_type_aliases_ignores_annotations_not_written_as_the_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest, attr: str
) -> None:
    name = re.sub(r"\W", "_", request.node.name)
    (tmp_path / f"{name}.py").write_text(
        "from dataclasses import dataclass\n\n"
        "MyAlias = int\n\n\n"
        "def func(x: int) -> None: ...\n\n\n"
        "lam = lambda x: None\n"
        "lam.__annotations__ = {'x': int}\n\n\n"
        "@dataclass\n"
        "class Point:\n"
        "    x: int\n"
    )
    monkeypatch.syspath_prepend(tmp_path)
    obj = attrgetter(attr)(importlib.import_module(name))
    _, eager = collect_documented_type_aliases(obj, name, _make_env_with_types([f"{name}.MyAlias"]))
    assert eager == {}


@pytest.mark.parametrize(
    "documented",
    [pytest.param("other.Foo", id="other-module"), pytest.param("mymod.sub.Foo", id="submodule")],
)
def test_collect_documented_type_aliases_ignores_other_module_types(documented: str) -> None:
    env = _make_env_with_types([documented])
    obj = MagicMock(spec=[])
    deferred, eager = collect_documented_type_aliases(obj, "mymod", env)
    assert "Foo" not in deferred
    assert eager == {}


@pytest.mark.parametrize(
    "documented",
    [pytest.param("am.Vector", id="module"), pytest.param("am.Ops.Vector", id="class-body")],
)
def test_collect_documented_type_aliases_sees_the_scopes_around_a_method(documented: str) -> None:
    deferred, _ = collect_documented_type_aliases(MagicMock(spec=[]), "am.Ops", _make_env_with_types([documented]))
    assert list(deferred) == ["Vector"]


def test_collect_documented_type_aliases_ignores_unqualified_names() -> None:
    env = _make_env_with_types(["EncoderHook"])
    obj = MagicMock(spec=[])
    deferred, eager = collect_documented_type_aliases(obj, "cbor2", env)
    assert "EncoderHook" not in deferred
    assert eager == {}


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(NameError("Callable"), id="name-error"),
        pytest.param(TypeError("type 'DiGraph' is not subscriptable"), id="type-error"),
        pytest.param(ValueError("a shape takes an int"), id="value-error"),
    ],
)
def test_collect_documented_type_aliases_annotations_error(error: Exception) -> None:
    """PEP 649 lazy annotation evaluation raising (NameError for TYPE_CHECKING-only names, TypeError
    for subscripting a non-generic class) must not propagate (issue #712)."""

    class _AnnotationsRaiser:
        @property
        def __annotations__(self) -> dict[str, object]:  # ruff:ignore[bad-dunder-method-name]
            raise error

    env = _make_env_with_types(["mymod.MyType"])
    deferred, eager = collect_documented_type_aliases(_AnnotationsRaiser(), "mymod", env)
    assert "MyType" in deferred
    assert eager == {}


@pytest.mark.parametrize(
    ("rst", "expected"),
    [
        pytest.param(
            ".. autofunction:: dropped_module.compare",
            '* **kind** ("Engine"["Any"] | "None") -- the kind',
            id="parameter",
        ),
        pytest.param(
            ".. autofunction:: dropped_module.compare",
            '* **spare** ("Engine"["str"] | "Engine"["bytes"]) -- the spare',
            id="union-the-dropped-arguments-told-apart",
        ),
        pytest.param(".. autofunction:: dropped_module.compare", '"Engine"["int"]', id="return"),
        pytest.param(".. autofunction:: dropped_module.quoted", '**kind** ("Engine"["int"]) -- the kind', id="quoted"),
        pytest.param(".. autofunction:: dropped_module.pick", '* **kind** ("Engine"["str"]) → "str"', id="overload"),
        pytest.param(
            ".. autoclass:: dropped_module.Column", '* **kind** ("Engine"["Any"]) -- the kind', id="class-body-ivar"
        ),
        pytest.param(
            ".. autoclass:: dropped_module.Column",
            '* **other** ("Engine"["str"] | "None") -- the other',
            id="instance-ivar",
        ),
    ],
)
@pytest.mark.sphinx("text", testroot="dropped-arguments")
@pytest.mark.usefixtures("wide_text_output")
def test_field_type_keeps_the_arguments_a_subscription_drops(
    app: SphinxTestApp, write_rst: Callable[[str], None], rst: str, expected: str
) -> None:
    write_rst(rst)
    app.build()

    assert expected in [line.strip() for line in (Path(app.outdir) / "index.txt").read_text().splitlines()]


@pytest.mark.sphinx(
    "text",
    testroot="dropped-arguments",
    confoverrides={"typehints_use_signature": True, "typehints_use_signature_return": True},
)
@pytest.mark.usefixtures("wide_text_output")
def test_kept_signature_keeps_the_arguments_a_subscription_drops(
    app: SphinxTestApp, write_rst: Callable[[str], None]
) -> None:
    write_rst(".. autofunction:: dropped_module.compare")
    app.build()

    assert (Path(app.outdir) / "index.txt").read_text().splitlines()[0] == (
        "dropped_module.compare(kind: Engine[Any] | None, spare: Engine[str] | Engine[bytes]) -> Engine[int]"
    )


@pytest.mark.sphinx(
    "text",
    testroot="dropped-arguments",
    confoverrides={"typehints_use_signature": True, "typehints_use_signature_return": True},
)
def test_kept_signature_links_the_class_whose_subscription_drops_the_arguments(
    app: SphinxTestApp, write_rst: Callable[[str], None]
) -> None:
    write_rst(".. autofunction:: dropped_module.quoted")
    app.build()

    signature = next(app.env.get_doctree("index").findall(addnodes.desc_signature))
    assert [ref["reftarget"] for ref in signature.findall(addnodes.pending_xref)] == ["engines.Engine", "int", "None"]


@pytest.mark.parametrize(
    ("function", "expected"),
    [
        pytest.param("sliced", '**kind** ("Engine") -- the kind', id="slice-a-call-cannot-take"),
        pytest.param("reassigned", '**kind** ("Engine") -- the kind', id="source-that-no-longer-evaluates"),
        pytest.param("aliased", '**kind** ("list"["Engine"]) -- the kind', id="alias-holding-a-forward-reference"),
    ],
)
@pytest.mark.sphinx("text", testroot="dropped-arguments")
def test_field_type_keeps_the_evaluated_type_when_the_source_keeps_no_arguments(
    app: SphinxTestApp, write_rst: Callable[[str], None], function: str, expected: str
) -> None:
    write_rst(f".. autofunction:: dropped_module.{function}")
    app.build()

    assert expected in [line.strip() for line in (Path(app.outdir) / "index.txt").read_text().splitlines()]
