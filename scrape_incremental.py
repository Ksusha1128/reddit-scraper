#!/usr/bin/env python3
"""
Incremental scraper — appends new reviews to existing CSV.
Never overwrites. Survives interruption. Shows progress.

Usage:
    python scrape_incremental.py
"""
import asyncio
import csv
import hashlib
import os
import sys
import time
from pathlib import Path

# Project imports
sys.path.insert(0, str(Path(__file__).parent))
from src.apps import TRACKED_APPS, GENERIC_QUERIES
from src.models import AppNiche, ReviewSource
from src.scraper.http_client import RedditClient
from src.scraper.rss_parser import parse_rss_feed
from src.analytics.sentiment import analyze_sentiment
from src.analytics.categorizer import categorize_text
from src.scraper.review_scraper import (
    NICHE_SUBREDDITS, _text_mentions_app, _detect_apps_in_text, _NICHE_KEYWORDS,
)

CSV_PATH = Path("reviews/all_reviews.csv")
FIELDS = [
    "app_name", "source", "author", "title", "text", "subreddit",
    "permalink", "date", "sentiment_score", "sentiment_label",
    "categories", "primary_category",
]


def content_hash(text: str) -> str:
    return hashlib.sha256(text[:500].encode()).hexdigest()[:16]


def load_existing_hashes() -> set[str]:
    """Load hashes of existing reviews to avoid duplicates."""
    hashes = set()
    if not CSV_PATH.exists():
        return hashes
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = f"{row.get('title', '')} {row.get('text', '')}"
            hashes.add(content_hash(text))
    print(f"📂 Loaded {len(hashes)} existing hashes from CSV")
    return hashes


def append_review(row: dict):
    """Append a single review row to CSV."""
    exists = CSV_PATH.exists() and CSV_PATH.stat().st_size > 0
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def make_row(app_name: str, source: str, entry, text: str) -> dict:
    score, label = analyze_sentiment(text)
    cats = categorize_text(text)
    return {
        "app_name": app_name,
        "source": source,
        "author": getattr(entry, "author", "[deleted]"),
        "title": getattr(entry, "title", ""),
        "text": text[:5000],
        "subreddit": getattr(entry, "subreddit", ""),
        "permalink": getattr(entry, "link", ""),
        "date": getattr(entry, "updated", ""),
        "sentiment_score": round(score, 4),
        "sentiment_label": label.value if hasattr(label, "value") else str(label),
        "categories": "; ".join(c.value if hasattr(c, "value") else str(c) for c in cats),
        "primary_category": cats[0].value if cats and hasattr(cats[0], "value") else (str(cats[0]) if cats else "uncategorized"),
    }


async def scrape_app_rss(client: RedditClient, app, seen: set[str]) -> int:
    """Scrape RSS for one app. Returns count of new reviews added."""
    added = 0
    for query in app.search_queries:
        try:
            rss = await client.get_rss(
                "https://www.reddit.com/search.rss",
                params={"q": query, "sort": "relevance", "t": "all", "limit": 50},
            )
            if not rss:
                continue
            entries = parse_rss_feed(rss)
            for entry in entries:
                full_text = f"{entry.title} {entry.body}"
                h = content_hash(full_text)
                if h in seen:
                    continue
                seen.add(h)
                if not _text_mentions_app(full_text, app):
                    continue
                row = make_row(app.name, "post", entry, full_text)
                append_review(row)
                added += 1
        except Exception as e:
            print(f"    ⚠️ {query}: {e}")
    return added


async def scrape_subreddit_rss(client: RedditClient, sub: str, apps: list, niche: AppNiche, seen: set[str]) -> int:
    """Scrape one subreddit RSS. Returns count of new reviews."""
    added = 0
    for sort in ("new", "hot"):
        try:
            rss = await client.get_rss(
                f"https://www.reddit.com/r/{sub}/{sort}.rss",
                params={"limit": 50},
            )
            if not rss:
                continue
            entries = parse_rss_feed(rss)
            for entry in entries:
                full_text = f"{entry.title} {entry.body}"
                h = content_hash(full_text)
                if h in seen:
                    continue
                detected = _detect_apps_in_text(full_text, apps)
                nkw = _NICHE_KEYWORDS.get(niche, [])
                if not detected and not any(kw in full_text.lower() for kw in nkw):
                    continue
                seen.add(h)
                name = detected[0] if detected else f"[{niche.value}]"
                row = make_row(name, "post", entry, full_text)
                append_review(row)
                added += 1
        except Exception as e:
            print(f"    ⚠️ r/{sub}/{sort}: {e}")
    return added


async def scrape_generic_rss(client: RedditClient, query: str, apps: list, niche: AppNiche, seen: set[str]) -> int:
    """Scrape generic niche query. Returns count of new reviews."""
    added = 0
    try:
        rss = await client.get_rss(
            "https://www.reddit.com/search.rss",
            params={"q": query, "sort": "relevance", "t": "all", "limit": 50},
        )
        if not rss:
            return 0
        entries = parse_rss_feed(rss)
        for entry in entries:
            full_text = f"{entry.title} {entry.body}"
            h = content_hash(full_text)
            if h in seen:
                continue
            detected = _detect_apps_in_text(full_text, apps)
            nkw = _NICHE_KEYWORDS.get(niche, [])
            if not detected and not any(kw in full_text.lower() for kw in nkw):
                continue
            seen.add(h)
            name = detected[0] if detected else f"[{niche.value}]"
            row = make_row(name, "post", entry, full_text)
            append_review(row)
            added += 1
    except Exception as e:
        print(f"    ⚠️ generic '{query}': {e}")
    return added


async def main():
    start = time.time()
    seen = load_existing_hashes()
    client = RedditClient()
    total_added = 0

    # ═══ PHASE 1: Per-app search ═══
    print(f"\n{'═'*60}")
    print(f"📡 PHASE 1: Scraping {len(TRACKED_APPS)} apps by name")
    print(f"{'═'*60}")

    for i, app in enumerate(TRACKED_APPS, 1):
        n = await scrape_app_rss(client, app, seen)
        total_added += n
        status = f"+{n}" if n > 0 else "—"
        print(f"  [{i:2d}/{len(TRACKED_APPS)}] {app.name:<30s} {status}")

    # ═══ PHASE 2: Generic queries ═══
    print(f"\n{'═'*60}")
    print(f"📡 PHASE 2: Generic niche queries")
    print(f"{'═'*60}")

    for niche, queries in GENERIC_QUERIES.items():
        apps = [a for a in TRACKED_APPS if a.niche == niche]
        niche_added = 0
        for query in queries:
            n = await scrape_generic_rss(client, query, apps, niche, seen)
            niche_added += n
            total_added += n
        print(f"  {niche.value}: +{niche_added}")

    # ═══ PHASE 3: Subreddit RSS ═══
    print(f"\n{'═'*60}")
    print(f"📡 PHASE 3: Scraping {sum(len(v) for v in NICHE_SUBREDDITS.values())} subreddits")
    print(f"{'═'*60}")

    for niche, subs in NICHE_SUBREDDITS.items():
        apps = [a for a in TRACKED_APPS if a.niche == niche]
        niche_added = 0
        for sub in subs:
            n = await scrape_subreddit_rss(client, sub, apps, niche, seen)
            niche_added += n
            total_added += n
            if n > 0:
                print(f"    r/{sub}: +{n}")
        print(f"  {niche.value}: +{niche_added}")

    await client.close()

    elapsed = time.time() - start
    print(f"\n{'═'*60}")
    print(f"✅ DONE in {elapsed:.0f}s")
    print(f"   New reviews added: {total_added}")
    print(f"   Total in CSV:     {sum(1 for _ in open(CSV_PATH)) - 1}")
    print(f"{'═'*60}")


if __name__ == "__main__":
    asyncio.run(main())
