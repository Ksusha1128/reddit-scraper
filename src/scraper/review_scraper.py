"""
Review scraper — core scraping logic.

Strategies:
  1. Search RSS — per-app search queries
  2. Generic RSS — niche-wide generic queries
  3. Subreddit RSS — parse niche subreddits directly (new!)
  4. Subreddit JSON — Reddit JSON API for deeper results (new!)

Key rules:
  - Every post MUST be assigned to a niche (no "General" bucket)
  - Posts mentioning no specific app -> niche still assigned via text analysis
  - Word-boundary alias matching to avoid false positives
"""

from __future__ import annotations

import re
import time

from src.analytics.categorizer import categorize_text
from src.analytics.sentiment import analyze_sentiment
from src.apps import GENERIC_QUERIES, GENERIC_QUERIES_FLAT, TRACKED_APPS, get_apps_by_niche
from src.logging import get_logger
from src.models import (
    AppConfig,
    AppNiche,
    Review,
    ReviewCategory,
    ReviewSource,
    RSSEntry,
    ScrapeResult,
)
from src.scraper.http_client import RedditClient
from src.scraper.rss_parser import parse_rss_feed

logger = get_logger(__name__)

# -- Niche subreddits to scrape directly --

NICHE_SUBREDDITS: dict[AppNiche, list[str]] = {
    AppNiche.RELATIONSHIPS: [
        "relationships", "relationship_advice", "Marriage", "LongDistance",
        "LDR", "DeadBedrooms", "dating_advice",
        "mentalhealth", "Anxiety", "depression", "therapy", "TalkTherapy",
        "Meditation", "ADHD", "BPD",
        "couple_apps", "LoveLanguages",
    ],
    AppNiche.SMOKING: [
        "stopsmoking", "quittingsmoking", "smokingcessation",
        "leaves", "stopdrinking",
    ],
    AppNiche.PLANT_SCANNER: [
        "whatsthisplant", "PlantIdentification", "houseplants",
        "gardening", "plants", "plantclinic", "succulents",
        "mycology", "SavageGarden",
    ],
    AppNiche.CALORIE_TRACKER: [
        "loseit", "CICO", "caloriecount", "Myfitnesspal",
        "1200isplenty", "1500isplenty", "intermittentfasting",
        "EatCheapAndHealthy", "nutrition", "MacroFactor",
        "cronometer", "Fitness", "xxfitness",
    ],
}


class ReviewScraper:
    """
    Scraper that collects app reviews from Reddit.

    Strategies:
      1. Per-app search queries (RSS)
      2. Generic niche queries (RSS)
      3. Subreddit direct scrape (RSS)
      4. Subreddit JSON API (deeper)
    """

    def __init__(self, client: RedditClient | None = None) -> None:
        self._client = client or RedditClient()
        self._seen: set[str] = set()
        self._reviews: list[Review] = []

    async def run(
        self,
        target_apps: list[str] | None = None,
        limit_per_query: int = 25,
    ) -> ScrapeResult:
        start = time.monotonic()
        errors: list[str] = []

        if target_apps:
            apps = [a for a in TRACKED_APPS if a.name in target_apps]
        else:
            apps = list(TRACKED_APPS)

        if not apps:
            errors.append(f"No matching apps found for: {target_apps}")
            return ScrapeResult(errors=errors)

        logger.info("scrape_start", apps=len(apps), limit_per_query=limit_per_query)

        # Strategy 1: search by app name
        for app in apps:
            for query in app.search_queries:
                try:
                    await self._search_and_collect(query, app, limit_per_query)
                except Exception as exc:
                    msg = f"Error searching '{query}': {exc}"
                    logger.error("search_error", query=query, error=str(exc))
                    errors.append(msg)

        # Strategy 2: generic queries (per niche)
        for niche, queries in GENERIC_QUERIES.items():
            niche_apps = [a for a in apps if a.niche == niche]
            for query in queries:
                try:
                    await self._search_generic(query, niche_apps, niche, limit_per_query)
                except Exception as exc:
                    msg = f"Error in generic search '{query}': {exc}"
                    logger.error("generic_search_error", query=query, error=str(exc))
                    errors.append(msg)

        # Strategy 3: scrape niche subreddits directly (RSS)
        for niche, subreddits in NICHE_SUBREDDITS.items():
            niche_apps = [a for a in apps if a.niche == niche]
            for sub in subreddits:
                try:
                    await self._scrape_subreddit_rss(sub, niche_apps, niche, limit_per_query)
                except Exception as exc:
                    msg = f"Error scraping r/{sub}: {exc}"
                    logger.error("subreddit_error", sub=sub, error=str(exc))
                    errors.append(msg)

        # Strategy 4: subreddit JSON API (deeper, top 5 per niche)
        for niche, subreddits in NICHE_SUBREDDITS.items():
            niche_apps = [a for a in apps if a.niche == niche]
            for sub in subreddits[:5]:
                try:
                    await self._scrape_subreddit_json(sub, niche_apps, niche)
                except Exception as exc:
                    msg = f"Error JSON r/{sub}: {exc}"
                    logger.error("json_error", sub=sub, error=str(exc))
                    errors.append(msg)

        elapsed = time.monotonic() - start
        result = ScrapeResult(
            total_reviews=len(self._reviews),
            posts_found=sum(1 for r in self._reviews if r.source == ReviewSource.POST),
            comments_found=sum(1 for r in self._reviews if r.source == ReviewSource.COMMENT),
            duplicates_skipped=len(self._seen) - len(self._reviews),
            duration_seconds=round(elapsed, 2),
            errors=errors,
        )
        logger.info("scrape_complete", total_reviews=result.total_reviews, duration=result.duration_seconds)
        return result

    @property
    def reviews(self) -> list[Review]:
        return list(self._reviews)

    # -- Strategy 1: App-specific search --

    async def _search_and_collect(self, query: str, app: AppConfig, limit: int) -> None:
        rss_content = await self._client.get_rss(
            "https://www.reddit.com/search.rss",
            params={"q": query, "sort": "relevance", "t": "all", "limit": min(limit, 100)},
        )
        if not rss_content:
            return
        entries = parse_rss_feed(rss_content)
        logger.debug("rss_results", query=query, count=len(entries))
        for entry in entries:
            full_text = f"{entry.title} {entry.body}"
            content_hash = RedditClient.content_hash(full_text)
            if content_hash in self._seen:
                continue
            self._seen.add(content_hash)
            if not _text_mentions_app(full_text, app):
                continue
            self._add_review(app.name, ReviewSource.POST, entry, full_text)
            if "/comments/" in entry.link:
                await self._collect_comments(entry.link, app)

    # -- Strategy 2: Generic queries --

    async def _search_generic(self, query: str, apps: list[AppConfig], niche: AppNiche, limit: int) -> None:
        rss_content = await self._client.get_rss(
            "https://www.reddit.com/search.rss",
            params={"q": query, "sort": "relevance", "t": "all", "limit": min(limit, 100)},
        )
        if not rss_content:
            return
        entries = parse_rss_feed(rss_content)
        for entry in entries:
            full_text = f"{entry.title} {entry.body}"
            content_hash = RedditClient.content_hash(full_text)
            if content_hash in self._seen:
                continue
            detected = _detect_apps_in_text(full_text, apps)
            if not detected:
                niche_keywords = _NICHE_KEYWORDS.get(niche, [])
                if not any(kw in full_text.lower() for kw in niche_keywords):
                    continue
                detected = [f"[{niche.value}]"]
            self._seen.add(content_hash)
            for app_name in detected:
                self._add_review(app_name, ReviewSource.POST, entry, full_text)
            if "/comments/" in entry.link:
                await self._collect_comments_generic(entry.link, apps, niche)

    # -- Strategy 3: Subreddit RSS scrape --

    async def _scrape_subreddit_rss(self, subreddit: str, apps: list[AppConfig], niche: AppNiche, limit: int) -> None:
        for sort in ("new", "hot", "top"):
            rss_content = await self._client.get_rss(
                f"https://www.reddit.com/r/{subreddit}/{sort}.rss",
                params={"limit": min(limit, 100)},
            )
            if not rss_content:
                continue
            entries = parse_rss_feed(rss_content)
            logger.debug("subreddit_rss", sub=subreddit, sort=sort, count=len(entries))
            for entry in entries:
                full_text = f"{entry.title} {entry.body}"
                content_hash = RedditClient.content_hash(full_text)
                if content_hash in self._seen:
                    continue
                detected = _detect_apps_in_text(full_text, apps)
                niche_keywords = _NICHE_KEYWORDS.get(niche, [])
                if not detected and not any(kw in full_text.lower() for kw in niche_keywords):
                    continue
                self._seen.add(content_hash)
                if detected:
                    for app_name in detected:
                        self._add_review(app_name, ReviewSource.POST, entry, full_text)
                else:
                    self._add_review(f"[{niche.value}]", ReviewSource.POST, entry, full_text)
                if "/comments/" in entry.link:
                    await self._collect_comments_generic(entry.link, apps, niche)

    # -- Strategy 4: Subreddit JSON API --

    async def _scrape_subreddit_json(self, subreddit: str, apps: list[AppConfig], niche: AppNiche) -> None:
        after = None
        for page in range(3):
            params: dict = {"limit": 25, "raw_json": 1}
            if after:
                params["after"] = after
            data = await self._client.get_json(f"/r/{subreddit}/new.json", params=params)
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
                permalink = f"https://reddit.com{post.get('permalink', '')}"
                author = post.get("author", "[deleted]")
                created = post.get("created_utc", 0)
                sub = post.get("subreddit", subreddit)
                full_text = f"{title} {selftext}"
                content_hash = RedditClient.content_hash(full_text)
                if content_hash in self._seen:
                    continue
                if not full_text.strip() or full_text.strip() in ("[deleted]", "[removed]"):
                    continue
                detected = _detect_apps_in_text(full_text, apps)
                niche_keywords = _NICHE_KEYWORDS.get(niche, [])
                if not detected and not any(kw in full_text.lower() for kw in niche_keywords):
                    continue
                self._seen.add(content_hash)
                from datetime import datetime, timezone
                dt = datetime.fromtimestamp(created, tz=timezone.utc).isoformat() if created else ""
                entry = RSSEntry(title=title, link=permalink, body=selftext[:5000], author=author, updated=dt, subreddit=sub)
                if detected:
                    for app_name in detected:
                        self._add_review(app_name, ReviewSource.POST, entry, full_text)
                else:
                    self._add_review(f"[{niche.value}]", ReviewSource.POST, entry, full_text)
            if not after:
                break

    # -- Comment collection --

    async def _collect_comments(self, post_url: str, app: AppConfig) -> None:
        rss_url = post_url.rstrip("/").split("?")[0] + ".rss"
        rss_content = await self._client.get_rss(rss_url, params={"limit": 100})
        if not rss_content:
            return
        entries = parse_rss_feed(rss_content)
        relevance_keywords = {"app", "recommend", "download", "tried", "using", "used", "subscription", "free", "paid", "features", "questions", "daily"}
        for i, comment in enumerate(entries):
            if i == 0:
                continue
            if len(comment.body) < 15:
                continue
            content_hash = RedditClient.content_hash(comment.body)
            if content_hash in self._seen:
                continue
            text_lower = comment.body.lower()
            is_relevant = _text_mentions_app(comment.body, app) or any(kw in text_lower for kw in relevance_keywords)
            if not is_relevant:
                continue
            self._seen.add(content_hash)
            comment_with_link = RSSEntry(**{**comment.model_dump(), "link": post_url})
            self._add_review(app.name, ReviewSource.COMMENT, comment_with_link, comment.body)

    async def _collect_comments_generic(self, post_url: str, apps: list[AppConfig], niche: AppNiche) -> None:
        rss_url = post_url.rstrip("/").split("?")[0] + ".rss"
        rss_content = await self._client.get_rss(rss_url, params={"limit": 100})
        if not rss_content:
            return
        entries = parse_rss_feed(rss_content)
        for i, comment in enumerate(entries):
            if i == 0:
                continue
            if len(comment.body) < 15:
                continue
            content_hash = RedditClient.content_hash(comment.body)
            if content_hash in self._seen:
                continue
            detected = _detect_apps_in_text(comment.body, apps)
            if not detected:
                text_lower = comment.body.lower()
                relevance = ("app", "recommend", "download", "tried", "using")
                if any(kw in text_lower for kw in relevance):
                    detected = [f"[{niche.value}]"]
                else:
                    continue
            self._seen.add(content_hash)
            comment_with_link = RSSEntry(**{**comment.model_dump(), "link": post_url})
            for app_name in detected:
                self._add_review(app_name, ReviewSource.COMMENT, comment_with_link, comment.body)

    # -- Review builder --

    def _add_review(self, app_name: str, source: ReviewSource, entry: RSSEntry, text: str) -> None:
        score, label = analyze_sentiment(text)
        categories = categorize_text(text)
        try:
            review = Review(
                app_name=app_name,
                source=source,
                author=entry.author,
                title=entry.title,
                text=text[:5000],
                subreddit=entry.subreddit,
                permalink=entry.link,
                sentiment_score=score,
                sentiment_label=label,
                categories=categories,
                primary_category=categories[0] if categories else ReviewCategory.UNCATEGORIZED,
            )
            self._reviews.append(review)
        except Exception as exc:
            logger.debug("review_validation_error", error=str(exc))


# -- Module-level helpers --

_alias_cache: dict[str, re.Pattern] = {}

def _get_alias_pattern(alias: str) -> re.Pattern:
    """Compiled word-boundary regex for an alias — avoids false positives."""
    if alias not in _alias_cache:
        escaped = re.escape(alias)
        _alias_cache[alias] = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
    return _alias_cache[alias]

def _text_mentions_app(text: str, app: AppConfig) -> bool:
    """Check if text mentions any of the app's aliases using word boundaries."""
    for alias in app.aliases:
        if _get_alias_pattern(alias).search(text):
            return True
    return False

def _detect_apps_in_text(text: str, apps: list[AppConfig]) -> list[str]:
    """Return names of all apps mentioned in text."""
    return [app.name for app in apps if _text_mentions_app(text, app)]

# -- Niche keyword lists --

_NICHE_KEYWORDS: dict[AppNiche, list[str]] = {
    AppNiche.RELATIONSHIPS: [
        "couple app", "couples app", "relationship app",
        "app for couples", "date night app",
        "couple widget", "love language", "couple quiz",
        "couple game", "long distance app", "intimacy app",
        "therapy app", "mental health app", "meditation app",
        "ai therapist", "cbt app", "anxiety app",
        "mood tracker", "mindfulness app", "counseling app",
        "self care app", "journaling app",
    ],
    AppNiche.SMOKING: [
        "quit smoking app", "stop smoking app",
        "quit vaping app", "nicotine app", "cessation app",
        "quit smoking", "stop smoking", "nicotine replacement",
    ],
    AppNiche.PLANT_SCANNER: [
        "plant identifier", "plant scanner", "plant care app",
        "plant id app", "identify plant", "garden app",
        "what plant is this", "plant identification",
    ],
    AppNiche.CALORIE_TRACKER: [
        "calorie tracker", "calorie counter", "nutrition app",
        "food tracker", "macro tracker", "diet app",
        "food logging", "food diary", "calorie app",
        "weight loss app", "fasting app",
    ],
}
