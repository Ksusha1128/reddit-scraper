"""Tests for review categorizer."""

from __future__ import annotations

from src.analytics.categorizer import categorize_text
from src.models import ReviewCategory


class TestCategorizer:
    """Test review categorization."""

    def test_pricing_category(self):
        cats = categorize_text("The subscription is too expensive, not worth the price")
        assert ReviewCategory.PRICING in cats

    def test_bugs_category(self):
        cats = categorize_text("The app keeps crashing and has many bugs, sync issues")
        assert ReviewCategory.BUGS in cats

    def test_communication_category(self):
        cats = categorize_text("I love the daily questions and check-in features for communication")
        assert ReviewCategory.COMMUNICATION in cats

    def test_ui_category(self):
        cats = categorize_text("Beautiful design, clean interface, easy to use navigation")
        assert ReviewCategory.UI_UX in cats

    def test_uncategorized(self):
        cats = categorize_text("asdf qwerty nothing meaningful here 12345")
        assert cats == [ReviewCategory.UNCATEGORIZED]

    def test_max_three_categories(self):
        # Text that matches many categories
        text = (
            "Great app with beautiful design, daily questions, "
            "but too expensive subscription and keeps crashing"
        )
        cats = categorize_text(text, max_categories=3)
        assert len(cats) <= 3

    def test_empty_text(self):
        cats = categorize_text("")
        assert cats == [ReviewCategory.UNCATEGORIZED]
