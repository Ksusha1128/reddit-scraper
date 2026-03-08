#!/usr/bin/env python3
"""
Fast batch scraper — scrapes ALL apps and writes results incrementally.
Even if killed mid-way, data collected so far is saved.

Usage:
    python scrape_fresh.py
"""
from __future__ import annotations

import asyncio
import csv
import hashlib
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.apps import TRACKED_APPS, GENERIC_QUERIES
from src.models import AppNiche, ReviewSource
from src.analytics.sentiment import analyze_sentiment
from src.analytics.categorizer import categorize_text

# ── Config ──
OUT_CSV = Path("reviews/all_reviews.csv")
COOLDOWN = (0.3, 0.8)  # fast but polite
TIMEOUT = 12
MAX_RETRIES = 2
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Reddit-Research-Bot/2.0"

# ── Niche subreddits ──
NICHE_SUBS: dict[AppNiche, list[str]] = {
    AppNiche.RELATIONSHIPS: [
        "relationships", "relationship_advice", "Marriage", "LongDistance",
        "dating_advice", "mentalhealth", "Anxiety", "depression", "therapy",
        "Meditation", "couple_apps",
    ],
    AppNiche.SMOKING: [
        "stopsmoking", "quittingsmoking", "leaves",
    ],
    AppNiche.PLANT_SCANNER: [
        "whatsthisplant", "PlantIdentification", "houseplants",
        "gardening", "plantclinic",
    ],
    AppNiche.CALORIE_TRACKER: [
        "loseit", "CICO", "Myfitnesspal", "1200isplenty",
        "intermittentfasting", "nutrition", "cronometer",
    ],
}

NICHE_KEYWORDS: dict[AppNiche, list[str]] = {
    AppNiche.RELATIONSHIPS: [
        "couple app", "relationship app", "therapy app", "mental health app",
        "meditation app", "ai therapist", "couple game", "long distance app",
    ],
    AppNiche.SMOKING: [
        "quit smoking", "stop smoking", "nicotine app", "cessation app",
    ],
    AppNiche.PLANT_SCANNER: [
        "plant identifier", "plant scanner", "plant id", "identify plant",
    ],
    AppNiche.CALORIE_TRACKER: [
        "calorie tracker", "calorie counter", "food tracker", "macro tracker",
        "diet app", "nutrition app",
    ],
}

# ── Alias matching ──
_cache: dict[str, re.Pattern] = {}


def _pat(alias: str) -> re.Pattern:
    if alias not in _cache:
        _cache[alias] = re.compile(rf"\b{re.escape(alias)}\b", re.I)
    return _cache[alias]


def mentions_app(text: str, app) -> bool:
    return any(_pat(a).search(text) for a in app.aliases)


def detect_apps(text: str, apps) -> list[str]:
    return [a.name for a in apps if mentions_app(text, a)]


def content_hash(text: str) -> str:
    return hashlib.sha256(text[:500].encode()).hexdigest()[:16]


# ── CSV writer ──
CSV_FIELDS = [
    "app_name", "source", "author", "title", "text", "subreddit",
    "permalink", "date", "sentiment_score", "sentiment_label",
    "categories", "primary_category",
]


class IncrementalWriter:
    def __init__(self, path: Path):
        self.path = path
        self.seen: set[str] = set()
        self.count = 0
        # Start fresh
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=CSV_FIELDS)
        self._writer.writeheader()
        self._file.flush()

    def add(self, row: dict) -> bool:
        h = content_hash(row.get("text", "") + row.get("title", ""))
        if h in self.seen:
            return False
        self.seen.add(h)
        self._writer.writerow(row)
        self.count += 1
        if self.count % 20 == 0:
            self._file.flush()
        return True

    def flush(self):
        self._file.flush()

    def close(self):
        self._file.close()


# ── HTTP ──
async def fetch_rss(client: httpx.AsyncClient, url: str, params: dict | None = None) -> str | None:
    for attempt in range(MAX_RETRIES):
        try:
            r = await client.get(url, params=params)
            if r.status_code == 200:
                await asyncio.sleep(random.uniform(*COOLDOWN))
                return r.text
            if r.status_code == 429:
                wait = 2 ** (attempt + 1) + random.uniform(0, 2)
                print(f"    ⏳ Rate limited, waiting {wait:.0f}s...")
                await asyncio.sleep(wait)
                continue
        except (httpx.TimeoutException, httpx.ConnectError):
            await asyncio.sleep(1)
    return None


async def fetch_json(client: httpx.AsyncClient, url: str, params: dict | None = None) -> dict | None:
    for attempt in range(MAX_RETRIES):
        try:
            r = await client.get(url, params=params)
            if r.status_code == 200:
                await asyncio.sleep(random.uniform(*COOLDOWN))
                return r.json()
            if r.status_code == 429:
                wait = 2 ** (attempt + 1) + random.uniform(0, 2)
                print(f"    ⏳ Rate limited (JSON), waiting {wait:.0f}s...")
                await asyncio.sleep(wait)
                continue
        except (httpx.TimeoutException, httpx.ConnectError):
            await asyncio.sleep(1)
    return None


# ── RSS Parser (simple) ──
def parse_rss_entries(xml_text: str) -> list[dict]:
    """Quick RSS parser — extract title, link, body, author, date, subreddit."""
    import xml.etree.ElementTree as ET
    entries = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return entries

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns):
        title = (entry.findtext("atom:title", "", ns) or "").strip()
        link_el = entry.find("atom:link", ns)
        link = link_el.get("href", "") if link_el is not None else ""
        content = (entry.findtext("atom:content", "", ns) or "").strip()
        author_el = entry.find("atom:author/atom:name", ns)
        author = author_el.text.strip() if author_el is not None and author_el.text else "[deleted]"
        updated = (entry.findtext("atom:updated", "", ns) or "").strip()

        # Clean HTML from content
        body = re.sub(r"<[^>]+>", " ", content)
        body = re.sub(r"\s+", " ", body).strip()

        # Extract subreddit from link
        sub_match = re.search(r"/r/(\w+)/", link)
        subreddit = sub_match.group(1) if sub_match else ""

        # Extract category (some feeds have it)
        cat_el = entry.find("atom:category", ns)
        if cat_el is not None and not subreddit:
            subreddit = cat_el.get("term", "")

        entries.append({
            "title": title[:500],
            "link": link,
            "body": body[:5000],
            "author": author,
            "updated": updated,
            "subreddit": subreddit,
        })
    return entries


def make_review_row(app_name: str, source: str, entry: dict, text: str) -> dict:
    score, label = analyze_sentiment(text)
    cats = categorize_text(text)
    primary = cats[0].value if cats else "uncategorized"
    cat_str = ", ".join(c.value for c in cats) if cats else "uncategorized"
    return {
        "app_name": app_name,
        "source": source,
        "author": entry.get("author", "[deleted]"),
        "title": entry.get("title", ""),
        "text": text[:5000],
        "subreddit": entry.get("subreddit", ""),
        "permalink": entry.get("link", ""),
        "date": entry.get("updated", ""),
        "sentiment_score": round(score, 4),
        "sentiment_label": label.value,
        "categories": cat_str,
        "primary_category": primary,
    }


# ── Main scraping logic ──
async def main():
    start = time.monotonic()
    writer = IncrementalWriter(OUT_CSV)
    errors = 0

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(TIMEOUT),
        follow_redirects=True,
    ) as client:

        total_apps = len(TRACKED_APPS)

        # ── STRATEGY 1: Per-app RSS search ──
        print(f"\n{'='*60}")
        print(f"📡 STRATEGY 1: App-specific RSS search ({total_apps} apps)")
        print(f"{'='*60}")

        for i, app in enumerate(TRACKED_APPS, 1):
            for q in app.search_queries:
                xml = await fetch_rss(client, "https://www.reddit.com/search.rss",
                                      {"q": q, "sort": "relevance", "t": "all", "limit": 100})
                if not xml:
                    errors += 1
                    continue
                entries = parse_rss_entries(xml)
                added = 0
                for e in entries:
                    full = f"{e['title']} {e['body']}"
                    if not mentions_app(full, app):
                        continue
                    row = make_review_row(app.name, "post", e, full)
                    if writer.add(row):
                        added += 1
                if added:
                    print(f"  [{i}/{total_apps}] {app.name}: +{added} from '{q[:40]}'")

            # Progress
            if i % 10 == 0:
                writer.flush()
                print(f"  ── Progress: {i}/{total_apps} apps, {writer.count} reviews total ──")

        writer.flush()
        print(f"\n✅ Strategy 1 done: {writer.count} reviews")

        # ── STRATEGY 2: Generic niche queries ──
        print(f"\n{'='*60}")
        print(f"📡 STRATEGY 2: Generic niche queries")
        print(f"{'='*60}")

        for niche, queries in GENERIC_QUERIES.items():
            niche_apps = [a for a in TRACKED_APPS if a.niche == niche]
            for q in queries:
                xml = await fetch_rss(client, "https://www.reddit.com/search.rss",
                                      {"q": q, "sort": "relevance", "t": "all", "limit": 100})
                if not xml:
                    errors += 1
                    continue
                entries = parse_rss_entries(xml)
                added = 0
                for e in entries:
                    full = f"{e['title']} {e['body']}"
                    detected = detect_apps(full, niche_apps)
                    if not detected:
                        kws = NICHE_KEYWORDS.get(niche, [])
                        if any(kw in full.lower() for kw in kws):
                            detected = [f"[{niche.value}]"]
                        else:
                            continue
                    for app_name in detected:
                        row = make_review_row(app_name, "post", e, full)
                        if writer.add(row):
                            added += 1
                if added:
                    print(f"  {niche.value}: +{added} from '{q[:50]}'")

        writer.flush()
        print(f"\n✅ Strategy 2 done: {writer.count} reviews total")

        # ── STRATEGY 3: Subreddit RSS (new/hot/top) ──
        print(f"\n{'='*60}")
        print(f"📡 STRATEGY 3: Subreddit RSS scraping")
        print(f"{'='*60}")

        for niche, subs in NICHE_SUBS.items():
            niche_apps = [a for a in TRACKED_APPS if a.niche == niche]
            for sub in subs:
                sub_added = 0
                for sort in ("new", "hot", "top"):
                    xml = await fetch_rss(client,
                                          f"https://www.reddit.com/r/{sub}/{sort}.rss",
                                          {"limit": 100})
                    if not xml:
                        continue
                    entries = parse_rss_entries(xml)
                    for e in entries:
                        full = f"{e['title']} {e['body']}"
                        detected = detect_apps(full, niche_apps)
                        if not detected:
                            kws = NICHE_KEYWORDS.get(niche, [])
                            if any(kw in full.lower() for kw in kws):
                                detected = [f"[{niche.value}]"]
                            else:
                                continue
                        for app_name in detected:
                            row = make_review_row(app_name, "post", e, full)
                            if writer.add(row):
                                sub_added += 1
                if sub_added:
                    print(f"  r/{sub}: +{sub_added}")

        writer.flush()
        print(f"\n✅ Strategy 3 done: {writer.count} reviews total")

        # ── STRATEGY 4: Subreddit JSON API ──
        print(f"\n{'='*60}")
        print(f"📡 STRATEGY 4: Subreddit JSON API (deeper)")
        print(f"{'='*60}")

        for niche, subs in NICHE_SUBS.items():
            niche_apps = [a for a in TRACKED_APPS if a.niche == niche]
            for sub in subs[:5]:  # top 5 per niche
                sub_added = 0
                after = None
                for page in range(5):  # up to 5 pages of 100
                    params = {"limit": 100, "raw_json": 1}
                    if after:
                        params["after"] = after
                    data = await fetch_json(client,
                                            f"https://www.reddit.com/r/{sub}/new.json",
                                            params)
                    if not data:
                        break
                    children = data.get("data", {}).get("children", [])
                    if not children:
                        break
                    after = data.get("data", {}).get("after")

                    for child in children:
                        post = child.get("data", {})
                        title = post.get("title", "")
                        selftext = post.get("selftext", "")
                        full = f"{title} {selftext}"
                        if not full.strip() or full.strip() in ("[deleted]", "[removed]"):
                            continue
                        permalink = f"https://reddit.com{post.get('permalink', '')}"
                        author = post.get("author", "[deleted]")
                        created = post.get("created_utc", 0)
                        dt = datetime.fromtimestamp(created, tz=timezone.utc).isoformat() if created else ""

                        detected = detect_apps(full, niche_apps)
                        if not detected:
                            kws = NICHE_KEYWORDS.get(niche, [])
                            if any(kw in full.lower() for kw in kws):
                                detected = [f"[{niche.value}]"]
                            else:
                                continue

                        entry = {
                            "title": title[:500],
                            "link": permalink,
                            "body": selftext[:5000],
                            "author": author,
                            "updated": dt,
                            "subreddit": post.get("subreddit", sub),
                        }
                        for app_name in detected:
                            row = make_review_row(app_name, "post", entry, full)
                            if writer.add(row):
                                sub_added += 1

                    if not after:
                        break

                if sub_added:
                    print(f"  r/{sub} (JSON): +{sub_added}")

        writer.flush()
        print(f"\n✅ Strategy 4 done: {writer.count} reviews total")

    # ── Summary ──
    elapsed = time.monotonic() - start
    writer.close()

    print(f"\n{'='*60}")
    print(f"🏁 SCRAPE COMPLETE")
    print(f"{'='*60}")
    print(f"  📝 Total reviews: {writer.count}")
    print(f"  ⏱️  Duration: {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  ⚠️  Errors: {errors}")
    print(f"  💾 Saved to: {OUT_CSV}")

    # Quick stats
    import pandas as pd
    df = pd.read_csv(OUT_CSV)
    print(f"\n  📊 Unique apps: {df['app_name'].nunique()}")
    print(f"  📊 Apps with data: {df.groupby('app_name').size().reset_index(name='n')}")
    apps_with_data = df["app_name"].unique().tolist()
    all_app_names = [a.name for a in TRACKED_APPS]
    missing = [a for a in all_app_names if a not in apps_with_data]
    print(f"  📊 Apps with 0 reviews: {len(missing)}")
    if missing:
        print(f"      {missing[:20]}")


if __name__ == "__main__":
    asyncio.run(main())
