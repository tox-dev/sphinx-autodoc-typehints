from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pytest import mark, param

from sphinx_autodoc_typehints._render import as_field_type, as_signature_type

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.config import Config

    from _render.conftest import MakeConfig
    from sphinx_autodoc_typehints._types import Annotation


@mark.parametrize(
    ("render", "hint", "short_literals", "expected"),
    [
        param(
            as_field_type,
            Literal["a"],
            False,
            (
                r":sphinx_autodoc_typehints_type:`\:py\:data\:\`\~typing.Literal\`\\ \\\["
                r"\:sphinx\_autodoc\_typehints\_value\:\`\'a\'\`\]`"
            ),
            id="field-subscript",
        ),
        param(
            as_field_type,
            Literal["a"],
            True,
            r":sphinx_autodoc_typehints_type:`\:sphinx\_autodoc\_typehints\_value\:\`\'a\'\``",
            id="field-short",
        ),
        param(as_signature_type, Literal["a"], False, "~typing.Literal['a']", id="signature-subscript"),
        param(as_signature_type, Literal["a"], True, "'a'", id="signature-inline-literal"),
        param(as_signature_type, Path, False, "~pathlib.Path", id="signature-role"),
        param(as_signature_type, ..., False, "...", id="signature-titled-role"),
        param(as_signature_type, dict[str, int], False, "dict[str, int]", id="signature-escaped-character"),
        param(as_signature_type, Literal["`"], True, "'`'", id="signature-escaped-backtick-in-role"),
    ],
)
def test_rendered_type(
    make_config: MakeConfig,
    render: Callable[[Annotation, Config], str],
    hint: Annotation,
    short_literals: bool,
    expected: str,
) -> None:
    assert render(hint, make_config(python_display_short_literal_types=short_literals)) == expected
