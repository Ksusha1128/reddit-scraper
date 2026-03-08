"""
Sentiment analysis for review texts.

Uses VADER when available, falls back to a simple keyword-based approach.
"""

from __future__ import annotations

import re

from src.logging import get_logger
from src.models import SentimentLabel

logger = get_logger(__name__)

# Try to use VADER for better accuracy
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer as _Vader

    _analyzer = _Vader()
    _USE_VADER = True
    logger.info("sentiment_engine", engine="VADER")
except ImportError:
    _analyzer = None
    _USE_VADER = False
    logger.info("sentiment_engine", engine="keyword_fallback")


# ── Keyword fallback sets ────────────────────────────────────────────────────

_POSITIVE = frozenset({
    "good", "great", "awesome", "excellent", "amazing", "love", "best", "perfect",
    "nice", "wonderful", "fantastic", "brilliant", "superb", "outstanding", "happy",
    "beautiful", "helpful", "thanks", "thank", "appreciate", "recommend", "interesting",
    "useful", "cool", "fun", "enjoy", "like", "loved", "impressive", "incredible",
})

_NEGATIVE = frozenset({
    "bad", "terrible", "awful", "horrible", "hate", "worst", "poor", "disappointing",
    "useless", "waste", "annoying", "boring", "ugly", "stupid", "dumb", "fail",
    "wrong", "broken", "sad", "angry", "frustrated", "scam", "fake", "trash",
    "pathetic", "ridiculous", "disgusting", "overpriced", "avoid", "never",
})

_INTENSIFIERS = frozenset({"very", "really", "extremely", "absolutely", "totally", "completely"})


def analyze_sentiment(text: str) -> tuple[float, SentimentLabel]:
    """
    Analyse sentiment of a text.

    Returns:
        (score, label) where score is in [-1.0, 1.0].
    """
    if not text or not text.strip():
        return 0.0, SentimentLabel.NEUTRAL

    if _USE_VADER and _analyzer is not None:
        return _vader_sentiment(text)
    return _keyword_sentiment(text)


def _vader_sentiment(text: str) -> tuple[float, SentimentLabel]:
    """VADER-based sentiment analysis."""
    scores = _analyzer.polarity_scores(text)  # type: ignore[union-attr]
    compound = scores["compound"]

    if compound >= 0.05:
        return round(compound, 3), SentimentLabel.POSITIVE
    if compound <= -0.05:
        return round(compound, 3), SentimentLabel.NEGATIVE
    return round(compound, 3), SentimentLabel.NEUTRAL


def _keyword_sentiment(text: str) -> tuple[float, SentimentLabel]:
    """Simple keyword-based fallback."""
    words = re.findall(r"\b[a-z]+\b", text.lower())
    if not words:
        return 0.0, SentimentLabel.NEUTRAL

    pos = 0.0
    neg = 0.0
    intensifier_next = False

    for word in words:
        multiplier = 1.5 if intensifier_next else 1.0
        if word in _POSITIVE:
            pos += multiplier
        elif word in _NEGATIVE:
            neg += multiplier
        intensifier_next = word in _INTENSIFIERS

    total = pos + neg
    if total == 0:
        return 0.0, SentimentLabel.NEUTRAL

    score = round((pos - neg) / total, 3)
    if score > 0.1:
        return score, SentimentLabel.POSITIVE
    if score < -0.1:
        return score, SentimentLabel.NEGATIVE
    return score, SentimentLabel.NEUTRAL
