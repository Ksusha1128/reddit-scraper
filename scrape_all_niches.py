#!/usr/bin/env python3
"""
Fast multi-niche scraper — goes directly to reddit.com RSS.
No mirror rotation, no backoff. Just grabs data for all 5 niches quickly.
Run: python scrape_all_niches.py
"""

import asyncio
import csv
import hashlib
import html
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

# ─── Config ──────────────────────────────────────────────────────────────

OUTPUT = Path("reviews/all_reviews.csv")
USER_AGENT = "CoupleAppReviewScraper/2.0 (research)"
COOLDOWN = 2.5  # seconds between requests
LIMIT = 50

# ─── App definitions per niche ───────────────────────────────────────────

NICHES: dict[str, dict[str, list[str]]] = {
    # niche_label → { app_name → [aliases] }
    "Пары и отношения": {
        "Couple Joy": ["couplejoy", "couple joy"],
        "Paired": ["paired app", "paired couple", "getpaired"],
        "Between": ["between app"],
        "Lovewick": ["lovewick", "love wick"],
        "Love Nudge": ["love nudge", "lovenudge"],
        "Couply": ["couply"],
        "Lasting": ["lasting app"],
        "Honeydue": ["honeydue", "honey due"],
        "Happy Couple": ["happy couple app", "happycouple"],
    },
    "Бросить курить": {
        "Smoke Free": ["smoke free", "smokefree"],
        "QuitNow!": ["quitnow", "quit now"],
        "Kwit": ["kwit"],
        "EasyQuit": ["easyquit", "easy quit"],
        "QuitGenius": ["quit genius", "quitgenius"],
        "Flamy": ["flamy"],
    },
    "AI-психолог": {
        "Breeze": ["breeze app", "breeze therapy"],
        "Headspace": ["headspace"],
        "Woebot": ["woebot"],
        "Wysa": ["wysa"],
        "Youper": ["youper"],
        "Calm": ["calm app"],
        "BetterHelp": ["betterhelp", "better help"],
        "Talkspace": ["talkspace", "talk space"],
    },
    "Сканер растений": {
        "PictureThis": ["picturethis", "picture this"],
        "PlantNet": ["plantnet", "pl@ntnet", "plant net"],
        "Planta": ["planta app", "planta plant"],
        "LeafSnap": ["leafsnap", "leaf snap"],
        "Blossom": ["blossom plant", "blossom app"],
        "Greg": ["greg plant", "greg app"],
    },
    "Трекер калорий": {
        "MyFitnessPal": ["myfitnesspal", "my fitness pal"],
        "Lose It!": ["lose it", "loseit"],
        "CalAI": ["calai", "cal ai"],
        "Cronometer": ["cronometer"],
        "Yazio": ["yazio"],
        "MacroFactor": ["macrofactor", "macro factor"],
        "FatSecret": ["fatsecret", "fat secret"],
    },
}

# Queries per app (fast — just 1-2 queries each)
APP_QUERIES: dict[str, list[str]] = {
    # Couple
    "Couple Joy": ['"couple joy" app'],
    "Paired": ['"paired" couple app'],
    "Between": ['"between app" couple'],
    "Lovewick": ["lovewick app"],
    "Love Nudge": ['"love nudge" app'],
    "Couply": ["couply app"],
    "Lasting": ['"lasting" marriage app'],
    "Honeydue": ["honeydue app"],
    "Happy Couple": ['"happy couple" app'],
    # Smoking
    "Smoke Free": ['"smoke free" app quit smoking'],
    "QuitNow!": ["quitnow app smoking"],
    "Kwit": ["kwit quit smoking app"],
    "EasyQuit": ["easyquit smoking app"],
    "QuitGenius": ["quit genius app smoking"],
    "Flamy": ["flamy quit smoking"],
    # AI Psych
    "Breeze": ['"breeze" therapy app'],
    "Headspace": ["headspace app review"],
    "Woebot": ["woebot app therapy"],
    "Wysa": ["wysa app ai therapist"],
    "Youper": ["youper app ai"],
    "Calm": ["calm app meditation review"],
    "BetterHelp": ["betterhelp app review"],
    "Talkspace": ["talkspace app review"],
    # Plant
    "PictureThis": ["picturethis plant app"],
    "PlantNet": ["plantnet plant identifier"],
    "Planta": ["planta plant care app"],
    "LeafSnap": ["leafsnap plant app"],
    "Blossom": ["blossom plant care app"],
    "Greg": ['"greg" plant care app'],
    # Calorie
    "MyFitnessPal": ["myfitnesspal app review"],
    "Lose It!": ["lose it calorie app"],
    "CalAI": ["calai calorie app"],
    "Cronometer": ["cronometer nutrition app"],
    "Yazio": ["yazio calorie app"],
    "MacroFactor": ["macrofactor app"],
    "FatSecret": ["fatsecret calorie app"],
}

# Generic queries per niche
GENERIC_QUERIES: dict[str, list[str]] = {
    "Пары и отношения": [
        "best couple app recommendation",
        "relationship app for couples review",
    ],
    "Бросить курить": [
        "best quit smoking app",
        "stop smoking app recommendation",
    ],
    "AI-психолог": [
        "best ai therapy app review",
        "mental health chatbot app recommendation",
    ],
    "Сканер растений": [
        "best plant identifier app",
        "plant identification app review",
    ],
    "Трекер калорий": [
        "best calorie tracker app review",
        "calorie counting app recommendation",
    ],
}

# ─── Sentiment (simple keyword-based — fast) ──────────────────────────────

_POS = {"love", "great", "amazing", "awesome", "excellent", "best", "recommend",
        "helpful", "nice", "good", "perfect", "fantastic", "wonderful", "enjoy",
        "easy", "useful", "works", "beautiful", "fun", "happy", "worth"}
_NEG = {"bad", "terrible", "hate", "awful", "horrible", "worst", "useless",
        "waste", "broken", "scam", "annoying", "disappointed", "frustrating",
        "expensive", "bug", "crash", "poor", "ugly", "sucks", "spam"}


def simple_sentiment(text: str) -> tuple[float, str]:
    words = set(text.lower().split())
    pos = len(words & _POS)
    neg = len(words & _NEG)
    total = pos + neg
    if total == 0:
        return 0.0, "neutral"
    score = (pos - neg) / total
    if score > 0.2:
        return round(score, 3), "positive"
    if score < -0.2:
        return round(score, 3), "negative"
    return round(score, 3), "neutral"


# ─── Categories (simple keyword) ─────────────────────────────────────────

CATS = {
    "💰 Цена / Подписка": ["price", "subscription", "paid", "free", "cost", "money", "premium", "trial"],
    "⭐ UX / Интерфейс": ["ui", "interface", "design", "ux", "layout", "look", "beautiful", "ugly"],
    "🐛 Баги / Проблемы": ["bug", "crash", "error", "broken", "glitch", "issue", "fix", "problem"],
    "📊 Функции": ["feature", "features", "functionality", "function", "tracking", "log", "sync"],
    "❤️ Общее мнение": ["love", "hate", "recommend", "best", "worst", "great", "terrible"],
}


def categorize(text: str) -> str:
    tl = text.lower()
    found = []
    for cat, keywords in CATS.items():
        if any(kw in tl for kw in keywords):
            found.append(cat)
    return " | ".join(found) if found else "📋 Без категории"


# ─── RSS helpers ──────────────────────────────────────────────────────────

NS = {"atom": "http://www.w3.org/2005/Atom"}


def clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_rss(content: str) -> list[dict]:
    entries = []
    try:
        root = ET.fromstring(content.encode())
    except ET.ParseError:
        return entries

    for el in root.findall("atom:entry", NS):
        title_el = el.find("atom:title", NS)
        link_el = el.find("atom:link", NS)
        content_el = el.find("atom:content", NS)
        author_el = el.find("atom:author/atom:name", NS)
        updated_el = el.find("atom:updated", NS)
        cat_el = el.find("atom:category", NS)

        title = (title_el.text or "").strip() if title_el is not None else ""
        link = link_el.get("href", "") if link_el is not None else ""
        body = clean_html((content_el.text or "").strip() if content_el is not None else "")
        author = (author_el.text or "").strip() if author_el is not None else "[deleted]"
        updated = (updated_el.text or "").strip() if updated_el is not None else ""
        subreddit = cat_el.get("term", "") if cat_el is not None else ""

        if author.startswith("/u/"):
            author = author[3:]
        if not body or body in ("[deleted]", "[removed]"):
            continue
        if re.match(r"^https://www\.reddit\.com/r/[^/]+/?$", link):
            continue

        entries.append({
            "title": title,
            "link": link,
            "body": body,
            "author": author,
            "updated": updated,
            "subreddit": subreddit,
        })
    return entries


def content_hash(text: str) -> str:
    return hashlib.sha256(text[:500].encode()).hexdigest()[:16]


# ─── Main scraper ─────────────────────────────────────────────────────────

async def fetch_rss(client: httpx.AsyncClient, query: str) -> str | None:
    try:
        r = await client.get(
            "https://www.reddit.com/search.rss",
            params={"q": query, "sort": "relevance", "t": "all", "limit": LIMIT},
        )
        if r.status_code == 200:
            return r.text
        print(f"  ⚠ HTTP {r.status_code} for query: {query}")
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        print(f"  ⚠ Connection error for query: {query} — {e}")
    return None


def text_mentions(text: str, aliases: list[str]) -> bool:
    tl = text.lower()
    return any(a in tl for a in aliases)


def detect_apps(text: str, niche_apps: dict[str, list[str]]) -> list[str]:
    return [name for name, aliases in niche_apps.items() if text_mentions(text, aliases)]


async def main():
    seen: set[str] = set()
    all_rows: list[dict] = []

    # Load existing hashes to avoid duplicating what we already have
    if OUTPUT.exists():
        import pandas as pd
        existing = pd.read_csv(OUTPUT, encoding="utf-8-sig")
        for _, row in existing.iterrows():
            h = content_hash(str(row.get("text", ""))[:500])
            seen.add(h)
        print(f"📌 Loaded {len(seen)} existing hashes from {OUTPUT}")

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(15),
        follow_redirects=True,
    ) as client:

        for niche_label, apps in NICHES.items():
            print(f"\n{'='*60}")
            print(f"🔍 Ниша: {niche_label} ({len(apps)} приложений)")
            print(f"{'='*60}")

            niche_count = 0

            # Strategy 1: App-specific queries
            for app_name, aliases in apps.items():
                queries = APP_QUERIES.get(app_name, [])
                for query in queries:
                    print(f"  📥 {app_name}: {query}")
                    rss = await fetch_rss(client, query)
                    if not rss:
                        continue
                    entries = parse_rss(rss)
                    added = 0
                    for entry in entries:
                        full_text = f"{entry['title']} {entry['body']}"
                        h = content_hash(full_text)
                        if h in seen:
                            continue
                        seen.add(h)
                        # Accept if mentions this app OR if the query was specific enough
                        if not text_mentions(full_text, aliases):
                            continue
                        score, label = simple_sentiment(full_text)
                        cats = categorize(full_text)
                        all_rows.append({
                            "app_name": app_name,
                            "source": "post",
                            "author": entry["author"],
                            "title": entry["title"],
                            "text": full_text[:5000],
                            "subreddit": entry["subreddit"],
                            "permalink": entry["link"],
                            "date": entry["updated"],
                            "sentiment_score": score,
                            "sentiment_label": label,
                            "categories": cats,
                            "primary_category": cats.split(" | ")[0],
                        })
                        added += 1
                    if added:
                        niche_count += added
                        print(f"    ✅ +{added} отзывов")
                    await asyncio.sleep(COOLDOWN)

            # Strategy 2: Generic niche queries
            generic = GENERIC_QUERIES.get(niche_label, [])
            for query in generic:
                print(f"  📥 [generic] {query}")
                rss = await fetch_rss(client, query)
                if not rss:
                    await asyncio.sleep(COOLDOWN)
                    continue
                entries = parse_rss(rss)
                added = 0
                for entry in entries:
                    full_text = f"{entry['title']} {entry['body']}"
                    h = content_hash(full_text)
                    if h in seen:
                        continue

                    detected = detect_apps(full_text, apps)
                    if not detected:
                        detected = ["General"]

                    seen.add(h)
                    score, label = simple_sentiment(full_text)
                    cats = categorize(full_text)
                    for det_app in detected:
                        all_rows.append({
                            "app_name": det_app,
                            "source": "post",
                            "author": entry["author"],
                            "title": entry["title"],
                            "text": full_text[:5000],
                            "subreddit": entry["subreddit"],
                            "permalink": entry["link"],
                            "date": entry["updated"],
                            "sentiment_score": score,
                            "sentiment_label": label,
                            "categories": cats,
                            "primary_category": cats.split(" | ")[0],
                        })
                        added += 1
                if added:
                    niche_count += added
                    print(f"    ✅ +{added} отзывов")
                await asyncio.sleep(COOLDOWN)

            print(f"  📊 Итого по нише «{niche_label}»: {niche_count} новых отзывов")

    # Save
    if all_rows:
        print(f"\n💾 Сохранение {len(all_rows)} новых отзывов...")

        # Append to existing CSV
        file_exists = OUTPUT.exists() and OUTPUT.stat().st_size > 0
        with open(OUTPUT, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "app_name", "source", "author", "title", "text", "subreddit",
                "permalink", "date", "sentiment_score", "sentiment_label",
                "categories", "primary_category",
            ])
            if not file_exists:
                writer.writeheader()
            writer.writerows(all_rows)

        print(f"✅ Готово! Добавлено {len(all_rows)} строк в {OUTPUT}")
    else:
        print("\n⚠ Новых отзывов не найдено")

    # Summary
    if OUTPUT.exists():
        import pandas as pd
        df = pd.read_csv(OUTPUT, encoding="utf-8-sig")
        print(f"\n📊 Итого в CSV: {len(df)} строк")
        print(f"   Приложения: {df['app_name'].nunique()}")
        print(f"   Распределение:")
        for app, count in df["app_name"].value_counts().items():
            print(f"     {app}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
