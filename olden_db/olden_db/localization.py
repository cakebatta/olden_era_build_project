from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class LocalizationError(ValueError):
    """Raised when a localization file has an unexpected structure."""


class DuplicateLocalizationKeyError(LocalizationError):
    """Raised when one localization key is assigned conflicting text."""


@dataclass(frozen=True, slots=True)
class LocalizationCatalog:
    """Lookup table mapping localization SIDs to visible text."""

    language: str
    tokens: dict[str, str]

    def __post_init__(self) -> None:
        if not self.language:
            raise ValueError("language cannot be empty")

    def get(self, sid: str) -> str:
        """Return localized text or raise a clear error for an unknown SID."""
        try:
            return self.tokens[sid]
        except KeyError as exc:
            raise KeyError(
                f"Unknown localization SID {sid!r} for language "
                f"{self.language!r}"
            ) from exc

    def resolve(self, sid: str | None, *, fallback: str | None = None) -> str | None:
        """
        Resolve one SID without forcing callers to catch KeyError.

        If `sid` is None, return `fallback`. If the SID is missing, return the
        supplied fallback or the SID itself.
        """
        if sid is None:
            return fallback

        return self.tokens.get(
            sid,
            fallback if fallback is not None else sid,
        )

    def contains(self, sid: str) -> bool:
        return sid in self.tokens


def parse_localization_file(
    path: str | Path,
    *,
    language: str,
) -> LocalizationCatalog:
    """Parse one localization JSON file containing a `tokens` array."""
    source = Path(path)

    try:
        with source.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as exc:
        raise LocalizationError(
            f"Invalid JSON in {source}: line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc

    return _parse_localization_document(
        data,
        language=language,
        source=str(source),
    )


def parse_localization_directory(
    directory: str | Path,
    *,
    language: str,
    pattern: str = "*.json",
) -> LocalizationCatalog:
    """
    Merge every matching localization JSON file in a text directory.

    Duplicate keys are allowed only when they map to identical text.
    """
    root = Path(directory)
    paths = sorted(path for path in root.glob(pattern) if path.is_file())

    if not paths:
        raise FileNotFoundError(
            f"No localization files matching {pattern!r} were found in {root}"
        )

    merged: dict[str, str] = {}

    for path in paths:
        catalog = parse_localization_file(path, language=language)
        _merge_tokens(
            merged,
            catalog.tokens,
            source=str(path),
        )

    return LocalizationCatalog(language=language, tokens=merged)


def parse_localization_files(
    paths: Iterable[str | Path],
    *,
    language: str,
) -> LocalizationCatalog:
    """Merge an explicit collection of localization files."""
    merged: dict[str, str] = {}
    found_any = False

    for raw_path in paths:
        found_any = True
        path = Path(raw_path)
        catalog = parse_localization_file(path, language=language)
        _merge_tokens(
            merged,
            catalog.tokens,
            source=str(path),
        )

    if not found_any:
        raise ValueError("paths cannot be empty")

    return LocalizationCatalog(language=language, tokens=merged)


def _parse_localization_document(
    data: object,
    *,
    language: str,
    source: str,
) -> LocalizationCatalog:
    if not isinstance(data, dict):
        raise LocalizationError(
            f"{source}: top-level JSON value must be an object"
        )

    raw_tokens = data.get("tokens")
    if not isinstance(raw_tokens, list):
        raise LocalizationError(
            f"{source}: top-level 'tokens' field must be a list"
        )

    parsed: dict[str, str] = {}

    for index, raw_token in enumerate(raw_tokens, start=1):
        if not isinstance(raw_token, dict):
            raise LocalizationError(
                f"{source}: token {index} must be an object"
            )

        sid = _required_string(
            raw_token,
            "sid",
            context=f"{source}: token {index}",
        )
        text = _required_string(
            raw_token,
            "text",
            context=f"{source}: token {index}",
            allow_empty=True,
        )

        if sid in parsed and parsed[sid] != text:
            raise DuplicateLocalizationKeyError(
                f"{source}: localization SID {sid!r} has conflicting values"
            )

        parsed[sid] = text

    return LocalizationCatalog(language=language, tokens=parsed)


def _merge_tokens(
    destination: dict[str, str],
    incoming: dict[str, str],
    *,
    source: str,
) -> None:
    for sid, text in incoming.items():
        if sid in destination and destination[sid] != text:
            raise DuplicateLocalizationKeyError(
                f"{source}: localization SID {sid!r} conflicts with an "
                "earlier file"
            )

        destination[sid] = text


def _required_string(
    mapping: dict[str, Any],
    key: str,
    *,
    context: str,
    allow_empty: bool = False,
) -> str:
    value = mapping.get(key)

    if not isinstance(value, str):
        raise LocalizationError(
            f"{context}: field {key!r} must be a string"
        )

    if not allow_empty and not value:
        raise LocalizationError(
            f"{context}: field {key!r} cannot be empty"
        )

    return value
