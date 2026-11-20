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

from lib.deepl import DeepLError, translate_entry
from lib.overrides import apply_overrides, load_overrides
from lib.rae import RaeError, fetch_word_of_day

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger("daily")


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip("'\"")
        if name and name not in os.environ:
            os.environ[name] = value


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
        help="Fetch the RAE entry without calling DeepL",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )
    load_dotenv(ROOT / ".env")

    try:
        entry = fetch_word_of_day()
    except (RaeError, OSError) as exc:
        LOGGER.error("Could not fetch the RAE word: %s", exc)
        return 1

    data = entry.to_dict()
    key = os.getenv("DEEPL_API_KEY", "").strip()

    if args.skip_translation or not key:
        data["translations"] = {}
        data["translation_status"] = "skipped"
        reason = (
            "translation skipped by flag"
            if args.skip_translation
            else "DEEPL_API_KEY is not set"
        )
        LOGGER.warning("Translations not generated: %s", reason)
    else:
        try:
            data["translations"] = translate_entry(
                data["word"],
                data["definition"],
                key,
            )
            data["translation_status"] = "ok"
        except DeepLError as exc:
            data["translations"] = {}
            data["translation_status"] = "failed"
            data["translation_error"] = str(exc)[:300]
            LOGGER.warning("DeepL translation failed: %s", exc)
            print(f"::warning title=DeepL translation failed::{exc}")

    overrides = load_overrides(ROOT / "overrides" / "terms.json")
    apply_overrides(data, overrides)

    data["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    archive = ROOT / "data" / "archive" / f"{data['date']}.json"
    latest = ROOT / "data" / "latest.json"
    write_json(archive, data)
    write_json(latest, data)

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
