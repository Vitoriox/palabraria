from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib import deepl  # noqa: E402
from lib.overrides import apply_overrides, load_overrides  # noqa: E402
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
        word, senses = parse_entry(
            fixture("noctambular.html"),
            "https://dle.rae.es/noctambular",
        )
        self.assertEqual(word, "noctambular")
        self.assertEqual(len(senses), 1)
        self.assertEqual(senses[0].pos, ["intr."])
        self.assertEqual(senses[0].definition, "Andar vagando de noche.")

    def test_multiple_senses_exclude_locutions(self) -> None:
        word, senses = parse_entry(
            fixture("banco.html"),
            "https://dle.rae.es/banco",
        )
        self.assertEqual(word, "banco")
        self.assertGreaterEqual(len(senses), 5)
        self.assertEqual(senses[0].pos, ["m."])
        self.assertTrue(
            senses[0].definition.startswith("Asiento, con respaldo")
        )
        self.assertNotIn("jugar banco", senses[0].definition)
        for sense in senses:
            self.assertTrue(sense.definition)
            self.assertNotIn("Permanecer en un banco", sense.definition)

    def test_to_dict_limits_other_senses(self) -> None:
        _, senses = parse_entry(fixture("banco.html"), "https://dle.rae.es/banco")
        entry = WordEntry(
            word="banco",
            display_date="viernes, 20 de noviembre de 2026",
            iso_date=date(2026, 11, 20),
            url="https://dle.rae.es/banco",
            senses=senses,
        )
        data = entry.to_dict()
        self.assertLessEqual(len(data["other_senses"]), 4)
        self.assertEqual(data["date"], "2026-11-20")
        self.assertEqual(data["pos"], ["m."])

    def test_clean_text_removes_space_before_punctuation(self) -> None:
        from bs4 import BeautifulSoup

        node = BeautifulSoup("<span>Andar , vagando .</span>", "html.parser").span
        self.assertEqual(clean_text(node), "Andar, vagando.")


class OverrideTests(unittest.TestCase):
    def test_apply_override(self) -> None:
        data = {
            "word": "noctambular",
            "translation_status": "skipped",
            "translations": {
                "en": {
                    "term": "nightwalk",
                    "definition": "Wrong",
                    "provider": "deepl",
                    "verified": False,
                }
            },
        }
        overrides = {
            "noctambular": {
                "en": {"term": "to wander at night", "definition": "To walk at night."},
                "de": {"term": "nachts umherwandern"},
            }
        }
        apply_overrides(data, overrides)
        self.assertEqual(data["translations"]["en"]["term"], "to wander at night")
        self.assertTrue(data["translations"]["en"]["verified"])
        self.assertEqual(data["translations"]["en"]["provider"], "manual")
        self.assertEqual(
            data["translations"]["de"]["term"], "nachts umherwandern"
        )
        self.assertEqual(data["translation_status"], "manual")

    def test_load_overrides_missing_file(self) -> None:
        self.assertEqual(load_overrides(ROOT / "does-not-exist.json"), {})

    def test_load_overrides_invalid_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "terms.json"
            path.write_text(json.dumps([]), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_overrides(path)


class FakeResponse:
    def __init__(self, text: str) -> None:
        self._text = text
        self.status_code = 200
        self.ok = True
        self.text = ""

    def json(self) -> dict:
        return {"translations": [{"text": self._text}]}


class FakeSession:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def post(self, url, headers=None, data=None, timeout=None):
        self.calls.append(dict(data))
        text = data["text"]
        target = data["target_lang"]
        if text == "noctambular" and target == "EN-US":
            return FakeResponse("noctambular")
        if text == "noctambular":
            return FakeResponse("nachts umherwandern")
        if text == "Andar vagando de noche.":
            return FakeResponse(
                "To walk about at night."
                if target == "EN-US"
                else "Nachts umherwandern."
            )
        return FakeResponse("translated")


class DeepLTests(unittest.TestCase):
    def test_translate_entry_marks_unchanged_term_missing(self) -> None:
        session = FakeSession()
        with mock.patch.object(deepl, "_session", return_value=session):
            result = deepl.translate_entry(
                "noctambular",
                "Andar vagando de noche.",
                "test-key",
            )

        self.assertIsNone(result["en"]["term"])
        self.assertEqual(result["en"]["definition"], "To walk about at night.")
        self.assertEqual(result["de"]["term"], "nachts umherwandern")
        self.assertEqual(result["en"]["provider"], "deepl")
        self.assertFalse(result["en"]["verified"])

        term_calls = [call for call in session.calls if call["text"] == "noctambular"]
        self.assertTrue(term_calls)
        self.assertEqual(term_calls[0]["context"], "Andar vagando de noche.")

    def test_empty_key_raises(self) -> None:
        with self.assertRaises(deepl.DeepLError):
            deepl.translate_entry("noctambular", "Andar vagando de noche.", " ")


if __name__ == "__main__":
    unittest.main()
