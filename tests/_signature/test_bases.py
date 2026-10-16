from __future__ import annotations

from typing import TYPE_CHECKING, Final

from pytest import MarkDecorator, mark, param

if TYPE_CHECKING:
    from conftest import BuildText

pytestmark: Final[MarkDecorator] = mark.sphinx("text", testroot="bases")


def _bases(text: str) -> str:
    # the text builder wraps each literal in double quotes
    return next(line for line in text.splitlines() if "Bases:" in line).strip().replace('"', "")


@mark.parametrize(
    ("name", "bases"),
    [
        param("Plain", "Bases: object", id="object"),
        param("Child", "Bases: Plain", id="class"),
        param("Open", "Bases: Generic[T]", id="generic"),
        param("Pairs", "Bases: Mapping[str, int]", id="subscripted-generic"),
        param("Sub", "Bases: Stack[X], Generic[X]", id="pep-695-type-parameter"),
        param("Reader", "Bases: Protocol", id="protocol"),
        param("FromMock", "Bases: Mocked", id="mocked-base-left-to-sphinx"),
        param("UsesHidden", "Bases: Stack[bytes | None]", id="alias-not-documented-expands"),
    ],
)
def test_bases_render_as_a_field_type(build_text: BuildText, name: str, bases: str) -> None:
    text = build_text(f".. autoclass:: bases_module.{name}\n   :show-inheritance:\n")

    assert _bases(text) == bases


@mark.sphinx(confoverrides={"typehints_fully_qualified": True})
def test_bases_follow_fully_qualified(build_text: BuildText) -> None:
    text = build_text(".. autoclass:: bases_module.Pairs\n   :show-inheritance:\n")

    assert _bases(text) == "Bases: collections.abc.Mapping[str, int]"


@mark.sphinx(
    confoverrides={
        "typehints_fully_qualified": True,
        "typehints_fixup_module_name": lambda module: "public" if module == "bases_module" else module,
    }
)
def test_bases_follow_fixup_module_name(build_text: BuildText) -> None:
    text = build_text(".. autoclass:: bases_module.Child\n   :show-inheritance:\n")

    assert _bases(text) == "Bases: public.Plain"


@mark.sphinx(confoverrides={"typehints_formatter": lambda annotation, _config: "<int>" if annotation is int else None})
def test_bases_follow_typehints_formatter(build_text: BuildText) -> None:
    text = build_text(".. autoclass:: bases_module.Pairs\n   :show-inheritance:\n")

    assert _bases(text) == "Bases: Mapping[str, <int>]"
