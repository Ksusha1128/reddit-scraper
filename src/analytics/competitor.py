# ruff: noqa: RUF001 E501
"""
Competitor comparison analysis.

Builds comparison matrices, identifies strengths/weaknesses per app,
and detects switch patterns.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class AppScore:
    """Aggregated metrics for one app."""
    name: str
    niche: str
    total_reviews: int = 0
    avg_sentiment: float = 0.0
    positive_pct: float = 0.0
    negative_pct: float = 0.0
    neutral_pct: float = 0.0
    top_pains: list[str] = field(default_factory=list)
    top_highlights: list[str] = field(default_factory=list)


@dataclass
class SwitchEvent:
    """A detected app switch mention."""
    from_app: str
    to_app: str
    reason: str
    author: str = ""


def build_comparison_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a comparison DataFrame: one row per app with aggregated metrics.
    """
    if df.empty or "app_name" not in df.columns:
        return pd.DataFrame()

    rows = []
    for app, grp in df.groupby("app_name"):
        if app in ("General", "General / Общее"):
            continue
        total = len(grp)
        if total < 2:
            continue

        avg_sent = grp["sentiment_score"].mean() if "sentiment_score" in grp.columns else 0
        pos = (grp["sentiment_label"] == "positive").sum() if "sentiment_label" in grp.columns else 0
        neg = (grp["sentiment_label"] == "negative").sum() if "sentiment_label" in grp.columns else 0
        neu = total - pos - neg
        niche = grp["niche_ru"].iloc[0] if "niche_ru" in grp.columns else ""

        rows.append({
            "Приложение": app,
            "Тематика": niche,
            "Отзывов": total,
            "Ср. тональность": round(avg_sent, 2),
            "😊 Позитив %": round(pos / total * 100, 1),
            "😞 Негатив %": round(neg / total * 100, 1),
            "😐 Нейтрал %": round(neu / total * 100, 1),
        })

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values("Отзывов", ascending=False)
    return result


def detect_switches(texts: list[str], authors: list[str] | None = None) -> list[SwitchEvent]:
    """Detect app-switching patterns in texts."""
    patterns = [
        re.compile(r"switch(?:ed)?\s+from\s+(\w[\w\s]*?)\s+to\s+(\w[\w\s]*?)(?:\s|[.,!?]|$)", re.I),
        re.compile(r"moved?\s+(?:from|away\s+from)\s+(\w[\w\s]*?)\s+to\s+(\w[\w\s]*?)(?:\s|[.,!?]|$)", re.I),
        re.compile(r"(?:left|quit|dropped)\s+(\w[\w\s]*?)\s+(?:for|and\s+(?:use|try|went))\s+(\w[\w\s]*?)(?:\s|[.,!?]|$)", re.I),
        re.compile(r"(\w[\w\s]*?)\s+(?:was|is)\s+(?:bad|terrible|awful).*?(?:now\s+(?:use|using)|switched?\s+to)\s+(\w[\w\s]*?)(?:\s|[.,!?]|$)", re.I),
    ]

    events: list[SwitchEvent] = []
    for i, text in enumerate(texts):
        author = authors[i] if authors and i < len(authors) else ""
        for pat in patterns:
            for m in pat.finditer(text):
                from_app = m.group(1).strip()[:30]
                to_app = m.group(2).strip()[:30]
                reason = text[:200].strip()
                events.append(SwitchEvent(
                    from_app=from_app,
                    to_app=to_app,
                    reason=reason,
                    author=author,
                ))

    return events


def get_strengths_weaknesses(df: pd.DataFrame) -> dict[str, dict[str, list[str]]]:
    """
    For each app, extract top positive and negative phrases.

    Returns:
        {app_name: {"strengths": [...], "weaknesses": [...]}}
    """
    from src.analytics.pain_extractor import PAIN_KEYWORDS

    result: dict[str, dict[str, list[str]]] = {}

    positive_keywords = [
        "love", "amazing", "great", "perfect", "best", "excellent",
        "helpful", "recommend", "easy to use", "beautiful", "intuitive",
        "accurate", "reliable", "fast", "smooth", "clean",
    ]

    for app, grp in df.groupby("app_name"):
        if app in ("General", "General / Общее"):
            continue
        texts = grp["text"].fillna("").tolist()

        # Weaknesses
        weakness_counts: Counter = Counter()
        for text in texts:
            tl = text.lower()
            for cat, kws in PAIN_KEYWORDS.items():
                for kw in kws:
                    if kw in tl:
                        weakness_counts[cat] += 1
                        break

        # Strengths
        strength_counts: Counter = Counter()
        for text in texts:
            tl = text.lower()
            for kw in positive_keywords:
                if kw in tl:
                    strength_counts[kw] += 1

        result[app] = {
            "strengths": [f"{k} ({v})" for k, v in strength_counts.most_common(5)],
            "weaknesses": [f"{k} ({v})" for k, v in weakness_counts.most_common(5)],
        }

    return result
