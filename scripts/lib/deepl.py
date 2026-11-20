"""Translate the RAE entry with the DeepL API."""

from __future__ import annotations

import logging
import os
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOGGER = logging.getLogger(__name__)

FREE_ENDPOINT = "https://api-free.deepl.com/v2/translate"
LANGUAGES = {"en": "EN-US", "de": "DE"}


class DeepLError(RuntimeError):
    """DeepL request failed."""


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"POST"}),
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _translate_text(
    session: requests.Session,
    key: str,
    text: str,
    target_lang: str,
    *,
    context: str | None = None,
    endpoint: str = FREE_ENDPOINT,
) -> str:
    data = {
        "text": text,
        "source_lang": "ES",
        "target_lang": target_lang,
    }
    if context:
        data["context"] = context[:5000]

    response = session.post(
        endpoint,
        headers={"Authorization": f"DeepL-Auth-Key {key}"},
        data=data,
        timeout=(10, 45),
    )

    if response.status_code == 456:
        raise DeepLError("DeepL quota exceeded")
    if response.status_code == 403:
        raise DeepLError("DeepL rejected the API key")
    if not response.ok:
        detail = response.text.replace("\n", " ")[:200]
        raise DeepLError(
            f"DeepL returned HTTP {response.status_code}: {detail}"
        )

    try:
        translated = response.json()["translations"][0]["text"].strip()
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise DeepLError("Unexpected DeepL response shape") from exc

    if not translated:
        raise DeepLError("DeepL returned an empty translation")
    return translated


def translate_entry(
    word: str,
    definition: str,
    key: str,
    *,
    endpoint: str | None = None,
) -> dict[str, dict]:
    """Return translations for the primary sense, keyed by language."""
    key = key.strip()
    if not key:
        raise DeepLError("DEEPL_API_KEY is empty")
    if not word.strip() or not definition.strip():
        raise DeepLError("The entry has no word or definition to translate")

    endpoint = endpoint or os.getenv("DEEPL_API_URL", FREE_ENDPOINT)
    session = _session()
    result: dict[str, dict] = {}

    for lang, target in LANGUAGES.items():
        LOGGER.info("Translating the headword to %s", lang)
        term = _translate_text(
            session,
            key,
            word,
            target,
            context=definition,
            endpoint=endpoint,
        )
        if term.casefold() == word.casefold():
            LOGGER.warning("DeepL did not translate %r to %s", word, lang)
            term = None

        time.sleep(0.15)
        LOGGER.info("Translating the definition to %s", lang)
        translated_definition = _translate_text(
            session,
            key,
            definition,
            target,
            endpoint=endpoint,
        )

        result[lang] = {
            "term": term,
            "definition": translated_definition,
            "provider": "deepl",
            "verified": False,
        }
        time.sleep(0.15)

    return result
