# ruff:ignore[implicit-namespace-package]  # Sphinx loads this extension from a path conf.py puts on sys.path
"""The controls a `live-example-picker` puts in the `conf.py` tab of each example, described from the reference."""

from __future__ import annotations

from html import escape
from itertools import groupby
from re import MULTILINE, split
from re import compile as compile_regex
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from live_example_variants import Option

_CONFVAL: Final = compile_regex(
    r"^\.\. confval:: (?P<name>\w+)\n(?:[ \t]+:\w+:.*\n)*\n(?P<content>(?:[ \t]+\S.*(?:\n|$))+)", MULTILINE
)
# a role shows its explicit title, or its target, cut to the last part by a leading tilde
_ROLE: Final = compile_regex(
    r":[\w:]+:`(?:(?P<title>[^`<]*?)\s*<[^`>]*>|~(?:[\w.]*\.)?(?P<short>[^`]+)|(?P<name>[^`]+))`"
)


def describe(reference: str) -> dict[str, str]:
    """Map each `.. confval::` entry of a reST page to the HTML of its first sentence, up to a semicolon."""
    return {
        match["name"]: _first_sentence(" ".join(match["content"].split())) for match in _CONFVAL.finditer(reference)
    }


def _first_sentence(text: str) -> str:
    plain = _ROLE.sub(lambda match: match["title"] or match["short"] or match["name"], text)
    sentence = split(r"(?<=\.)\s|;\s", plain, maxsplit=1)[0].removesuffix(".")
    # the literals of reST alternate with the text around them
    parts = sentence.split("``")
    return "".join(f"<code>{escape(part)}</code>" if at % 2 else escape(part) for at, part in enumerate(parts)) + "."


def selector(options: list[Option], conf: str, descriptions: dict[str, str], reference: str, example: int) -> str:
    """Lay out the controls of one example in the groups of the options, above the `conf.py` they make."""
    groups = "".join(
        f'<fieldset class="lep-group"><legend>{escape(group)}</legend>'
        f"{''.join(_option(option, descriptions.get(option.name, ''), reference, example) for option in members)}"
        "</fieldset>"
        for group, members in groupby(options, key=lambda option: option.group)
    )
    return (
        '<form class="live-example-picker">'
        f'<div class="lep-groups">{groups}</div>'
        '<div class="lep-actions"><span class="lep-status" role="status"></span>'
        '<button type="reset" class="lep-reset">Reset to the defaults</button></div>'
        f'<div class="highlight-python notranslate"><div class="highlight"><pre>{conf}</pre></div></div></form>'
    )


def _option(option: Option, description: str, reference: str, example: int) -> str:
    name, ident = escape(option.name), f"lep-{example}-{escape(option.name)}"
    tip = (
        '<span class="lep-tipwrap">'
        f'<button type="button" class="lep-info" aria-describedby="{ident}-tip" aria-label="About {name}">i</button>'
        f'<span class="lep-tip" role="tooltip" id="{ident}-tip">{description}</span></span>'
    )
    link = f'<a class="lep-name" href="{reference}#confval-{name}"><code>{name}</code></a>'
    if set(option.values) == {True, False}:
        checked = " checked" if option.values[0] else ""
        return (
            '<div class="lep-option">'
            f'<input type="checkbox" role="switch" class="lep-switch" id="{ident}" name="{name}"{checked}>'
            f'<div class="lep-text"><div class="lep-head"><label class="lep-label" for="{ident}">'
            f"{escape(option.label)}</label>{tip}</div>{link}</div></div>"
        )
    segments = "".join(
        f'<label class="lep-segment"><input type="radio" name="{name}" value="{at}"{"" if at else " checked"}>'
        f"<span>{escape(str(value))}</span></label>"
        for at, value in enumerate(option.values)
    )
    return (
        '<div class="lep-option lep-option-wide">'
        f'<div class="lep-text"><div class="lep-head"><span class="lep-label" id="{ident}-label">'
        f"{escape(option.label)}</span>{tip}</div>{link}</div>"
        f'<div class="lep-segmented" role="radiogroup" aria-labelledby="{ident}-label">{segments}</div></div>'
    )


__all__ = [
    "describe",
    "selector",
]
