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
        self.assertEqual(word, "palabraprueba")
        self.assertIn("20 de noviembre de 2026", display_date)
        self.assertTrue(url.startswith("https://dle.rae.es/palabraprueba"))

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
        word, senses = parse_entry(fixture("entry-single.html"))
        self.assertEqual(word, "palabraprueba")
        self.assertEqual(
            senses, ["Definición ficticia para probar el analizador."]
        )

    def test_multiple_senses_exclude_locutions(self) -> None:
        word, senses = parse_entry(fixture("entry-multiple.html"))
        self.assertEqual(word, "palabramultiple")
        self.assertGreaterEqual(len(senses), 5)
        self.assertEqual(senses[0], "Primera definición ficticia.")
        self.assertNotIn("Locución ficticia que no debe incluirse.", senses)
        for sense in senses:
            self.assertTrue(sense)

    def test_to_dict_keeps_only_primary_sense(self) -> None:
        entry = WordEntry(
            word="palabraprueba",
            display_date="viernes, 20 de noviembre de 2026",
            iso_date=date(2026, 11, 20),
            senses=[
                "Primera definición ficticia.",
                "Segunda definición ficticia.",
            ],
        )
        self.assertEqual(
            entry.to_dict(),
            {
                "date": "2026-11-20",
                "display_date": "viernes, 20 de noviembre de 2026",
                "word": "palabraprueba",
                "definition": "Primera definición ficticia.",
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
                "en": {"term": "testword", "definition": "A test definition."},
                "de": {"term": None, "definition": "Eine Testdefinition."},
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
                "en": {"term": "testword"},
                "de": {"term": "Testwort"},
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
        if text == "palabraprueba":
            return FakeResponse("palabraprueba" if lang == "en" else "Testwort")
        if text == "Definición ficticia para probar el analizador.":
            return FakeResponse(
                "Fictional definition for testing the parser."
                if lang == "en"
                else "Fiktive Definition zum Testen des Parsers."
            )
        raise AssertionError(f"Unexpected request: {text!r}")


class DictionaryTests(unittest.TestCase):
    def test_translate_entry_marks_unchanged_term_missing(self) -> None:
        session = FakeSession()
        with mock.patch.object(dictionary, "_session", return_value=session), mock.patch.object(
            dictionary.time, "sleep"
        ):
            result = dictionary.translate_entry(
                "palabraprueba", "Definición ficticia para probar el analizador."
            )

        self.assertIsNone(result["en"]["term"])
        self.assertEqual(
            result["en"]["definition"],
            "Fictional definition for testing the parser.",
        )
        self.assertEqual(result["de"]["term"], "Testwort")
        self.assertEqual(
            result["de"]["definition"],
            "Fiktive Definition zum Testen des Parsers.",
        )

        pairs = [call["langpair"] for call in session.calls]
        self.assertEqual(pairs, ["es|en", "es|en", "es|de", "es|de"])

    def test_empty_word_raises(self) -> None:
        with self.assertRaises(dictionary.DictionaryError):
            dictionary.translate_entry(
                " ", "Definición ficticia para probar el analizador."
            )


if __name__ == "__main__":
    unittest.main()
