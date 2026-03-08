"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_review_text() -> str:
    return (
        "I've been using Couple Joy for 3 months now. "
        "The daily questions are great for communication, "
        "but the subscription is too expensive at $10/month. "
        "The app crashes sometimes when loading quizzes."
    )


@pytest.fixture
def sample_rss_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Best couple app?</title>
    <link href="https://www.reddit.com/r/relationships/comments/test123/best_couple_app/"/>
    <content type="html">&lt;p&gt;Anyone tried Couple Joy?&lt;/p&gt;</content>
    <author><name>/u/test_author</name></author>
    <updated>2024-06-15T10:30:00Z</updated>
    <category term="relationships"/>
  </entry>
</feed>"""
