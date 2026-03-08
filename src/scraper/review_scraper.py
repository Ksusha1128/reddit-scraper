"""
Review scraper — core scraping logic for couple app reviews.

Responsibilities:
- Search Reddit RSS for app-related posts
- Fetch comments from relevant posts
- Detect which app is mentioned
- Categorise reviews
- Analyse sentiment
- Deduplicate entries
"""

from __future__ import annotations

import time

from src.analytics.categorizer import categorize_text
from src.analytics.sentiment import analyze_sentiment
from src.apps import GENERIC_QUERIES_FLAT, TRACKED_APPS
from src.logging import get_logger
from src.models import (
    AppConfig,
    Review,
    ReviewCategory,
    ReviewSource,
    RSSEntry,
    ScrapeResult,
)
from src.scraper.http_client import RedditClient
from src.scraper.rss_parser import parse_rss_feed

logger = get_logger(__name__)


class ReviewScraper:
    """
    Async scraper that collects couple-app reviews from Reddit.

    Usage:
        scraper = ReviewScraper()
        result = await scraper.run(target_apps=["Couple Joy"], limit_per_query=25)
    """

    def __init__(self, client: RedditClient | None = None) -> None:
        self._client = client or RedditClient()
        self._seen: set[str] = set()  # content hashes for deduplication
        self._reviews: list[Review] = []

    async def run(
        self,
        target_apps: list[str] | None = None,
        limit_per_query: int = 25,
    ) -> ScrapeResult:
        """
        Execute the full scrape pipeline.

        Args:
            target_apps: List of app names to scrape (None = all).
            limit_per_query: Max RSS results per search query.

        Returns:
            ScrapeResult with counts and any errors.
        """
        start = time.monotonic()
        errors: list[str] = []

        # Resolve target apps
        if target_apps:
            apps = [a for a in TRACKED_APPS if a.name in target_apps]
        else:
            apps = list(TRACKED_APPS)

        if not apps:
            errors.append(f"No matching apps found for: {target_apps}")
            return ScrapeResult(errors=errors)

        logger.info(
            "scrape_start",
            apps=[a.name for a in apps],
            limit_per_query=limit_per_query,
        )

        # Strategy 1: search by app name
        for app in apps:
            for query in app.search_queries:
                try:
                    await self._search_and_collect(query, app, limit_per_query)
                except Exception as exc:  # noqa: BLE001
                    msg = f"Error searching '{query}': {exc}"
                    logger.error("search_error", query=query, error=str(exc))
                    errors.append(msg)

        # Strategy 2: generic queries (all niches)
        for query in GENERIC_QUERIES_FLAT:
            try:
                await self._search_generic(query, apps, limit_per_query)
            except Exception as exc:  # noqa: BLE001
                msg = f"Error in generic search '{query}': {exc}"
                logger.error("generic_search_error", query=query, error=str(exc))
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

        logger.info(
            "scrape_complete",
            total_reviews=result.total_reviews,
            duration=result.duration_seconds,
        )

        return result

    @property
    def reviews(self) -> list[Review]:
        """Access collected reviews."""
        return list(self._reviews)

    # ── Private helpers ──────────────────────────────────────────────────

    async def _search_and_collect(
        self, query: str, app: AppConfig, limit: int
    ) -> None:
        """Search RSS for a specific query and collect reviews for one app."""
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

            # Fetch comments for this post
            if "/comments/" in entry.link:
                await self._collect_comments(entry.link, app)

    async def _search_generic(
        self, query: str, apps: list[AppConfig], limit: int
    ) -> None:
        """Search generic couple-app queries, detect mentioned apps."""
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
                # Check if mentions any app-related keywords
                general_keywords = [
                    # Couple / Relationships
                    "couple app", "couples app", "relationship app",
                    "app for couples", "date night app",
                    "couple widget", "love language", "couple quiz",
                    "couple game", "long distance app", "intimacy app",
                    # Smoking / Vaping cessation
                    "quit smoking app", "stop smoking app",
                    "quit vaping app", "nicotine app", "cessation app",
                    # Mental Health / AI Therapy
                    "therapy app", "mental health app", "meditation app",
                    "ai therapist", "cbt app", "anxiety app",
                    "mood tracker", "mindfulness app", "counseling app",
                    # Plant identification
                    "plant identifier", "plant scanner", "plant care app",
                    "plant id app", "identify plant", "garden app",
                    # Calorie / Nutrition
                    "calorie tracker", "calorie counter", "nutrition app",
                    "food tracker", "macro tracker", "diet app",
                    "food logging", "food diary", "calorie app",
                ]
                if not any(kw in full_text.lower() for kw in general_keywords):
                    continue
                detected = ["General"]

            self._seen.add(content_hash)

            for app_name in detected:
                self._add_review(app_name, ReviewSource.POST, entry, full_text)

            # Comments
            if "/comments/" in entry.link:
                await self._collect_comments_generic(entry.link, apps)

    async def _collect_comments(self, post_url: str, app: AppConfig) -> None:
        """Fetch and filter comments for an app-specific post."""
        rss_url = post_url.rstrip("/").split("?")[0] + ".rss"
        rss_content = await self._client.get_rss(rss_url, params={"limit": 100})
        if not rss_content:
            return

        entries = parse_rss_feed(rss_content)
        relevance_keywords = {
            "app", "recommend", "download", "tried", "using",
            "used", "subscription", "free", "paid", "features",
            "questions", "daily",
        }

        for i, comment in enumerate(entries):
            if i == 0:
                continue  # First entry is the post itself
            if len(comment.body) < 15:
                continue

            content_hash = RedditClient.content_hash(comment.body)
            if content_hash in self._seen:
                continue

            text_lower = comment.body.lower()
            is_relevant = (
                _text_mentions_app(comment.body, app)
                or any(kw in text_lower for kw in relevance_keywords)
            )
            if not is_relevant:
                continue

            self._seen.add(content_hash)
            comment_with_link = RSSEntry(**{**comment.model_dump(), "link": post_url})
            self._add_review(app.name, ReviewSource.COMMENT, comment_with_link, comment.body)

    async def _collect_comments_generic(
        self, post_url: str, apps: list[AppConfig]
    ) -> None:
        """Fetch comments for a generic post, detect apps."""
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
                    detected = ["General"]
                else:
                    continue

            self._seen.add(content_hash)
            comment_with_link = RSSEntry(**{**comment.model_dump(), "link": post_url})
            for app_name in detected:
                self._add_review(app_name, ReviewSource.COMMENT, comment_with_link, comment.body)

    def _add_review(
        self,
        app_name: str,
        source: ReviewSource,
        entry: RSSEntry,
        text: str,
    ) -> None:
        """Build a Review model and append to results."""
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
        except Exception as exc:  # noqa: BLE001
            logger.debug("review_validation_error", error=str(exc))


# ── Module-level helpers ─────────────────────────────────────────────────────


def _text_mentions_app(text: str, app: AppConfig) -> bool:
    """Check if text mentions any of the app's aliases."""
    text_lower = text.lower()
    return any(alias in text_lower for alias in app.aliases)


def _detect_apps_in_text(text: str, apps: list[AppConfig]) -> list[str]:
    """Return names of all apps mentioned in text."""
    return [app.name for app in apps if _text_mentions_app(text, app)]
