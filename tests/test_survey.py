"""Tests for survey templates."""

from __future__ import annotations

from src.survey.templates import (
    COUPLE_APP_SURVEY,
    format_survey_as_json_schema,
    format_survey_as_reddit_comment,
)


class TestSurveyTemplate:
    def test_default_survey_has_questions(self):
        assert len(COUPLE_APP_SURVEY) > 0

    def test_all_questions_have_ids(self):
        ids = [q.id for q in COUPLE_APP_SURVEY]
        assert len(ids) == len(set(ids)), "Duplicate question IDs found"

    def test_format_as_markdown(self):
        text = format_survey_as_reddit_comment()
        assert "**1." in text
        assert "Quick Survey" in text
        assert "Thank you" in text

    def test_format_includes_all_questions(self):
        text = format_survey_as_reddit_comment()
        for i, _q in enumerate(COUPLE_APP_SURVEY, 1):
            assert f"**{i}." in text

    def test_json_schema_structure(self):
        schema = format_survey_as_json_schema()
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert len(schema["properties"]) == len(COUPLE_APP_SURVEY)

    def test_json_schema_required_fields(self):
        schema = format_survey_as_json_schema()
        required_qs = [q.id for q in COUPLE_APP_SURVEY if q.required]
        assert set(schema["required"]) == set(required_qs)
