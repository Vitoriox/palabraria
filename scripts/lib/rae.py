"""Fetch and parse the RAE word of the day from the DLE website."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter, Retry

BASE_URL = "https://dle.rae.es/"
MADRID = ZoneInfo("Europe/Madrid")

REQUEST_HEADERS = {
    "User-Agent": (
        "Palabra-del-dia/1.0 "
        "(+https://github.com/Vitoriox/palabraria/issues)"
    ),
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

LOGGER = logging.getLogger(__name__)


class RaeError(RuntimeError):
    """Base error for RAE fetching and parsing."""


@dataclass
class WordEntry:
    word: str
    display_date: str
    iso_date: date
    senses: list[str]

    @property
    def primary(self) -> str:
        return self.senses[0]

    def to_dict(self) -> dict:
        return {
            "date": self.iso_date.isoformat(),
            "display_date": self.display_date,
            "word": self.word,
            "definition": self.primary,
        }


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _get(session: requests.Session, url: str) -> str:
    response = session.get(url, timeout=(10, 30))
    response.raise_for_status()
    text = response.text
    if "Just a moment" in text and "c-word-day" not in text:
        raise RaeError(
            "Cloudflare returned a challenge page instead of the DLE. "
            "Retry later or run the fetch from a different network."
        )
    return text


def clean_text(node) -> str:
    text = node.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?»)\]])", r"\1", text)
    text = re.sub(r"([«(\[])\s+", r"\1", text)
    return text.strip()


def parse_spanish_date(text: str) -> date | None:
    match = re.search(
        r"(\d{1,2})\s+de\s+([a-záéíóúüñ]+)\s+de\s+(\d{4})",
        text.casefold(),
    )
    if not match:
        return None
    month = MONTHS.get(match.group(2))
    if not month:
        return None
    try:
        return date(int(match.group(3)), month, int(match.group(1)))
    except ValueError:
        return None


def parse_homepage(html: str) -> tuple[str, str, str]:
    soup = BeautifulSoup(html, "html.parser")
    box = soup.select_one(".c-word-day")
    if box is None:
        raise RaeError("No .c-word-day block found on the DLE homepage")

    word_node = box.select_one(".c-word-day__word")
    date_node = box.select_one(".c-word-day__subtitle")
    link_node = box.select_one("a.c-word-day__link")
    if word_node is None or date_node is None or link_node is None:
        raise RaeError("The word-of-day block is missing expected elements")

    word = clean_text(word_node)
    display_date = clean_text(date_node)
    href = link_node.get("href", "").strip()
    if not word or not display_date or not href:
        raise RaeError("The word-of-day block has empty values")

    return word, display_date, urljoin(BASE_URL, href)


def parse_entry(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("article.o-main__article")
    if article is None:
        raise RaeError("No main article found on the DLE entry page")

    title = article.select_one("h1.c-page-header__title")
    if title is None:
        raise RaeError("No entry title found on the DLE entry page")
    word = clean_text(title)

    section = None
    for candidate in article.find_all("section", class_="c-section"):
        heading = candidate.find("h2", recursive=False)
        if heading and clean_text(heading) == "Definición":
            section = candidate
            break
    if section is None:
        section = article.find("section", class_="c-section")
    if section is None:
        raise RaeError("No definition section found on the DLE entry page")

    definition_list = section.find("ol", class_="c-definitions")
    if definition_list is None:
        items = section.select("div.c-definitions__item[role='definition']")
    else:
        items = definition_list.select(
            "div.c-definitions__item[role='definition']"
        )

    senses: list[str] = []
    for item in items:
        if item.find_parent("div", class_="fc-definition"):
            continue
        definition_node = item.select_one(".dle24-definition")
        if definition_node is None:
            continue
        definition = clean_text(definition_node)
        if definition:
            senses.append(definition)

    if not senses:
        raise RaeError("No definitions could be parsed from the DLE entry")

    return word, senses


def fetch_word_of_day() -> WordEntry:
    session = make_session()

    homepage = _get(session, BASE_URL)
    word, display_date, url = parse_homepage(homepage)

    entry_html = _get(session, url)
    entry_word, senses = parse_entry(entry_html)

    if entry_word.casefold() != word.casefold():
        LOGGER.warning(
            "Homepage word %r differs from entry title %r", word, entry_word
        )
        word = entry_word

    iso_date = parse_spanish_date(display_date)
    today = datetime.now(MADRID).date()
    if iso_date is None:
        LOGGER.warning("Could not parse the Spanish date %r", display_date)
        iso_date = today
    elif iso_date != today:
        LOGGER.warning(
            "DLE word of the day is dated %s, Madrid is %s",
            iso_date,
            today,
        )

    return WordEntry(
        word=word,
        display_date=display_date,
        iso_date=iso_date,
        senses=senses,
    )
