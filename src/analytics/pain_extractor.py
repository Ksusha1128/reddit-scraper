# ruff: noqa: RUF001 E501
"""
Pain & feature-request extractor from review texts.

Extracts:
- User pains/frustrations (negative patterns)
- Feature requests ("I wish...", "need...", "should add...")
- Positive highlights (what users love)
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class PainItem:
    """A single extracted pain/feature/highlight."""
    text: str
    count: int = 1
    examples: list[str] = field(default_factory=list)
    apps: list[str] = field(default_factory=list)


# ── Pain extraction patterns ────────────────────────────────────────────────

_PAIN_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(?:hate|hated|hating)\s+(?:that|how|when|the)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\b(?:frustrat(?:ed|ing)|annoy(?:ed|ing)|disappoint(?:ed|ing))\s+(?:by|with|that|about)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\bthe (?:worst|biggest) (?:thing|part|issue|problem)\s+(?:is|was|about)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\b(?:can(?:'?t| not)|couldn(?:'?t| not))\s+(?:even\s+)?(.{10,60}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\b(?:doesn(?:'?t| not)|didn(?:'?t| not)|won(?:'?t| not))\s+(?:even\s+)?(.{5,60}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\b(?:broken|buggy|glitch(?:y|es)?|crash(?:es|ed|ing)?|lag(?:gy|s)?)\b.{0,40}?(.{10,60}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\b(?:too\s+(?:expensive|slow|complicated|confusing|buggy))\b", re.I),
    re.compile(r"\b(?:waste\s+of\s+(?:money|time))\b", re.I),
    re.compile(r"\b(?:not\s+worth)\s+(.{5,50}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\b(?:overpriced|paywall|rip\s*off|scam(?:my)?)\b", re.I),
    re.compile(r"\b(?:subscription|premium)\s+(?:is\s+)?(?:too\s+)?(?:expensive|costly|overpriced|ridiculous)\b", re.I),
    re.compile(r"\buninstall(?:ed)?\b", re.I),
    re.compile(r"\bswitched?\s+(?:to|from|away)\b", re.I),
]

_FEATURE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bi\s+wish\s+(?:it\s+)?(?:had|could|would|there\s+was)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\bwould\s+(?:be\s+)?(?:nice|great|cool|awesome)\s+(?:if|to\s+have)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\b(?:they|it)\s+should\s+(?:add|have|include|support)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\bneed(?:s)?\s+(?:a|an|to\s+add|to\s+have|more)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\bplease\s+add\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\bif\s+(?:only|it)\s+(?:had|could|would)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\blacking\s+(.{5,60}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\bmissing\s+(.{5,60}?)(?:[.\n!?]|$)", re.I),
]

_POSITIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\blove\s+(?:that|how|the|this)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\b(?:the\s+)?best\s+(?:thing|part|feature)\s+(?:is|about)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\breally\s+(?:like|enjoy|appreciate)\s+(.{10,80}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\b(?:amazing|awesome|excellent|fantastic|great|perfect)\s+(.{5,60}?)(?:[.\n!?]|$)", re.I),
    re.compile(r"\bhighly\s+recommend\b", re.I),
    re.compile(r"\b(?:game|life)\s*changer\b", re.I),
    re.compile(r"\bsaved\s+(?:my|our)\s+(.{5,50}?)(?:[.\n!?]|$)", re.I),
]

# ── Keyword-based pain categories ────────────────────────────────────────────

PAIN_KEYWORDS: dict[str, list[str]] = {
    "💰 Цена / подписка": [
        "expensive", "overpriced", "subscription", "paywall", "rip off",
        "not worth the price", "too costly", "free version useless",
        "raised prices", "premium only", "in-app purchase",
    ],
    "🐛 Баги / технические проблемы": [
        "crash", "bug", "glitch", "freeze", "lag", "slow",
        "not loading", "sync issue", "broken", "error",
        "doesn't work", "won't open", "update broke",
    ],
    "😤 Плохой UX / дизайн": [
        "confusing", "complicated", "ugly", "hard to use",
        "bad interface", "unintuitive", "cluttered", "navigation",
        "too many steps", "not user friendly",
    ],
    "📉 Неточность / качество данных": [
        "inaccurate", "wrong data", "incorrect", "not accurate",
        "bad database", "missing food", "wrong calories",
        "misidentif", "wrong plant", "false positive",
    ],
    "🔒 Приватность / безопасность": [
        "privacy", "data collection", "tracking", "permissions",
        "suspicious", "account hacked", "personal data",
    ],
    "📵 Проблемы с уведомлениями": [
        "notification", "too many notifications", "spam",
        "no notifications", "alert",
    ],
    "🔄 Переход с конкурента": [
        "switched from", "moved to", "left", "uninstalled",
        "looking for alternative", "better option",
    ],
    "😔 Не хватает функций": [
        "missing feature", "no support for", "doesn't have",
        "wish it had", "would be nice", "need more",
    ],
}


def extract_pains(texts: list[str], app_names: list[str] | None = None) -> list[PainItem]:
    """Extract pain points from review texts using patterns + keywords."""
    category_counts: dict[str, Counter] = {}
    category_examples: dict[str, list[str]] = {}
    category_apps: dict[str, Counter] = {}

    for i, text in enumerate(texts):
        text_lower = text.lower()
        app = app_names[i] if app_names and i < len(app_names) else "Unknown"

        for cat, keywords in PAIN_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    if cat not in category_counts:
                        category_counts[cat] = Counter()
                        category_examples[cat] = []
                        category_apps[cat] = Counter()
                    category_counts[cat][kw] += 1
                    if len(category_examples[cat]) < 5:
                        snippet = text[:200].strip()
                        if snippet not in category_examples[cat]:
                            category_examples[cat].append(snippet)
                    category_apps[cat][app] += 1
                    break  # One category match per text per category

    results = []
    for cat in sorted(category_counts, key=lambda c: sum(category_counts[c].values()), reverse=True):
        total = sum(category_counts[cat].values())
        results.append(PainItem(
            text=cat,
            count=total,
            examples=category_examples.get(cat, []),
            apps=[f"{app} ({cnt})" for app, cnt in category_apps[cat].most_common(5)],
        ))
    return results


def extract_feature_requests(texts: list[str], app_names: list[str] | None = None) -> list[PainItem]:
    """Extract feature requests from texts."""
    found: Counter = Counter()
    examples: dict[str, list[str]] = {}
    apps: dict[str, Counter] = {}

    for i, text in enumerate(texts):
        app = app_names[i] if app_names and i < len(app_names) else "Unknown"
        for pat in _FEATURE_PATTERNS:
            for m in pat.finditer(text):
                key = m.group(0).strip()[:100].lower()
                key = re.sub(r"\s+", " ", key)
                found[key] += 1
                if key not in examples:
                    examples[key] = []
                    apps[key] = Counter()
                if len(examples[key]) < 3:
                    examples[key].append(text[:200].strip())
                apps[key][app] += 1

    results = []
    for phrase, cnt in found.most_common(30):
        results.append(PainItem(
            text=phrase,
            count=cnt,
            examples=examples.get(phrase, []),
            apps=[f"{a} ({c})" for a, c in apps[phrase].most_common(3)],
        ))
    return results


def extract_highlights(texts: list[str], app_names: list[str] | None = None) -> list[PainItem]:
    """Extract positive highlights from texts."""
    found: Counter = Counter()
    examples: dict[str, list[str]] = {}
    apps: dict[str, Counter] = {}

    for i, text in enumerate(texts):
        app = app_names[i] if app_names and i < len(app_names) else "Unknown"
        for pat in _POSITIVE_PATTERNS:
            for m in pat.finditer(text):
                key = m.group(0).strip()[:100].lower()
                key = re.sub(r"\s+", " ", key)
                found[key] += 1
                if key not in examples:
                    examples[key] = []
                    apps[key] = Counter()
                if len(examples[key]) < 3:
                    examples[key].append(text[:200].strip())
                apps[key][app] += 1

    results = []
    for phrase, cnt in found.most_common(30):
        results.append(PainItem(
            text=phrase,
            count=cnt,
            examples=examples.get(phrase, []),
            apps=[f"{a} ({c})" for a, c in apps[phrase].most_common(3)],
        ))
    return results
