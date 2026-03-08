# ruff: noqa: RUF001 E501
"""
User segmentation based on review content.

Segments users into behavioral groups:
- Frustrated (negative sentiment)
- Searchers (looking for an app)
- Advocates (highly positive)
- Switchers (changed from one app to another)
- Price-sensitive (mentions cost/subscription)
- New users (just started)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd


@dataclass
class Segment:
    """A user segment with metadata."""
    key: str
    name_ru: str
    icon: str
    description_ru: str
    keywords: list[str]
    sentiment_range: tuple[float, float] | None = None  # (min, max) or None
    count: int = 0
    users: list[dict] = field(default_factory=list)


SEGMENTS: list[Segment] = [
    Segment(
        key="frustrated",
        name_ru="Разочарованные",
        icon="😤",
        description_ru="Негативный опыт с приложением — потенциальные клиенты",
        keywords=["hate", "terrible", "awful", "horrible", "worst", "useless",
                  "waste", "annoying", "frustrated", "disappointed", "uninstall"],
        sentiment_range=(-1.0, -0.3),
    ),
    Segment(
        key="searchers",
        name_ru="Ищут решение",
        icon="🔍",
        description_ru="Активно ищут приложение прямо сейчас",
        keywords=["best app for", "recommend", "looking for", "any suggestions",
                  "what app", "which app", "alternative to", "similar to"],
        sentiment_range=None,
    ),
    Segment(
        key="advocates",
        name_ru="Адвокаты",
        icon="😊",
        description_ru="Лояльные пользователи — понять что их держит",
        keywords=["love this", "best app", "highly recommend", "amazing app",
                  "game changer", "life changer", "saved my", "perfect app"],
        sentiment_range=(0.5, 1.0),
    ),
    Segment(
        key="switchers",
        name_ru="Переключились",
        icon="🔄",
        description_ru="Ушли от конкурента или переключились",
        keywords=["switched from", "switched to", "moved to", "left",
                  "tried .* then", "used to use", "migrated", "replaced"],
        sentiment_range=None,
    ),
    Segment(
        key="price_sensitive",
        name_ru="Чувствительны к цене",
        icon="💰",
        description_ru="Жалуются на стоимость подписки",
        keywords=["expensive", "overpriced", "subscription", "paywall",
                  "too much money", "not worth", "free version", "cheaper"],
        sentiment_range=None,
    ),
    Segment(
        key="new_users",
        name_ru="Новые пользователи",
        icon="🆕",
        description_ru="Только начали использовать — первые впечатления, онбординг",
        keywords=["just started", "first week", "new to", "just downloaded",
                  "just installed", "trying out", "first time", "beginner"],
        sentiment_range=None,
    ),
]


def segment_users(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Segment a DataFrame of reviews into user groups.

    Args:
        df: DataFrame with columns: text, sentiment_score, author, app_name, etc.

    Returns:
        Dict of segment_key → filtered DataFrame
    """
    results: dict[str, pd.DataFrame] = {}

    for seg in SEGMENTS:
        mask = pd.Series(False, index=df.index)

        # Keyword matching
        if seg.keywords:
            text_col = df["text"].fillna("").str.lower()
            for kw in seg.keywords:
                if ".*" in kw:
                    mask |= text_col.str.contains(kw, regex=True, na=False)
                else:
                    mask |= text_col.str.contains(kw, regex=False, na=False)

        # Sentiment range
        if seg.sentiment_range and "sentiment_score" in df.columns:
            lo, hi = seg.sentiment_range
            sent_mask = (df["sentiment_score"] >= lo) & (df["sentiment_score"] <= hi)
            if seg.keywords:
                mask = mask | sent_mask  # OR: either keyword or sentiment
            else:
                mask = sent_mask

        seg_df = df[mask].copy()
        seg.count = len(seg_df)
        results[seg.key] = seg_df

    return results


def get_segment_summary(df: pd.DataFrame) -> list[dict]:
    """Get a summary of all segments with counts."""
    segmented = segment_users(df)
    summary = []
    for seg in SEGMENTS:
        seg_df = segmented.get(seg.key, pd.DataFrame())
        unique_users = seg_df["author"].nunique() if not seg_df.empty and "author" in seg_df.columns else 0
        summary.append({
            "icon": seg.icon,
            "name": seg.name_ru,
            "description": seg.description_ru,
            "reviews": len(seg_df),
            "users": unique_users,
            "key": seg.key,
        })
    return summary
