"""Tests for review models validation."""

from __future__ import annotations

import pytest

from src.models import (
    AppConfig,
    Review,
    ReviewCategory,
    ReviewSource,
    RSSEntry,
    SentimentLabel,
    SurveyQuestion,
)


class TestReviewModel:
    """Test Review model validation."""

    def test_valid_review(self):
        review = Review(
            app_name="Couple Joy",
            source=ReviewSource.POST,
            author="testuser",
            title="Great app!",
            text="This is a review of the couple joy app that I love",
            subreddit="relationships",
            permalink="https://reddit.com/r/relationships/comments/abc",
            sentiment_score=0.5,
            sentiment_label=SentimentLabel.POSITIVE,
        )
        assert review.app_name == "Couple Joy"
        assert review.source == ReviewSource.POST

    def test_empty_text_rejected(self):
        with pytest.raises(ValueError, match="empty or deleted"):
            Review(
                app_name="Test",
                source=ReviewSource.POST,
                text="",
            )

    def test_deleted_text_rejected(self):
        with pytest.raises(ValueError, match="empty or deleted"):
            Review(
                app_name="Test",
                source=ReviewSource.POST,
                text="[deleted]",
            )

    def test_removed_text_rejected(self):
        with pytest.raises(ValueError, match="empty or deleted"):
            Review(
                app_name="Test",
                source=ReviewSource.POST,
                text="[removed]",
            )

    def test_text_stripped(self):
        review = Review(
            app_name="Test",
            source=ReviewSource.COMMENT,
            text="  some review text with spaces  ",
        )
        assert review.text == "some review text with spaces"

    def test_text_max_length(self):
        long_text = "a" * 6000
        with pytest.raises(ValueError):
            Review(
                app_name="Test",
                source=ReviewSource.POST,
                text=long_text,
            )

    def test_sentiment_score_bounds(self):
        with pytest.raises(ValueError):
            Review(
                app_name="Test",
                source=ReviewSource.POST,
                text="Some text here",
                sentiment_score=1.5,  # Out of range
            )

    def test_default_category(self):
        review = Review(
            app_name="Test",
            source=ReviewSource.POST,
            text="Just a normal review",
        )
        assert review.primary_category == ReviewCategory.UNCATEGORIZED


class TestAppConfig:
    """Test AppConfig validation."""

    def test_valid_app(self):
        app = AppConfig(
            name="Test App",
            search_queries=["test app"],
            aliases=["test"],
        )
        assert app.name == "Test App"

    def test_empty_queries_rejected(self):
        with pytest.raises(ValueError):
            AppConfig(
                name="Test",
                search_queries=[],
                aliases=["test"],
            )

    def test_empty_aliases_rejected(self):
        with pytest.raises(ValueError):
            AppConfig(
                name="Test",
                search_queries=["test"],
                aliases=[],
            )


class TestRSSEntry:
    """Test RSSEntry model."""

    def test_defaults(self):
        entry = RSSEntry()
        assert entry.author == "[deleted]"
        assert entry.title == ""
        assert entry.body == ""


class TestSurveyQuestion:
    """Test SurveyQuestion model."""

    def test_open_question(self):
        q = SurveyQuestion(
            id="q1",
            text="What do you think?",
            question_type="open",
        )
        assert q.required is True

    def test_scale_question(self):
        q = SurveyQuestion(
            id="q2",
            text="Rate 1-10",
            question_type="scale",
            options=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
        )
        assert len(q.options) == 10
