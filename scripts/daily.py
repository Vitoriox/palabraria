#!/usr/bin/env python3
"""Fetch today's RAE word, translate it, and store the result as JSON."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from lib.dictionary import DictionaryError, translate_entry
from lib.overrides import apply_overrides, load_overrides
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-translation",
        action="store_true",
        help="Fetch the RAE entry without translating",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        entry = fetch_word_of_day()
    except (RaeError, OSError) as exc:
        LOGGER.error("Could not fetch the RAE word: %s", exc)
        return 1

    data = entry.to_dict()

    if args.skip_translation:
        data["translations"] = {}
        data["translation_status"] = "skipped"
        LOGGER.warning("Translations skipped by flag")
    else:
        try:
            data["translations"] = translate_entry(data["word"], data["definition"])
            data["translation_status"] = "ok"
        except DictionaryError as exc:
            data["translations"] = {}
            data["translation_status"] = "failed"
            data["translation_error"] = str(exc)[:300]
            LOGGER.warning("Translation failed: %s", exc)
            print(f"::warning title=Translation failed::{exc}")

    overrides = load_overrides(ROOT / "overrides" / "terms.json")
    apply_overrides(data, overrides)

    data["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    archive = ROOT / "data" / "archive" / f"{data['date']}.json"
    write_json(archive, data)
    write_json(ROOT / "data" / "latest.json", data)

    LOGGER.info(
        "Stored %r (%s), translations: %s",
        data["word"],
        data["date"],
        data["translation_status"],
    )
    print(f"::notice title=Word of the day::{data['word']} ({data['date']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
