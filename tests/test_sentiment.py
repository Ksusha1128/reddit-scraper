"""Tests for sentiment analysis."""

from __future__ import annotations

from src.analytics.sentiment import analyze_sentiment
from src.models import SentimentLabel


class TestSentiment:
    """Test sentiment analysis functions."""

    def test_positive_text(self):
        score, label = analyze_sentiment("This app is amazing, I love it so much!")
        assert label == SentimentLabel.POSITIVE
        assert score > 0

    def test_negative_text(self):
        score, label = analyze_sentiment("Terrible app, waste of money, horrible experience")
        assert label == SentimentLabel.NEGATIVE
        assert score < 0

    def test_neutral_text(self):
        _score, label = analyze_sentiment("The app has a calendar feature")
        assert label == SentimentLabel.NEUTRAL

    def test_empty_text(self):
        score, label = analyze_sentiment("")
        assert label == SentimentLabel.NEUTRAL
        assert score == 0.0

    def test_none_text(self):
        score, _label = analyze_sentiment("")
        assert score == 0.0

    def test_score_range(self):
        score, _ = analyze_sentiment("really great excellent perfect")
        assert -1.0 <= score <= 1.0
