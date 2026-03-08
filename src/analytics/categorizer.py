"""
Review categorizer — assigns categories to review texts based on keyword matching.

Categories are defined as ReviewCategory enum values in models.py.
"""

from __future__ import annotations

from src.models import ReviewCategory

# ── Category keyword map ─────────────────────────────────────────────────────

CATEGORY_KEYWORDS: dict[ReviewCategory, list[str]] = {
    ReviewCategory.COMMUNICATION: [
        "communicat", "talk", "message", "chat", "conversation",
        "discuss", "listen", "express", "voice", "call",
        "share feelings", "open up", "daily question",
        "check-in", "check in", "connect",
    ],
    ReviewCategory.INTIMACY: [
        "intima", "physical", "touch", "affection",
        "love language", "romance", "romantic", "passion",
        "desire", "cuddle", "intimacy",
    ],
    ReviewCategory.ACTIVITIES: [
        "quiz", "game", "challenge", "question", "activity",
        "date idea", "date night", "fun", "play", "trivia",
        "bucket list", "adventure", "dare", "card",
        "icebreaker", "would you rather",
    ],
    ReviewCategory.PLANNING: [
        "calendar", "plan", "schedule", "remind", "anniversary",
        "birthday", "event", "countdown", "milestone",
        "memory", "memories", "timeline", "special day",
    ],
    ReviewCategory.PRICING: [
        "price", "paid", "premium", "subscription", "free",
        "cost", "expensive", "cheap", "money", "worth",
        "paywall", "trial", "purchase", "in-app",
        "pro version", "upgrade", "billing", "refund",
    ],
    ReviewCategory.BUGS: [
        "bug", "crash", "glitch", "error", "fix", "broken",
        "not work", "doesn't work", "won't load", "slow",
        "laggy", "freeze", "stuck", "issue", "problem",
        "update", "sync", "notification",
    ],
    ReviewCategory.GENERAL: [
        "love this", "hate this", "recommend", "best app",
        "worst app", "amazing", "terrible", "awesome",
        "great app", "bad app", "helpful", "useless",
        "perfect", "disappointed", "satisfied", "enjoy",
        "favorite", "favourite", "uninstall", "delete",
        "download", "install", "review", "overall",
    ],
    ReviewCategory.RELATIONSHIP: [
        "relationship", "partner", "boyfriend", "girlfriend",
        "husband", "wife", "spouse", "couple", "together",
        "closer", "bond", "trust", "understand",
        "improve", "better", "helped", "saved", "strengthen",
        "grow", "growth", "heal", "therapy",
    ],
    ReviewCategory.PRIVACY: [
        "privacy", "private", "secure", "security", "data",
        "personal", "hack", "leak", "safe", "account",
        "password", "login", "permission",
    ],
    ReviewCategory.UI_UX: [
        "design", "interface", "ui", "ux", "beautiful",
        "ugly", "clean", "intuitive", "confusing", "easy to use",
        "user friendly", "layout", "theme", "dark mode",
        "navigation", "simple", "complicated",
    ],
}


def categorize_text(text: str, max_categories: int = 3) -> list[ReviewCategory]:
    """
    Assign up to ``max_categories`` to a review text.

    Scores each category by counting keyword matches.
    Returns the top categories sorted by score, or [UNCATEGORIZED].
    """
    text_lower = text.lower()
    scores: dict[ReviewCategory, int] = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score

    if not scores:
        return [ReviewCategory.UNCATEGORIZED]

    sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [cat for cat, _ in sorted_cats[:max_categories]]
