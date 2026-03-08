"""Tests for the HTTP client."""

from __future__ import annotations

from src.scraper.http_client import RedditClient


class TestContentHash:
    """Test deterministic content hashing."""

    def test_same_input_same_hash(self):
        h1 = RedditClient.content_hash("Hello world")
        h2 = RedditClient.content_hash("Hello world")
        assert h1 == h2

    def test_different_input_different_hash(self):
        h1 = RedditClient.content_hash("Hello world")
        h2 = RedditClient.content_hash("Goodbye world")
        assert h1 != h2

    def test_hash_is_string(self):
        h = RedditClient.content_hash("test")
        assert isinstance(h, str)
        assert len(h) == 16  # sha256[:16]

    def test_long_text_truncated(self):
        """Hash uses first 500 chars — so texts identical in first 500 chars produce same hash."""
        base = "a" * 500
        h1 = RedditClient.content_hash(base + "suffix1")
        h2 = RedditClient.content_hash(base + "suffix2")
        assert h1 == h2  # Both truncated to same 500 chars
