"""
Review categorizer — assigns categories to review texts based on keyword matching.

Categories are defined as ReviewCategory enum values in models.py.
"""

from __future__ import annotations

from src.models import ReviewCategory

# ── Category keyword map ─────────────────────────────────────────────────────

CATEGORY_KEYWORDS: dict[ReviewCategory, list[str]] = {
    ReviewCategory.BUGS: [
        "bug", "crash", "glitch", "error", "fix", "broken",
        "not work", "doesn't work", "won't load", "slow",
        "laggy", "freeze", "stuck", "issue", "problem",
        "update broke", "sync issue", "notification bug",
        "force close", "white screen", "black screen",
        "can't open", "won't open", "keeps crashing",
    ],
    ReviewCategory.ENGAGEMENT: [
        "use every day", "daily", "routine", "habit",
        "engagement", "streak", "log", "track", "logging",
        "using it for", "been using", "started using",
        "switched to", "switched from", "tried", "experience",
        "my experience", "how i use", "workflow", "progress",
        "journey", "results", "month", "week", "year",
        "addicted", "hooked", "motivat", "gamif",
    ],
    ReviewCategory.UI_UX: [
        "design", "interface", "ui", "ux", "beautiful",
        "ugly", "clean", "intuitive", "confusing", "easy to use",
        "user friendly", "layout", "theme", "dark mode",
        "navigation", "simple", "complicated", "looks",
        "aesthetic", "color", "font", "icon", "widget",
        "home screen", "dashboard",
    ],
    ReviewCategory.COMMUNICATION: [
        "communicat", "message", "chat", "in-app chat",
        "partner feature", "share with", "send to",
        "notification", "remind", "alert", "push notification",
        "invite", "connect with", "social", "community",
        "forum", "support chat", "customer support",
    ],
    ReviewCategory.FEATURES: [
        "feature", "function", "option", "setting", "tool",
        "integration", "export", "import", "backup",
        "custom", "filter", "sort", "search", "scan",
        "camera", "photo", "barcode", "api", "sync",
        "offline", "cloud", "widget", "shortcut",
        "apple watch", "wearable", "fitbit", "garmin",
    ],
    ReviewCategory.PRICING: [
        "price", "paid", "premium", "subscription", "free",
        "cost", "expensive", "cheap", "money", "worth",
        "paywall", "trial", "purchase", "in-app",
        "pro version", "upgrade", "billing", "refund",
        "cancel", "renewal", "annual", "monthly",
        "lifetime", "discount", "coupon",
    ],
    ReviewCategory.DEVELOPERS: [
        "develop", "developer", "build", "building",
        "coding", "code", "api", "sdk", "open source",
        "github", "contribute", "pull request", "fork",
        "create app", "making app", "my app", "startup",
        "launch", "mvp", "indie", "side project",
        "tech stack", "framework", "flutter", "react native",
        "swift", "kotlin",
    ],
    ReviewCategory.USER_EXPERIENCE: [
        "love this", "hate this", "recommend", "best app",
        "worst app", "amazing", "terrible", "awesome",
        "great app", "bad app", "helpful", "useless",
        "perfect", "disappointed", "satisfied", "enjoy",
        "favorite", "favourite", "uninstall", "delete",
        "download", "install", "overall", "opinion",
        "honest review", "my review", "rating", "stars",
    ],
    ReviewCategory.NEEDS: [
        "need", "want", "wish", "miss", "missing",
        "please add", "should have", "request", "suggest",
        "would be nice", "looking for", "alternative",
        "better than", "compared to", "vs", "versus",
        "complain", "frustrat", "annoy", "disappoint",
        "don't understand", "can't find", "where is",
        "how to", "help me", "anyone know",
    ],
    ReviewCategory.PRIVACY: [
        "privacy", "private", "secure", "security", "data",
        "personal", "hack", "leak", "safe", "account",
        "password", "login", "permission", "tracking",
        "sell data", "gdpr", "encrypt", "two factor",
        "2fa", "breach", "suspicious",
    ],
    ReviewCategory.USER_INTENT: [
        "want to quit", "trying to quit", "going to start",
        "plan to", "thinking about", "considering",
        "should i", "is it worth", "anyone tried",
        "want to lose", "want to gain", "goal",
        "new year", "resolution", "motivation",
        "ready to", "decided to", "committed",
        "want to try", "looking to start", "help me choose",
        "which app", "what app", "best for",
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
        return [ReviewCategory.TOPIC_POST]

    sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [cat for cat, _ in sorted_cats[:max_categories]]
