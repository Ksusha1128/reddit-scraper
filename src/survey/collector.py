"""
Survey response collector — scrapes Reddit for survey answers.

Monitors specific posts/threads for structured survey responses
from English-speaking Reddit users.
"""

from __future__ import annotations

import re
from datetime import datetime

from src.logging import get_logger
from src.models import RSSEntry, SurveyQuestion, SurveyResponse
from src.scraper.http_client import RedditClient
from src.scraper.rss_parser import parse_rss_feed
from src.survey.templates import COUPLE_APP_SURVEY

logger = get_logger(__name__)


class SurveyCollector:
    """
    Collects and parses survey responses from Reddit comments.

    Usage:
        collector = SurveyCollector()
        responses = await collector.collect_from_post(
            post_url="https://www.reddit.com/r/relationships/comments/abc123/survey/",
            survey_id="couple_app_v1",
        )
    """

    def __init__(
        self,
        client: RedditClient | None = None,
        questions: list[SurveyQuestion] | None = None,
    ) -> None:
        self._client = client or RedditClient()
        self._questions = questions or COUPLE_APP_SURVEY

    async def collect_from_post(
        self,
        post_url: str,
        survey_id: str = "default",
    ) -> list[SurveyResponse]:
        """
        Fetch comments from a survey post and parse structured answers.

        Args:
            post_url: Full URL to the Reddit post containing the survey.
            survey_id: Identifier for this survey run.

        Returns:
            List of parsed SurveyResponse objects.
        """
        rss_url = post_url.rstrip("/").split("?")[0] + ".rss"
        content = await self._client.get_rss(rss_url, params={"limit": 500})

        if not content:
            logger.warning("survey_fetch_failed", post_url=post_url)
            return []

        entries = parse_rss_feed(content)
        responses: list[SurveyResponse] = []

        for i, entry in enumerate(entries):
            if i == 0:
                continue  # Skip the post itself

            parsed = self._parse_response(entry, survey_id)
            if parsed:
                responses.append(parsed)

        logger.info(
            "survey_collected",
            post_url=post_url,
            total_comments=len(entries) - 1,
            parsed_responses=len(responses),
        )
        return responses

    def _parse_response(self, entry: RSSEntry, survey_id: str) -> SurveyResponse | None:
        """
        Try to parse a comment as a survey response.

        Looks for numbered answers (1. answer, 2. answer, etc.)
        or question-keyword matches.
        """
        text = entry.body.strip()
        if len(text) < 20:
            return None

        answers: dict[str, str | int | list[str]] = {}

        # Strategy 1: numbered answers (1. ..., 2. ..., etc.)
        numbered = re.findall(r"(?:^|\n)\s*(\d+)[.)]\s*(.+?)(?=\n\s*\d+[.)]|\Z)", text, re.DOTALL)

        if numbered:
            for num_str, answer_text in numbered:
                idx = int(num_str) - 1
                if 0 <= idx < len(self._questions):
                    q = self._questions[idx]
                    answers[q.id] = answer_text.strip()

        # Strategy 2: if no numbered answers, use the whole text as q1 answer
        if not answers and len(text) > 30:
            answers[self._questions[0].id] = text[:2000]

        if not answers:
            return None

        try:
            return SurveyResponse(
                survey_id=survey_id,
                respondent=entry.author,
                subreddit=entry.subreddit,
                answers=answers,
                submitted_at=datetime.utcnow(),
                source_permalink=entry.link,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("survey_parse_error", error=str(exc))
            return None

    async def export_responses(
        self,
        responses: list[SurveyResponse],
        output_path: str = "surveys/responses.csv",
    ) -> None:
        """Export survey responses to CSV."""
        from pathlib import Path

        import pandas as pd

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        rows = []
        for r in responses:
            row = {
                "survey_id": r.survey_id,
                "respondent": r.respondent,
                "subreddit": r.subreddit,
                "submitted_at": r.submitted_at.isoformat(),
                "source_permalink": r.source_permalink,
            }
            # Flatten answers
            for key, value in r.answers.items():
                if isinstance(value, list):
                    row[key] = "; ".join(str(v) for v in value)
                else:
                    row[key] = value
            rows.append(row)

        pd.DataFrame(rows).to_csv(output_path, index=False, encoding="utf-8-sig")
        logger.info("survey_exported", path=output_path, responses=len(rows))
