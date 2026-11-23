#!/usr/bin/env python3
"""Fetch today's RAE word, translate it, and store the result as JSON."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from lib.dictionary import DictionaryError, translate_entry
from lib.rae import RaeError, fetch_word_of_day

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger("daily")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def check_translations(data: dict, status: str) -> str:
    """Warn about missing terms after a successful translation run."""
    if status != "ok":
        return status
    missing = [
        lang
        for lang in ("en", "de")
        if not (data.get("translations", {}).get(lang, {}).get("term"))
    ]
    if missing:
        message = f"Missing translation term for: {', '.join(missing)}"
        LOGGER.warning(message)
        print(f"::warning title=Partial translation::{message}")
        return "partial"
    return "ok"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        entry = fetch_word_of_day()
    except (RaeError, OSError) as exc:
        LOGGER.error("Could not fetch the RAE word: %s", exc)
        return 1

    data = entry.to_dict()

    try:
        data["translations"] = translate_entry(data["word"], data["definition"])
        status = "ok"
    except DictionaryError as exc:
        data["translations"] = {}
        status = "failed"
        LOGGER.warning("Translation failed: %s", exc)
        print(f"::warning title=Translation failed::{exc}")

    status = check_translations(data, status)
    write_json(ROOT / "data" / "latest.json", data)

    LOGGER.info(
        "Stored %r (%s), translations: %s",
        data["word"],
        data["date"],
        status,
    )
    print(f"::notice title=Word of the day::{data['word']} ({data['date']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
