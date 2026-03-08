"""
HTTP client with exponential backoff, rate limiting, and mirror rotation.

This is the ONLY place in the project that makes outbound HTTP requests.
All other modules go through this client.
"""

from __future__ import annotations

import asyncio
import hashlib
import random
from typing import Any

import httpx

from src.config import settings
from src.logging import get_logger

logger = get_logger(__name__)


class RedditClient:
    """
    Async HTTP client for Reddit with:
    - Mirror rotation with health tracking
    - Exponential backoff on failures
    - Configurable rate limiting (via asyncio.Semaphore)
    - Deterministic request deduplication
    """

    def __init__(self) -> None:
        cfg = settings.scraper
        self._timeout = httpx.Timeout(cfg.request_timeout)
        self._headers = {"User-Agent": cfg.user_agent}
        self._mirrors = list(cfg.mirrors)
        self._max_retries = cfg.max_retries
        self._backoff_factor = cfg.retry_backoff_factor
        self._cooldown_min = cfg.cooldown_min
        self._cooldown_max = cfg.cooldown_max

        # Track mirror health: mirror_url → consecutive_failures
        self._mirror_health: dict[str, int] = {m: 0 for m in self._mirrors}

        # Rate limiting — allow 2 concurrent requests for faster scraping
        self._semaphore = asyncio.Semaphore(2)

        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self._headers,
                timeout=self._timeout,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _pick_mirror(self) -> str:
        """Pick the healthiest mirror (fewest consecutive failures)."""
        healthy = [m for m, fails in self._mirror_health.items() if fails < 3]
        if not healthy:
            # Reset all mirrors if all are unhealthy
            self._mirror_health = {m: 0 for m in self._mirrors}
            healthy = list(self._mirrors)
        return random.choice(healthy)

    async def _cooldown(self) -> None:
        delay = random.uniform(self._cooldown_min, self._cooldown_max)
        await asyncio.sleep(delay)

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> dict | None:
        """
        GET JSON from reddit.com directly (no mirrors — they don't support JSON API).

        Args:
            path: URL path (e.g. "/r/relationships/new.json")
            params: Query parameters

        Returns:
            Parsed JSON or None on failure.
        """
        async with self._semaphore:
            client = await self._get_client()
            url = f"https://www.reddit.com{path}"

            for attempt in range(self._max_retries):
                try:
                    response = await client.get(url, params=params)

                    if response.status_code == 200:
                        await self._cooldown()
                        return response.json()

                    if response.status_code == 429:
                        wait = self._backoff_factor ** (attempt + 1)
                        logger.warning("rate_limited_json", url=url, retry_in=wait, attempt=attempt + 1)
                        await asyncio.sleep(wait)
                        continue

                    logger.warning("json_http_error", url=url, status=response.status_code, attempt=attempt + 1)

                except (httpx.TimeoutException, httpx.ConnectError) as exc:
                    wait = self._backoff_factor ** attempt
                    logger.warning("json_connection_error", url=url, error=str(exc), retry_in=wait, attempt=attempt + 1)
                    await asyncio.sleep(wait)

            logger.error("json_retries_exhausted", path=path)
            return None

    async def get_text(self, path: str, params: dict[str, Any] | None = None) -> str | None:
        """GET request returning raw text (for RSS feeds)."""
        async with self._semaphore:
            client = await self._get_client()

            for attempt in range(self._max_retries):
                mirror = self._pick_mirror()
                url = f"{mirror}{path}"

                try:
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        self._mirror_health[mirror] = 0
                        await self._cooldown()
                        return response.text

                    self._mirror_health[mirror] = self._mirror_health.get(mirror, 0) + 1
                    if response.status_code == 429:
                        await asyncio.sleep(self._backoff_factor ** (attempt + 1))
                        continue

                except (httpx.TimeoutException, httpx.ConnectError):
                    self._mirror_health[mirror] = self._mirror_health.get(mirror, 0) + 1
                    await asyncio.sleep(self._backoff_factor ** attempt)

            return None

    async def get_rss(self, url: str, params: dict[str, Any] | None = None) -> str | None:
        """
        GET request to a full URL (e.g. reddit.com RSS) — no mirror rotation.
        Used for RSS endpoints that only work on reddit.com itself.
        """
        async with self._semaphore:
            client = await self._get_client()

            for attempt in range(self._max_retries):
                try:
                    response = await client.get(url, params=params)
                    if response.status_code == 200:
                        await self._cooldown()
                        return response.text

                    if response.status_code == 429:
                        await asyncio.sleep(self._backoff_factor ** (attempt + 1))
                        continue

                except (httpx.TimeoutException, httpx.ConnectError):
                    await asyncio.sleep(self._backoff_factor ** attempt)

            return None

    @staticmethod
    def content_hash(text: str) -> str:
        """
        Deterministic hash for deduplication.
        Unlike Python's built-in hash(), this is stable across runs.
        """
        return hashlib.sha256(text[:500].encode("utf-8")).hexdigest()[:16]
