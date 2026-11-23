#!/usr/bin/env python3
"""Assemble the static site in dist/ with the latest word data."""

from __future__ import annotations

import json
import logging
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger("build")

REQUIRED_FIELDS = ("date", "word", "definition")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    latest = ROOT / "data" / "latest.json"
    if not latest.exists():
        LOGGER.error("data/latest.json does not exist; run scripts/daily.py first")
        return 1

    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        LOGGER.error("data/latest.json is not valid JSON: %s", exc)
        return 1

    missing = [field for field in REQUIRED_FIELDS if not data.get(field)]
    if missing:
        LOGGER.error("data/latest.json is missing fields: %s", ", ".join(missing))
        return 1

    dist = ROOT / "dist"
    shutil.rmtree(dist, ignore_errors=True)
    shutil.copytree(ROOT / "site", dist)
    (dist / ".nojekyll").write_text("", encoding="utf-8")

    output = dist / "data" / "latest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    LOGGER.info("Built %s with data for %s", dist, data["date"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
