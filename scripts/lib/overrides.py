"""Apply optional manual translation overrides."""

from __future__ import annotations

import json
import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def load_overrides(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read overrides from {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("overrides/terms.json must contain a JSON object")
    return data


def apply_overrides(data: dict, overrides: dict) -> dict:
    """Apply word-level overrides to the primary-sense translations."""
    if not overrides:
        return data

    entry = overrides.get(data.get("word", ""))
    if entry is None:
        folded = data.get("word", "").casefold()
        entry = next(
            (
                value
                for key, value in overrides.items()
                if key.casefold() == folded
            ),
            None,
        )
    if not isinstance(entry, dict):
        return data

    translations = data.setdefault("translations", {})
    applied = False
    for lang in ("en", "de"):
        values = entry.get(lang)
        if not isinstance(values, dict):
            continue
        current = translations.setdefault(lang, {})
        for field in ("term", "definition"):
            value = values.get(field)
            if isinstance(value, str) and value.strip():
                current[field] = value.strip()
        if current:
            current["provider"] = "manual"
            current["verified"] = True
            applied = True
            LOGGER.info("Applied manual %s override for %r", lang, data["word"])

    complete = all(
        translations.get(lang, {}).get("term")
        or translations.get(lang, {}).get("definition")
        for lang in ("en", "de")
    )
    if applied and complete and data.get("translation_status") != "ok":
        data["translation_status"] = "manual"
    return data
