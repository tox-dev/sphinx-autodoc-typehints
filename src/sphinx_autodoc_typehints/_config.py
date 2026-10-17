"""
The configuration options the extension registers and their validation before reading.

It also wraps `typehints_fixup_module_name` so the cached environment can pickle it.
"""

from __future__ import annotations

from dataclasses import dataclass
from inspect import getsource
from typing import TYPE_CHECKING, Final, Literal

from sphinx.errors import ConfigError

from ._render import keep_type_mapping

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.environment import BuildEnvironment


@dataclass(frozen=True, slots=True, kw_only=True)
class Option:
    name: str
    default: bool | Callable[[Config], bool] | tuple[type, ...] | None
    rebuild: Literal["env", ""]
    types: tuple[type, ...] = ()


OPTIONS: Final[tuple[Option, ...]] = (
    Option(name="always_document_param_types", default=False, rebuild="env"),
    # follows autodoc's own setting unless set
    Option(
        name="typehints_fully_qualified",
        default=lambda config: config.autodoc_typehints_format == "fully-qualified",
        rebuild="env",
        types=(bool,),
    ),
    Option(name="typehints_document_rtype", default=True, rebuild="env"),
    Option(name="typehints_document_rtype_none", default=True, rebuild="env"),
    Option(name="typehints_use_rtype", default=True, rebuild="env"),
    Option(name="typehints_defaults", default=None, rebuild="env"),
    Option(name="simplify_optional_unions", default=True, rebuild="env"),
    Option(name="always_use_bars_union", default=False, rebuild="env"),
    Option(name="typehints_modernize_annotations", default=False, rebuild="env"),
    Option(name="typehints_formatter", default=None, rebuild="env"),
    Option(name="typehints_formatter_pass_context", default=False, rebuild="env", types=(bool,)),
    Option(name="typehints_annotated_metadata", default=(), rebuild="env", types=(tuple,)),
    Option(name="typehints_annotated_description", default=None, rebuild="env"),
    Option(name="typehints_document_overloads", default=True, rebuild="env"),
    Option(name="typehints_use_signature", default=False, rebuild="env"),
    Option(name="typehints_use_signature_return", default=False, rebuild="env"),
    Option(name="typehints_fixup_module_name", default=None, rebuild="env"),
)


def validate_config(app: Sphinx, _env: BuildEnvironment, _docnames: list[str]) -> None:
    """Reject a `typehints_defaults` or `typehints_formatter` the extension cannot use before reading a document."""
    valid = {None, "comma", "braces", "braces-after", "optional"}
    if app.config.typehints_defaults not in valid | {False}:
        msg = f"typehints_defaults needs to be one of {valid!r}, not {app.config.typehints_defaults!r}"
        raise ConfigError(msg)

    if (formatter := app.config.typehints_formatter) is not None and not callable(formatter):
        msg = f"typehints_formatter needs to be callable or `None`, not {formatter}"
        raise ConfigError(msg)
    if (extractor := app.config.typehints_annotated_description) is not None and not callable(extractor):
        msg = f"typehints_annotated_description needs to be callable or `None`, not {extractor}"
        raise ConfigError(msg)


def cache_annotated_metadata(_app: Sphinx, config: Config) -> None:
    """Store stable names instead of unpickleable classes in the Sphinx config."""
    if not isinstance(metadata := config.typehints_annotated_metadata, tuple) or not all(
        isinstance(item, type) for item in metadata
    ):
        msg = "typehints_annotated_metadata needs a tuple of types"
        raise ConfigError(msg)
    config.typehints_annotated_metadata = tuple(f"{item.__module__}.{item.__qualname__}" for item in metadata)


def store_type_mapping(app: Sphinx, env: BuildEnvironment, _docnames: list[str]) -> None:
    keep_type_mapping(app.config, env)


def cache_fixup_module_name(_app: Sphinx, config: Config) -> None:
    """Wrap `typehints_fixup_module_name` so the environment Sphinx caches can tell whether it changed."""
    if (function := config.typehints_fixup_module_name) is not None:
        config.typehints_fixup_module_name = _FixupModuleName(function)


def cache_formatter(_app: Sphinx, config: Config) -> None:
    """Keep the formatter comparable across incremental builds."""
    if (function := config.typehints_formatter) is not None and callable(function):
        config.typehints_formatter = _CachedCallable(function)


def cache_annotated_description(_app: Sphinx, config: Config) -> None:
    """Keep the description callback comparable across incremental builds."""
    if (function := config.typehints_annotated_description) is not None and callable(function):
        config.typehints_annotated_description = _CachedCallable(function)


# Sphinx can't pickle a function into its cached environment, so the source tells whether it changed between builds
class _CachedCallable[**P, R]:
    __hash__ = None

    def __init__(self, function: Callable[P, R]) -> None:
        self._function = function
        try:
            self._source = getsource(function)
        except (OSError, TypeError):
            # with no source to compare, the repr carries the object's id, so every build counts as a change
            self._source = repr(function)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        return self._function(*args, **kwargs)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _CachedCallable) and self._source == other._source

    def __repr__(self) -> str:
        return self._source

    def __getstate__(self) -> dict[str, str]:
        return {"_source": self._source}


class _FixupModuleName(_CachedCallable):
    pass


__all__ = [
    "OPTIONS",
    "cache_annotated_description",
    "cache_annotated_metadata",
    "cache_fixup_module_name",
    "cache_formatter",
    "store_type_mapping",
    "validate_config",
]
