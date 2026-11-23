from __future__ import annotations

import html
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import daily  # noqa: E402
from lib import dictionary  # noqa: E402
from lib.rae import (  # noqa: E402
    RaeError,
    WordEntry,
    clean_text,
    parse_entry,
    parse_homepage,
    parse_spanish_date,
)

FIXTURES = ROOT / "tests" / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class HomepageTests(unittest.TestCase):
    def test_parses_word_date_and_url(self) -> None:
        word, display_date, url = parse_homepage(fixture("homepage.html"))
        self.assertEqual(word, "noctambular")
        self.assertIn("20 de noviembre de 2026", display_date)
        self.assertTrue(url.startswith("https://dle.rae.es/noctambular"))

    def test_missing_block_raises(self) -> None:
        with self.assertRaises(RaeError):
            parse_homepage("<html><body>nothing</body></html>")


class DateTests(unittest.TestCase):
    def test_spanish_date(self) -> None:
        self.assertEqual(
            parse_spanish_date("viernes, 20 de noviembre de 2026"),
            date(2026, 11, 20),
        )
        self.assertEqual(
            parse_spanish_date("1 de enero de 2027"),
            date(2027, 1, 1),
        )

    def test_invalid_date(self) -> None:
        self.assertIsNone(parse_spanish_date("sin fecha"))
        self.assertIsNone(parse_spanish_date("31 de febrero de 2026"))


class EntryTests(unittest.TestCase):
    def test_single_sense(self) -> None:
        word, senses = parse_entry(fixture("noctambular.html"))
        self.assertEqual(word, "noctambular")
        self.assertEqual(senses, ["Andar vagando de noche."])

    def test_multiple_senses_exclude_locutions(self) -> None:
        word, senses = parse_entry(fixture("banco.html"))
        self.assertEqual(word, "banco")
        self.assertGreaterEqual(len(senses), 5)
        self.assertTrue(senses[0].startswith("Asiento, con respaldo"))
        self.assertNotIn("jugar banco", senses[0])
        for sense in senses:
            self.assertTrue(sense)
            self.assertNotIn("Permanecer en un banco", sense)

    def test_to_dict_keeps_only_primary_sense(self) -> None:
        entry = WordEntry(
            word="banco",
            display_date="viernes, 20 de noviembre de 2026",
            iso_date=date(2026, 11, 20),
            senses=[
                "Asiento, con respaldo o sin él, en que pueden sentarse dos o más personas.",
                "Madero grueso escuadrado que se coloca horizontalmente.",
            ],
        )
        self.assertEqual(
            entry.to_dict(),
            {
                "date": "2026-11-20",
                "display_date": "viernes, 20 de noviembre de 2026",
                "word": "banco",
                "definition": (
                    "Asiento, con respaldo o sin él, en que pueden sentarse dos o más personas."
                ),
            },
        )

    def test_clean_text_removes_space_before_punctuation(self) -> None:
        from bs4 import BeautifulSoup

        node = BeautifulSoup("<span>Andar , vagando .</span>", "html.parser").span
        self.assertEqual(clean_text(node), "Andar, vagando.")


class TranslationStatusTests(unittest.TestCase):
    def test_flags_missing_term(self) -> None:
        data = {
            "translations": {
                "en": {"term": "nightwalk", "definition": "To walk at night."},
                "de": {"term": None, "definition": "Nachts umher."},
            }
        }
        with mock.patch("builtins.print"), self.assertLogs("daily", level="WARNING"):
            status = daily.check_translations(data, "ok")
        self.assertEqual(status, "partial")

    def test_keeps_failed_status(self) -> None:
        self.assertEqual(daily.check_translations({"translations": {}}, "failed"), "failed")

    def test_leaves_complete_translations_alone(self) -> None:
        data = {
            "translations": {
                "en": {"term": "nightwalk"},
                "de": {"term": "Nachtwanderung"},
            }
        }
        self.assertEqual(daily.check_translations(data, "ok"), "ok")


class FakeResponse:
    def __init__(self, translated: str) -> None:
        self.ok = True
        self._translated = html.escape(translated)

    def json(self) -> dict:
        return {"responseData": {"translatedText": self._translated}}


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def get(self, _url, params=None, timeout=None):
        self.calls.append(dict(params or {}))
        text = (params or {}).get("q", "")
        lang = (params or {}).get("langpair", "").split("|")[-1]
        if text == "noctambular":
            return FakeResponse("noctambular" if lang == "en" else "Nachtschwärmer")
        if text == "Andar vagando de noche.":
            return FakeResponse(
                "To walk about at night."
                if lang == "en"
                else "Nachts umherstreifen."
            )
        raise AssertionError(f"Unexpected request: {text!r}")


class DictionaryTests(unittest.TestCase):
    def test_translate_entry_marks_unchanged_term_missing(self) -> None:
        session = FakeSession()
        with mock.patch.object(dictionary, "_session", return_value=session), mock.patch.object(
            dictionary.time, "sleep"
        ):
            result = dictionary.translate_entry(
                "noctambular", "Andar vagando de noche."
            )

        self.assertIsNone(result["en"]["term"])
        self.assertEqual(result["en"]["definition"], "To walk about at night.")
        self.assertEqual(result["de"]["term"], "Nachtschwärmer")
        self.assertEqual(result["de"]["definition"], "Nachts umherstreifen.")

        pairs = [call["langpair"] for call in session.calls]
        self.assertEqual(pairs, ["es|en", "es|en", "es|de", "es|de"])

    def test_empty_word_raises(self) -> None:
        with self.assertRaises(dictionary.DictionaryError):
            dictionary.translate_entry(" ", "Andar vagando de noche.")


if __name__ == "__main__":
    unittest.main()
