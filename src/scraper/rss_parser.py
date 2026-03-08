"""
RSS feed parser.

Parses Reddit's Atom RSS feeds into validated RSSEntry models.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET

from src.logging import get_logger
from src.models import RSSEntry

logger = get_logger(__name__)

# Atom namespace
_NS = {"atom": "http://www.w3.org/2005/Atom"}


def clean_html(text: str) -> str:
    """Strip HTML tags, decode entities, normalise whitespace."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", text)
    return text


def parse_rss_feed(content: str | bytes) -> list[RSSEntry]:
    """
    Parse an Atom RSS feed into a list of RSSEntry models.

    Args:
        content: Raw XML content from Reddit RSS.

    Returns:
        List of validated RSSEntry objects (invalid entries are skipped).
    """
    entries: list[RSSEntry] = []

    try:
        root = ET.fromstring(content if isinstance(content, bytes) else content.encode())
    except ET.ParseError as exc:
        logger.warning("rss_parse_error", error=str(exc))
        return entries

    for entry_el in root.findall("atom:entry", _NS):
        try:
            title = _text(entry_el, "atom:title")
            link = _attr(entry_el, "atom:link", "href")
            body = clean_html(_text(entry_el, "atom:content"))
            author = _text(entry_el, "atom:author/atom:name")
            updated = _text(entry_el, "atom:updated")
            subreddit = _attr(entry_el, "atom:category", "term")

            # Clean author
            if author.startswith("/u/"):
                author = author[3:]

            # Skip empty / deleted content
            if not body or body in ("[deleted]", "[removed]"):
                continue

            # Skip subreddit-level links (not actual posts)
            if re.match(r"^https://www\.reddit\.com/r/[^/]+/?$", link):
                continue

            entries.append(
                RSSEntry(
                    title=title,
                    link=link,
                    body=body,
                    author=author or "[deleted]",
                    updated=updated,
                    subreddit=subreddit,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("rss_entry_skip", error=str(exc))
            continue

    return entries


def _text(parent: ET.Element, xpath: str) -> str:
    """Extract text from an XML element, returning empty string if missing."""
    el = parent.find(xpath, _NS)
    return (el.text or "").strip() if el is not None else ""


def _attr(parent: ET.Element, xpath: str, attr: str) -> str:
    """Extract attribute from an XML element."""
    el = parent.find(xpath, _NS)
    return el.get(attr, "") if el is not None else ""
