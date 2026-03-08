"""
Fetch comments for all posts in reviews/all_reviews.csv.
Simple synchronous version using requests — no async complexity.
"""

import hashlib
import html
import re
import time
import xml.etree.ElementTree as ET

import pandas as pd
import requests

from src.analytics.categorizer import categorize_text
from src.analytics.sentiment import analyze_sentiment
from src.models import ReviewCategory

CSV_PATH = "reviews/all_reviews.csv"
SAVE_EVERY = 200

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

_NS = {"atom": "http://www.w3.org/2005/Atom"}


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _post_base(url: str) -> str:
    m = re.search(r"(/r/\w+/comments/\w+)", str(url))
    return m.group(1) if m else str(url)


def clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_comments_from_rss(xml_text: str) -> list[dict]:
    """Parse RSS XML, return list of comment dicts (skip first entry = post)."""
    results = []
    try:
        root = ET.fromstring(xml_text.encode() if isinstance(xml_text, str) else xml_text)
    except ET.ParseError:
        return results

    entries = root.findall("atom:entry", _NS)
    for i, entry in enumerate(entries):
        if i == 0:  # first entry is the post itself
            continue
        title_el = entry.find("atom:title", _NS)
        content_el = entry.find("atom:content", _NS)
        author_el = entry.find("atom:author/atom:name", _NS)
        updated_el = entry.find("atom:updated", _NS)
        cat_el = entry.find("atom:category", _NS)

        body = clean_html((content_el.text or "").strip() if content_el is not None else "")
        if len(body) < 10:
            continue
        if body in ("[deleted]", "[removed]"):
            continue

        author = (author_el.text or "").strip() if author_el is not None else "[deleted]"
        if author.startswith("/u/"):
            author = author[3:]

        results.append({
            "title": (title_el.text or "").strip() if title_el is not None else "",
            "body": body,
            "author": author,
            "updated": (updated_el.text or "").strip() if updated_el is not None else "",
            "subreddit": cat_el.get("term", "") if cat_el is not None else "",
        })
    return results


def fetch_post_comments(permalink: str) -> list[dict] | None:
    """Fetch comments for a single post via RSS. Returns list or None on error."""
    rss_url = permalink.rstrip("/").split("?")[0] + ".rss"
    try:
        resp = requests.get(rss_url, headers=HEADERS, params={"limit": 100}, timeout=15)
        if resp.status_code == 429:
            time.sleep(5)
            resp = requests.get(rss_url, headers=HEADERS, params={"limit": 100}, timeout=15)
        if resp.status_code != 200:
            return None
        return parse_comments_from_rss(resp.text)
    except Exception:
        return None


def main():
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} rows ({(df['source']=='post').sum()} posts, "
          f"{(df['source']=='comment').sum()} comments)")

    posts = df[df["source"] == "post"].copy()
    existing_comments = df[df["source"] == "comment"].copy()

    # Only process posts from last 3 months
    if "date" in posts.columns:
        posts["date"] = pd.to_datetime(posts["date"], errors="coerce", utc=True)
        cutoff = posts["date"].max() - pd.Timedelta(days=30)
        posts = posts[posts["date"] >= cutoff]
        print(f"Filtered to last 1 month: {len(posts)} posts")

    # Skip posts that already have comments
    already_done: set[str] = set()
    if not existing_comments.empty:
        already_done = set(existing_comments["permalink"].fillna("").apply(_post_base))

    posts["_base"] = posts["permalink"].fillna("").apply(_post_base)
    todo = posts.drop_duplicates(subset="_base")
    todo = todo[~todo["_base"].isin(already_done)]
    print(f"Already done: {len(already_done)}, To process: {len(todo)}")

    # Hash set for dedup
    seen: set[str] = set()
    for txt in df["text"].dropna():
        seen.add(content_hash(str(txt)))

    new_rows: list[dict] = []
    processed = 0
    errors = 0
    empty = 0
    t0 = time.time()

    for _, row in todo.iterrows():
        permalink = str(row.get("permalink", ""))
        if not permalink or "/comments/" not in permalink:
            processed += 1
            continue

        comments = fetch_post_comments(permalink)
        if comments is None:
            errors += 1
            processed += 1
            time.sleep(1)
            continue

        if not comments:
            empty += 1
            processed += 1
            time.sleep(0.5)
            continue

        app_name = row.get("app_name", "")
        sub = row.get("subreddit", "")

        for c in comments:
            ch = content_hash(c["body"])
            if ch in seen:
                continue
            seen.add(ch)

            score, label = analyze_sentiment(c["body"])
            categories = categorize_text(c["body"])
            primary_cat = categories[0].value if categories else ReviewCategory.TOPIC_POST.value

            new_rows.append({
                "app_name": app_name,
                "source": "comment",
                "author": c["author"],
                "title": c["title"],
                "text": c["body"][:5000],
                "subreddit": c["subreddit"] or sub,
                "permalink": permalink,
                "date": c["updated"],
                "sentiment_score": score,
                "sentiment_label": label,
                "categories": "|".join(cat.value for cat in categories),
                "primary_category": primary_cat,
            })

        processed += 1
        time.sleep(0.3)  # rate limit

        if processed % 20 == 0:
            elapsed = time.time() - t0
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (len(todo) - processed) / rate / 60 if rate > 0 else 0
            print(f"  {processed}/{len(todo)} | +{len(new_rows)} comments | "
                  f"{empty} empty | {errors} err | {rate:.1f}/s | ETA {eta:.0f}m")

        if len(new_rows) >= SAVE_EVERY:
            _save(new_rows)
            new_rows.clear()

    if new_rows:
        _save(new_rows)

    elapsed = time.time() - t0
    print(f"\n✅ Done in {elapsed/60:.1f}m | {processed} posts | {errors} errors | {empty} empty")
    final = pd.read_csv(CSV_PATH)
    print(f"CSV: {len(final)} rows ({(final['source']=='post').sum()} posts, "
          f"{(final['source']=='comment').sum()} comments)")


def _save(rows: list[dict]) -> None:
    new_df = pd.DataFrame(rows)
    header_df = pd.read_csv(CSV_PATH, nrows=0)
    new_df = new_df.reindex(columns=header_df.columns)
    new_df.to_csv(CSV_PATH, mode="a", header=False, index=False)
    print(f"  💾 Saved {len(rows)} comments")


if __name__ == "__main__":
    main()
