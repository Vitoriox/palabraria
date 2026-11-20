"""Translate through MyMemory's free API (no key needed)."""

from __future__ import annotations

import html
import json
import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGGER = logging.getLogger(__name__)

API_URL = "https://api.mymemory.translated.net/get"
LANG_PAIRS = {"en": "es|en", "de": "es|de"}


class DictionaryError(RuntimeError):
    """Translation request failed."""


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Palabra-del-dia/1.0 (https://github.com/Vitoriox/palabraria)",
            "Accept": "application/json",
        }
    )
    retry = Retry(
        total=1,
        connect=1,
        read=1,
        status=1,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _translate(session: requests.Session, text: str, lang: str) -> str | None:
    """Translate one string into ``lang`` and return plain text."""
    params = {"q": text, "langpair": LANG_PAIRS[lang]}
    try:
        response = session.get(API_URL, params=params, timeout=(5, 10))
    except requests.RequestException as exc:
        LOGGER.warning("MyMemory request failed for %s: %s", lang, exc)
        return None
    if not response.ok:
        LOGGER.warning("MyMemory returned HTTP %s for %s", response.status_code, lang)
        return None
    try:
        data = response.json()
    except (ValueError, json.JSONDecodeError) as exc:
        LOGGER.warning("MyMemory returned invalid JSON for %s: %s", lang, exc)
        return None

    translated = (data.get("responseData") or {}).get("translatedText")
    if not isinstance(translated, str):
        return None
    translated = html.unescape(translated).strip()
    if not translated or "MYMEMORY WARNING" in translated.upper():
        return None
    return translated


def translate_entry(word: str, definition: str) -> dict[str, dict]:
    """Translate the headword and its definition into English and German."""
    if not word.strip() or not definition.strip():
        raise DictionaryError("The entry has no word or definition to translate")

    session = _session()
    result: dict[str, dict] = {}

    for lang in ("en", "de"):
        LOGGER.info("Translating to %s", lang)
        term = _translate(session, word, lang)
        time.sleep(0.4)
        translated_definition = _translate(session, definition, lang)
        time.sleep(0.4)

        if term and term.casefold() == word.casefold():
            term = None

        result[lang] = {
            "term": term,
            "definition": translated_definition,
            "provider": "mymemory",
            "verified": False,
        }
        LOGGER.info("%s: %r / %r", lang, term, translated_definition)

    return result
