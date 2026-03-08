#!/usr/bin/env python3
"""
💑 Reddit Couple Apps Review Scraper
Парсер отзывов о приложениях для пар с Reddit.
Собирает отзывы о: Couple Joy, Between, Paired, Lovewick, Love Nudge, Couply и др.
Автоматически категоризирует отзывы.

Работает через RSS (не требует API ключей).

Использование:
    python couple_apps_scraper.py                      # Парсинг всех приложений
    python couple_apps_scraper.py --app "Couple Joy"   # Только одно приложение
    python couple_apps_scraper.py --limit 50           # Лимит постов на запрос
    python couple_apps_scraper.py --output reviews     # Папка для результатов
"""

import requests
import pandas as pd
import time
import os
import re
import json
import random
import argparse
import html
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from collections import defaultdict

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
    _analyzer = SentimentIntensityAnalyzer()
except ImportError:
    VADER_AVAILABLE = False
    _analyzer = None
    print("⚠️  vaderSentiment не установлен. pip install vaderSentiment")

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================

USER_AGENT = "CoupleAppReviewScraper/1.0"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})

COOLDOWN = (2, 4)  # задержка между запросами (сек)

# ============================================================
# ПРИЛОЖЕНИЯ ДЛЯ ПАР — поисковые запросы и ключевые слова
# ============================================================

COUPLE_APPS = {
    "Couple Joy": {
        "search_queries": [
            "couple joy app",
            "couplejoy",
            '"couple joy"',
        ],
        "aliases": ["couplejoy", "couple joy"],
    },
    "Between": {
        "search_queries": [
            '"between app" couple',
            '"between" relationship app',
        ],
        "aliases": ["between app"],
    },
    "Paired": {
        "search_queries": [
            '"paired app"',
            '"paired" couple app',
            "paired relationship app",
        ],
        "aliases": ["paired app", "paired couple"],
    },
    "Lovewick": {
        "search_queries": [
            "lovewick",
            "lovewick app",
        ],
        "aliases": ["lovewick", "love wick"],
    },
    "Love Nudge": {
        "search_queries": [
            '"love nudge"',
            '"love nudge" app',
        ],
        "aliases": ["love nudge", "lovenudge"],
    },
    "Couply": {
        "search_queries": [
            "couply app",
            "couply couple",
        ],
        "aliases": ["couply"],
    },
    "Lasting": {
        "search_queries": [
            '"lasting app"',
            '"lasting" marriage app',
        ],
        "aliases": ["lasting app"],
    },
    "Honeydue": {
        "search_queries": [
            "honeydue",
            "honeydue app",
        ],
        "aliases": ["honeydue", "honey due"],
    },
    "Happy Couple": {
        "search_queries": [
            '"happy couple" app',
            "happycouple app",
        ],
        "aliases": ["happy couple app", "happycouple"],
    },
}

# Общие запросы — для поиска постов, где обсуждаются приложения в целом
GENERIC_QUERIES = [
    "best couple app",
    "couple app recommendation",
    "best app for couples relationship",
    "couples app review",
    "app for couples long distance",
    "relationship app",
    "app to improve relationship couples",
    "date night app couples",
    "app for couples questions",
]

# ============================================================
# КАТЕГОРИИ ОТЗЫВОВ
# ============================================================

REVIEW_CATEGORIES = {
    "💬 Общение / Коммуникация": {
        "keywords": [
            "communicat", "talk", "message", "chat", "conversation",
            "discuss", "listen", "express", "voice", "call",
            "share feelings", "open up", "daily question",
            "check-in", "check in", "connect",
        ],
        "description": "Отзывы о функциях общения, вопросах дня, чатах"
    },
    "❤️ Близость / Интимность": {
        "keywords": [
            "intima", "sex", "physical", "touch", "affection",
            "love language", "romance", "romantic", "passion",
            "desire", "sensual", "cuddle", "kiss", "hug",
            "intimacy", "bedroom",
        ],
        "description": "Отзывы о функциях для улучшения близости"
    },
    "🎯 Активности / Игры / Квизы": {
        "keywords": [
            "quiz", "game", "challenge", "question", "activity",
            "date idea", "date night", "fun", "play", "trivia",
            "bucket list", "adventure", "dare", "card",
            "icebreaker", "would you rather",
        ],
        "description": "Отзывы об играх, викторинах, идеях для свиданий"
    },
    "📅 Планирование / Календарь": {
        "keywords": [
            "calendar", "plan", "schedule", "remind", "anniversary",
            "birthday", "event", "countdown", "milestone",
            "memory", "memories", "timeline", "special day",
        ],
        "description": "Отзывы о планировании, напоминаниях, календаре"
    },
    "💰 Цена / Подписка": {
        "keywords": [
            "price", "paid", "premium", "subscription", "free",
            "cost", "expensive", "cheap", "money", "worth",
            "paywall", "trial", "purchase", "in-app",
            "pro version", "upgrade", "billing", "refund",
        ],
        "description": "Отзывы о стоимости, подписках, покупках"
    },
    "🐛 Баги / Технические проблемы": {
        "keywords": [
            "bug", "crash", "glitch", "error", "fix", "broken",
            "not work", "doesn't work", "won't load", "slow",
            "laggy", "freeze", "stuck", "issue", "problem",
            "update", "sync", "notification",
        ],
        "description": "Отзывы о технических проблемах"
    },
    "⭐ Общее впечатление": {
        "keywords": [
            "love this", "hate this", "recommend", "best app",
            "worst app", "amazing", "terrible", "awesome",
            "great app", "bad app", "helpful", "useless",
            "perfect", "disappointed", "satisfied", "enjoy",
            "favorite", "favourite", "uninstall", "delete",
            "download", "install", "review", "overall",
        ],
        "description": "Общие впечатления и рекомендации"
    },
    "👫 Влияние на отношения": {
        "keywords": [
            "relationship", "partner", "boyfriend", "girlfriend",
            "husband", "wife", "spouse", "couple", "together",
            "closer", "bond", "trust", "understand",
            "improve", "better", "helped", "saved", "strengthen",
            "grow", "growth", "heal", "therapy",
        ],
        "description": "Как приложение повлияло на отношения"
    },
    "🔒 Приватность / Безопасность": {
        "keywords": [
            "privacy", "private", "secure", "security", "data",
            "personal", "hack", "leak", "safe", "account",
            "password", "login", "permission",
        ],
        "description": "Отзывы о приватности и безопасности"
    },
    "📱 UI/UX / Дизайн": {
        "keywords": [
            "design", "interface", "ui", "ux", "beautiful",
            "ugly", "clean", "intuitive", "confusing", "easy to use",
            "user friendly", "layout", "theme", "dark mode",
            "navigation", "simple", "complicated",
        ],
        "description": "Отзывы о дизайне и удобстве использования"
    },
}


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def clean_html(text):
    """Очищает HTML-теги и entities."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[\u200b-\u200f\u2060\ufeff]', '', text)
    return text


def detect_app(text, app_config):
    """Определяет, упоминается ли приложение в тексте."""
    text_lower = text.lower()
    for alias in app_config["aliases"]:
        if alias in text_lower:
            return True
    return False


def detect_any_app(text, apps_dict):
    """Возвращает список приложений, упомянутых в тексте."""
    found = []
    for app_name, app_config in apps_dict.items():
        if detect_app(text, app_config):
            found.append(app_name)
    return found


def categorize_review(text):
    """Категоризирует отзыв. Возвращает до 3 категорий."""
    text_lower = text.lower()
    scores = {}

    for cat_name, cat_config in REVIEW_CATEGORIES.items():
        score = sum(1 for kw in cat_config["keywords"] if kw in text_lower)
        if score > 0:
            scores[cat_name] = score

    if scores:
        sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [c for c, _ in sorted_cats[:3]]
    return ["📝 Без категории"]


def analyze_sentiment(text):
    """Анализ тональности текста."""
    if not VADER_AVAILABLE or not _analyzer:
        return 0.0, "neutral"
    s = _analyzer.polarity_scores(text)
    c = s["compound"]
    if c >= 0.05:
        return c, "positive"
    elif c <= -0.05:
        return c, "negative"
    return c, "neutral"


# ============================================================
# RSS-ПАРСИНГ
# ============================================================

def search_rss(query, limit=25):
    """Поиск постов через Reddit RSS."""
    url = "https://www.reddit.com/search.rss"
    params = {
        "q": query,
        "sort": "relevance",
        "t": "all",
        "limit": min(limit, 100),
    }

    try:
        r = SESSION.get(url, params=params, timeout=15)
        if r.status_code != 200:
            print(f"     ⚠️ RSS search status {r.status_code}")
            return []
        return parse_rss_entries(r.content)
    except Exception as e:
        print(f"     ❌ RSS error: {e}")
        return []


def fetch_post_comments_rss(post_url, limit=100):
    """Получает комментарии поста через RSS."""
    rss_url = post_url.rstrip('/') + '.rss'
    if '?' in rss_url:
        rss_url = rss_url.split('?')[0] + '.rss'

    params = {"limit": limit}
    try:
        r = SESSION.get(rss_url, params=params, timeout=15)
        if r.status_code != 200:
            return []
        return parse_rss_entries(r.content)
    except:
        return []


def parse_rss_entries(content):
    """Парсит RSS XML в список словарей."""
    entries = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return entries

    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    for entry in root.findall('atom:entry', ns):
        title_el = entry.find('atom:title', ns)
        link_el = entry.find('atom:link', ns)
        content_el = entry.find('atom:content', ns)
        author_el = entry.find('atom:author/atom:name', ns)
        updated_el = entry.find('atom:updated', ns)
        category_el = entry.find('atom:category', ns)

        title = title_el.text if title_el is not None and title_el.text else ""
        link = link_el.get('href', '') if link_el is not None else ""
        raw_content = content_el.text if content_el is not None and content_el.text else ""
        author = author_el.text if author_el is not None and author_el.text else "[deleted]"
        if author.startswith('/u/'):
            author = author[3:]
        updated = updated_el.text if updated_el is not None and updated_el.text else ""
        subreddit = category_el.get('term', '') if category_el is not None else ""

        body = clean_html(raw_content)

        if not body or body in ['[deleted]', '[removed]']:
            continue

        # Skip entries that are just subreddit links (not actual posts)
        if re.match(r'^https://www\.reddit\.com/r/[^/]+/?$', link):
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


# ============================================================
# ОСНОВНОЙ ПАРСЕР
# ============================================================

def scrape_couple_app_reviews(target_apps=None, limit_per_query=25, output_dir="reviews"):
    """
    Основная функция: парсит Reddit на тему приложений для пар.
    """

    if target_apps:
        apps = {k: v for k, v in COUPLE_APPS.items() if k in target_apps}
    else:
        apps = COUPLE_APPS

    if not apps:
        print("❌ Приложения не найдены!")
        return

    os.makedirs(output_dir, exist_ok=True)

    all_reviews = []
    seen_texts = set()  # дедупликация по хешу текста

    print("=" * 60)
    print("💑 REDDIT COUPLE APPS REVIEW SCRAPER")
    print("=" * 60)
    print(f"📱 Приложения: {', '.join(apps.keys())}")
    print(f"📊 Лимит на запрос: {limit_per_query}")
    print(f"📁 Результаты: {output_dir}/")
    print("=" * 60)

    total_start = time.time()

    # ======= СТРАТЕГИЯ 1: Поиск по названию приложения =======
    for app_name, app_config in apps.items():
        print(f"\n{'─' * 50}")
        print(f"📱 Ищем отзывы: {app_name}")
        print(f"{'─' * 50}")

        for query in app_config["search_queries"]:
            print(f"\n  🔍 Поиск: \"{query}\"")

            entries = search_rss(query, limit=limit_per_query)
            print(f"     📄 Найдено записей: {len(entries)}")

            for entry in entries:
                full_text = f"{entry['title']} {entry['body']}"
                text_hash = hash(full_text[:200])

                if text_hash in seen_texts:
                    continue

                if not detect_app(full_text, app_config):
                    continue

                seen_texts.add(text_hash)
                print(f"     ✅ {entry['title'][:70]}")

                _add_review(all_reviews, app_name, "post", entry, full_text)

                # Скрапим комментарии
                link = entry["link"]
                if '/comments/' in link:
                    print(f"        💬 Комментарии...")
                    comments = fetch_post_comments_rss(link)
                    time.sleep(random.uniform(*COOLDOWN))

                    comment_count = 0
                    for i, comment in enumerate(comments):
                        if i == 0:
                            continue  # Первый — сам пост
                        c_text = comment["body"]
                        if len(c_text) < 15 or c_text in ['[deleted]', '[removed]']:
                            continue

                        c_hash = hash(c_text[:200])
                        if c_hash in seen_texts:
                            continue

                        c_lower = c_text.lower()
                        is_relevant = (
                            detect_app(c_text, app_config) or
                            any(kw in c_lower for kw in [
                                "app", "recommend", "download", "tried",
                                "using", "used", "subscription", "free",
                                "paid", "features", "questions", "daily",
                            ])
                        )
                        if not is_relevant:
                            continue

                        seen_texts.add(c_hash)
                        comment["link"] = link
                        _add_review(all_reviews, app_name, "comment", comment, c_text)
                        comment_count += 1

                    print(f"        💬 +{comment_count} комментариев")

            time.sleep(random.uniform(*COOLDOWN))

    # ======= СТРАТЕГИЯ 2: Общие запросы =======
    print(f"\n{'═' * 60}")
    print("🔍 ОБЩИЙ ПОИСК: приложения для пар")
    print(f"{'═' * 60}")

    for query in GENERIC_QUERIES:
        print(f"\n  🔎 \"{query}\"")
        entries = search_rss(query, limit=limit_per_query)
        print(f"     📄 Найдено: {len(entries)}")

        for entry in entries:
            full_text = f"{entry['title']} {entry['body']}"
            text_hash = hash(full_text[:200])
            if text_hash in seen_texts:
                continue

            detected = detect_any_app(full_text, apps)
            if not detected:
                couple_keywords = ["couple app", "couples app", "relationship app",
                                   "app for couples", "date night app"]
                if not any(kw in full_text.lower() for kw in couple_keywords):
                    continue
                detected = ["General / Общее"]

            seen_texts.add(text_hash)

            for det_app in detected:
                _add_review(all_reviews, det_app, "post", entry, full_text)

            # Комментарии
            link = entry["link"]
            if '/comments/' in link:
                comments = fetch_post_comments_rss(link)
                time.sleep(random.uniform(*COOLDOWN))

                for i, comment in enumerate(comments):
                    if i == 0:
                        continue
                    c_text = comment["body"]
                    if len(c_text) < 15:
                        continue

                    c_hash = hash(c_text[:200])
                    if c_hash in seen_texts:
                        continue

                    c_detected = detect_any_app(c_text, apps)
                    if not c_detected:
                        c_lower = c_text.lower()
                        if any(kw in c_lower for kw in ["app", "recommend", "download", "tried", "using"]):
                            c_detected = ["General / Общее"]
                        else:
                            continue

                    seen_texts.add(c_hash)
                    comment["link"] = link
                    for det_app in c_detected:
                        _add_review(all_reviews, det_app, "comment", comment, c_text)

        time.sleep(random.uniform(*COOLDOWN))

    # ============================================================
    # СОХРАНЕНИЕ
    # ============================================================
    elapsed = time.time() - total_start

    print(f"\n{'═' * 60}")
    print("💾 СОХРАНЕНИЕ РЕЗУЛЬТАТОВ")
    print(f"{'═' * 60}")

    if not all_reviews:
        print("⚠️ Отзывы не найдены!")
        return

    df = pd.DataFrame(all_reviews)

    # 1. Все отзывы
    f1 = f"{output_dir}/all_reviews.csv"
    df.to_csv(f1, index=False, encoding="utf-8-sig")
    print(f"  ✅ {f1} — {len(df)} отзывов")

    # 2. По приложениям
    for app_name in df["app_name"].unique():
        app_df = df[df["app_name"] == app_name]
        safe = re.sub(r'[^\w\-]', '_', app_name)
        f2 = f"{output_dir}/reviews_{safe}.csv"
        app_df.to_csv(f2, index=False, encoding="utf-8-sig")
        print(f"  ✅ {f2} — {len(app_df)} отзывов")

    # 3. По категориям (развёрнутая таблица)
    cat_rows = []
    for _, row in df.iterrows():
        for cat in row["categories"].split(" | "):
            cat_rows.append({
                "category": cat.strip(),
                "app_name": row["app_name"],
                "text": row["text"],
                "sentiment_label": row["sentiment_label"],
                "sentiment_score": row["sentiment_score"],
                "author": row["author"],
                "subreddit": row["subreddit"],
                "permalink": row["permalink"],
                "date": row["date"],
            })
    df_cat = pd.DataFrame(cat_rows)
    f3 = f"{output_dir}/reviews_by_category.csv"
    df_cat.to_csv(f3, index=False, encoding="utf-8-sig")
    print(f"  ✅ {f3} — {len(df_cat)} записей")

    # 4. Только тексты отзывов (удобно для чтения)
    f4 = f"{output_dir}/reviews_text_only.csv"
    df[["app_name", "primary_category", "sentiment_label", "text", "author", "subreddit", "permalink"]].to_csv(
        f4, index=False, encoding="utf-8-sig"
    )
    print(f"  ✅ {f4}")

    # 5. Статистика JSON
    stats = _generate_stats(df)
    f5 = f"{output_dir}/stats_summary.json"
    with open(f5, "w", encoding="utf-8") as fj:
        json.dump(stats, fj, ensure_ascii=False, indent=2)
    print(f"  ✅ {f5}")

    # 6. Markdown-отчёт
    f6 = f"{output_dir}/REPORT.md"
    _generate_report(df, stats, f6)
    print(f"  ✅ {f6}")

    # ============================================================
    # ФИНАЛЬНАЯ СТАТИСТИКА
    # ============================================================
    print(f"\n{'═' * 60}")
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print(f"{'═' * 60}")
    print(f"  ⏱️  Время: {elapsed:.1f}s")
    print(f"  📝 Всего отзывов: {len(df)}")
    print(f"  📄 Из постов: {len(df[df['source']=='post'])}")
    print(f"  💬 Из комментариев: {len(df[df['source']=='comment'])}")

    print(f"\n  📱 По приложениям:")
    for app, cnt in df["app_name"].value_counts().items():
        print(f"     {app}: {cnt}")

    print(f"\n  📂 По категориям:")
    for cat, cnt in df["primary_category"].value_counts().head(10).items():
        print(f"     {cat}: {cnt}")

    print(f"\n  😊 Тональность:")
    for label, cnt in df["sentiment_label"].value_counts().items():
        emoji = {"positive": "😊", "negative": "😞", "neutral": "😐"}.get(label, "❓")
        print(f"     {emoji} {label}: {cnt}")

    print(f"\n{'═' * 60}")
    print(f"✅ ГОТОВО! Результаты → {output_dir}/")
    print(f"{'═' * 60}")


def _add_review(reviews_list, app_name, source, entry, text):
    """Добавляет отзыв в список."""
    sentiment_score, sentiment_label = analyze_sentiment(text)
    categories = categorize_review(text)

    reviews_list.append({
        "app_name": app_name,
        "source": source,
        "author": entry.get("author", "[unknown]"),
        "title": entry.get("title", ""),
        "text": text.strip()[:2000],
        "subreddit": entry.get("subreddit", ""),
        "permalink": entry.get("link", ""),
        "date": entry.get("updated", ""),
        "sentiment_score": round(sentiment_score, 3),
        "sentiment_label": sentiment_label,
        "categories": " | ".join(categories),
        "primary_category": categories[0],
    })


def _generate_stats(df):
    """Генерирует сводную статистику."""
    stats = {
        "total_reviews": len(df),
        "posts_count": int(len(df[df["source"] == "post"])),
        "comments_count": int(len(df[df["source"] == "comment"])),
        "apps": {},
        "categories": {},
        "sentiment": {},
        "subreddits": {},
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    for app_name, g in df.groupby("app_name"):
        stats["apps"][app_name] = {
            "total": int(len(g)),
            "avg_sentiment": round(float(g["sentiment_score"].mean()), 3),
            "positive": int(len(g[g["sentiment_label"] == "positive"])),
            "negative": int(len(g[g["sentiment_label"] == "negative"])),
            "neutral": int(len(g[g["sentiment_label"] == "neutral"])),
            "top_categories": {k: int(v) for k, v in g["primary_category"].value_counts().head(5).items()},
        }

    stats["categories"] = {k: int(v) for k, v in df["primary_category"].value_counts().items()}
    stats["sentiment"] = {k: int(v) for k, v in df["sentiment_label"].value_counts().items()}
    stats["subreddits"] = {k: int(v) for k, v in df["subreddit"].value_counts().items()}

    return stats


def _generate_report(df, stats, filepath):
    """Генерирует Markdown отчёт."""
    r = []
    r.append("# 💑 Отчёт: Отзывы о приложениях для пар с Reddit\n")
    r.append(f"**Дата:** {stats['generated_at']}\n")
    r.append(f"**Всего отзывов:** {stats['total_reviews']}  ")
    r.append(f"**Из постов:** {stats['posts_count']} | **Из комментариев:** {stats['comments_count']}\n")
    r.append("\n---\n")

    r.append("## 📱 По приложениям\n")
    r.append("| Приложение | Отзывов | Ср. тональность | 😊 | 😞 | 😐 |")
    r.append("|---|---|---|---|---|---|")
    for app, s in sorted(stats["apps"].items(), key=lambda x: x[1]["total"], reverse=True):
        r.append(f"| {app} | {s['total']} | {s['avg_sentiment']:.2f} | {s['positive']} | {s['negative']} | {s['neutral']} |")

    r.append("\n---\n")

    r.append("## 📂 По категориям\n")
    r.append("| Категория | Кол-во |")
    r.append("|---|---|")
    for cat, cnt in sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True):
        r.append(f"| {cat} | {cnt} |")

    r.append("\n---\n")

    r.append("## ⭐ Топ позитивные отзывы\n")
    pos = df[df["sentiment_label"] == "positive"].nlargest(10, "sentiment_score")
    for _, row in pos.iterrows():
        r.append(f"**{row['app_name']}** (r/{row['subreddit']})")
        r.append(f"> {row['text'][:300].replace(chr(10), ' ')}...\n")

    r.append("\n---\n")

    r.append("## 😞 Топ негативные отзывы\n")
    neg = df[df["sentiment_label"] == "negative"].nsmallest(10, "sentiment_score")
    for _, row in neg.iterrows():
        r.append(f"**{row['app_name']}** (r/{row['subreddit']})")
        r.append(f"> {row['text'][:300].replace(chr(10), ' ')}...\n")

    r.append("\n---\n")

    r.append("## 📋 Примеры отзывов по категориям\n")
    for cat_name, cat_cfg in REVIEW_CATEGORIES.items():
        mask = df["categories"].str.contains(re.escape(cat_name), na=False)
        subset = df[mask]
        if len(subset) == 0:
            continue
        r.append(f"### {cat_name}")
        r.append(f"*{cat_cfg['description']}* ({len(subset)} отзывов)\n")
        for _, row in subset.head(3).iterrows():
            r.append(f"- **{row['app_name']}**: {row['text'][:200].replace(chr(10), ' ')}...\n")
        r.append("")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(r))


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="💑 Reddit Couple Apps Review Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python couple_apps_scraper.py                                 # Все приложения
  python couple_apps_scraper.py --app "Couple Joy"              # Только Couple Joy
  python couple_apps_scraper.py --app "Paired" --app "Lovewick" # Несколько
  python couple_apps_scraper.py --limit 50                      # Больше постов
  python couple_apps_scraper.py --output my_reviews             # Своя папка
  python couple_apps_scraper.py --list-apps                     # Список приложений
  python couple_apps_scraper.py --list-categories               # Категории
        """
    )

    parser.add_argument("--app", action="append", help="Название приложения (можно несколько раз)")
    parser.add_argument("--limit", type=int, default=25, help="Лимит постов на запрос (default: 25)")
    parser.add_argument("--output", type=str, default="reviews", help="Папка для результатов (default: reviews)")
    parser.add_argument("--list-apps", action="store_true", help="Показать список приложений")
    parser.add_argument("--list-categories", action="store_true", help="Показать категории")

    args = parser.parse_args()

    if args.list_apps:
        print("\n📱 Поддерживаемые приложения:")
        print("─" * 40)
        for name, cfg in COUPLE_APPS.items():
            print(f"  • {name}")
            print(f"    Запросы: {', '.join(cfg['search_queries'][:3])}")
        print()
        return

    if args.list_categories:
        print("\n📂 Категории отзывов:")
        print("─" * 40)
        for name, cfg in REVIEW_CATEGORIES.items():
            print(f"  {name}")
            print(f"    {cfg['description']}")
            kws = ', '.join(cfg['keywords'][:5])
            print(f"    Ключевые слова: {kws}...")
            print()
        return

    scrape_couple_app_reviews(
        target_apps=args.app,
        limit_per_query=args.limit,
        output_dir=args.output,
    )


if __name__ == "__main__":
    main()
