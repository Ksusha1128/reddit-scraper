"""
Pydantic models (schemas) for all domain entities.

Provides strict validation for data entering and leaving the system.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

# ── Enums ────────────────────────────────────────────────────────────────────


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class ReviewSource(str, Enum):
    POST = "post"
    COMMENT = "comment"


class AppNiche(str, Enum):
    """Market niche / vertical for tracked apps."""

    COUPLE = "💑 Couple & Relationships"
    SMOKING = "🚭 Smoking Cessation"
    AI_PSYCHOLOGIST = "🧠 AI Psychologist & Mental Health"
    PLANT_SCANNER = "🌿 AI Plant Scanner"
    CALORIE_TRACKER = "🍎 Calorie & Nutrition Tracker"


class ReviewCategory(str, Enum):
    COMMUNICATION = "💬 Communication"
    INTIMACY = "❤️ Intimacy"
    ACTIVITIES = "🎯 Activities & Games"
    PLANNING = "📅 Planning & Calendar"
    PRICING = "💰 Pricing & Subscription"
    BUGS = "🐛 Bugs & Technical Issues"
    GENERAL = "⭐ General Impression"
    RELATIONSHIP = "👫 Relationship Impact"
    PRIVACY = "🔒 Privacy & Security"
    UI_UX = "📱 UI/UX & Design"
    UNCATEGORIZED = "📝 Uncategorized"


# ── Domain Models ────────────────────────────────────────────────────────────


class AppConfig(BaseModel):
    """Configuration for a single tracked app."""

    name: str
    niche: AppNiche = AppNiche.COUPLE
    search_queries: list[str] = Field(min_length=1)
    aliases: list[str] = Field(min_length=1)


class Review(BaseModel):
    """A single review extracted from Reddit."""

    app_name: str
    source: ReviewSource
    author: str = "[deleted]"
    title: str = ""
    text: str = Field(max_length=5000)
    subreddit: str = ""
    permalink: str = ""
    date: datetime | None = None
    sentiment_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    sentiment_label: SentimentLabel = SentimentLabel.NEUTRAL
    categories: list[ReviewCategory] = Field(default_factory=lambda: [ReviewCategory.UNCATEGORIZED])
    primary_category: ReviewCategory = ReviewCategory.UNCATEGORIZED

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped or stripped in ("[deleted]", "[removed]"):
            raise ValueError("Review text is empty or deleted")
        return stripped


class RSSEntry(BaseModel):
    """A parsed RSS feed entry."""

    title: str = ""
    link: str = ""
    body: str = ""
    author: str = "[deleted]"
    updated: str = ""
    subreddit: str = ""


class ScrapeResult(BaseModel):
    """Summary of a scrape job execution."""

    total_reviews: int = 0
    posts_found: int = 0
    comments_found: int = 0
    duplicates_skipped: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = Field(default_factory=list)


# ── Survey Models ────────────────────────────────────────────────────────────


class SurveyQuestion(BaseModel):
    """A question in a user survey."""

    id: str
    text: str
    question_type: str = "open"  # open | scale | multiple_choice
    options: list[str] | None = None
    required: bool = True


class SurveyResponse(BaseModel):
    """A single survey response from a Reddit user."""

    survey_id: str
    respondent: str
    subreddit: str
    answers: dict[str, str | int | list[str]]
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    source_permalink: str = ""
