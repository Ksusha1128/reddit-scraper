"""
Survey templates for Reddit user research.

Define your survey questions here. The survey engine will format them
as Reddit comments/messages for English-speaking users.
"""

from __future__ import annotations

from src.models import SurveyQuestion

# ── Default couple-app survey ────────────────────────────────────────────────

COUPLE_APP_SURVEY: list[SurveyQuestion] = [
    SurveyQuestion(
        id="q1_current_app",
        text="Which couple/relationship app(s) are you currently using or have used?",
        question_type="open",
        required=True,
    ),
    SurveyQuestion(
        id="q2_satisfaction",
        text="On a scale of 1-10, how satisfied are you with your current couple app?",
        question_type="scale",
        options=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
        required=True,
    ),
    SurveyQuestion(
        id="q3_best_feature",
        text="What's the ONE feature you love the most?",
        question_type="open",
        required=True,
    ),
    SurveyQuestion(
        id="q4_worst_pain",
        text="What's the biggest pain point or missing feature?",
        question_type="open",
        required=True,
    ),
    SurveyQuestion(
        id="q5_categories",
        text="Which features are most important to you?",
        question_type="multiple_choice",
        options=[
            "Daily questions & check-ins",
            "Date night ideas",
            "Communication tools",
            "Shared calendar & planning",
            "Quizzes & games",
            "Love language tracking",
            "Memory/photo sharing",
            "Intimacy & relationship growth",
        ],
        required=True,
    ),
    SurveyQuestion(
        id="q6_pricing",
        text="How much would you pay monthly for a couple app? (in USD)",
        question_type="multiple_choice",
        options=["Free only", "$1-3", "$4-6", "$7-10", "$10+"],
        required=True,
    ),
    SurveyQuestion(
        id="q7_switch",
        text="What would make you switch to a new couple app?",
        question_type="open",
        required=False,
    ),
    SurveyQuestion(
        id="q8_recommendation",
        text="Would you recommend your current app to friends? Why or why not?",
        question_type="open",
        required=False,
    ),
]


def format_survey_as_reddit_comment(
    questions: list[SurveyQuestion] | None = None,
    intro: str | None = None,
) -> str:
    """
    Format survey questions as a Reddit comment/post body.

    Returns:
        Markdown-formatted string ready to post on Reddit.
    """
    if questions is None:
        questions = COUPLE_APP_SURVEY

    if intro is None:
        intro = (
            "👋 **Quick Survey — Help us build a better couple app!**\n\n"
            "We're researching what couples actually want in a relationship app. "
            "Your answers are anonymous and will help improve the experience for everyone. "
            "Feel free to skip any question you don't want to answer.\n\n"
            "---\n"
        )

    lines = [intro]

    for i, q in enumerate(questions, 1):
        required = " *(required)*" if q.required else " *(optional)*"
        lines.append(f"**{i}. {q.text}**{required}\n")

        if q.question_type == "scale" and q.options:
            lines.append(f"   Scale: {q.options[0]} — {q.options[-1]}\n")
        elif q.question_type == "multiple_choice" and q.options:
            for opt in q.options:
                lines.append(f"   - [ ] {opt}")
            lines.append("")

        lines.append("")

    lines.append("---\n")
    lines.append("*Thank you for your time! 🙏 Reply below or DM us.*\n")

    return "\n".join(lines)


def format_survey_as_json_schema(
    questions: list[SurveyQuestion] | None = None,
) -> dict:
    """
    Generate a JSON schema for survey responses (useful for API validation).
    """
    if questions is None:
        questions = COUPLE_APP_SURVEY

    properties: dict = {}
    required: list[str] = []

    for q in questions:
        prop: dict = {"title": q.text}

        if q.question_type == "scale" and q.options:
            prop["type"] = "integer"
            prop["minimum"] = int(q.options[0])
            prop["maximum"] = int(q.options[-1])
        elif q.question_type == "multiple_choice":
            prop["type"] = "array"
            prop["items"] = {"type": "string", "enum": q.options or []}
        else:
            prop["type"] = "string"

        properties[q.id] = prop
        if q.required:
            required.append(q.id)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }
