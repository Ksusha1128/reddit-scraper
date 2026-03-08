"""
CLI entry point — uses Typer for clean, typed argument parsing.

All commands are grouped logically:
  - scrape:   collect reviews from Reddit
  - survey:   generate and collect user surveys
  - export:   export data to various formats
  - apps:     manage tracked apps list
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from src.config import settings
from src.logging import setup_logging

app = typer.Typer(
    name="couple-scraper",
    help="🤖 Reddit Couple Apps Review Scraper & Survey Tool",
    add_completion=False,
    no_args_is_help=True,
)


# ── Scrape commands ──────────────────────────────────────────────────────────


@app.command()
def scrape(
    apps: list[str] | None = typer.Option(
        None, "--app", "-a", help="App name(s) to scrape (default: all)"
    ),
    limit: int = typer.Option(25, "--limit", "-l", help="Max posts per search query"),
    output: str = typer.Option("reviews", "--output", "-o", help="Output directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Scrape Reddit for couple app reviews."""
    setup_logging("DEBUG" if verbose else settings.log_level)

    from src.export.reports import ReviewExporter
    from src.scraper.review_scraper import ReviewScraper

    async def _run() -> None:
        scraper = ReviewScraper()
        try:
            result = await scraper.run(target_apps=apps, limit_per_query=limit)

            typer.echo(f"\n{'═' * 60}")
            typer.echo("📊 SCRAPE RESULTS")
            typer.echo(f"{'═' * 60}")
            typer.echo(f"  📝 Total reviews:  {result.total_reviews}")
            typer.echo(f"  📄 From posts:     {result.posts_found}")
            typer.echo(f"  💬 From comments:  {result.comments_found}")
            typer.echo(f"  🔄 Duplicates:     {result.duplicates_skipped}")
            typer.echo(f"  ⏱️  Duration:       {result.duration_seconds}s")

            if result.errors:
                typer.echo(f"  ⚠️  Errors:        {len(result.errors)}")

            if scraper.reviews:
                exporter = ReviewExporter(scraper.reviews, output_dir=output)
                paths = exporter.export_all()
                typer.echo(f"\n  💾 Exported {len(paths)} files to {output}/")
            else:
                typer.echo("\n  ⚠️  No reviews found.")

        finally:
            await scraper._client.close()

    asyncio.run(_run())


# ── Survey commands ──────────────────────────────────────────────────────────


@app.command()
def survey_generate(
    output: str = typer.Option("survey_post.md", "--output", "-o", help="Output file"),
) -> None:
    """Generate a survey post template (Markdown) to post on Reddit."""
    setup_logging(settings.log_level)

    from src.survey.templates import format_survey_as_reddit_comment

    text = format_survey_as_reddit_comment()
    Path(output).write_text(text, encoding="utf-8")
    typer.echo(f"✅ Survey template saved to {output}")
    typer.echo("   Copy-paste it as a Reddit post in relevant subreddits.")


@app.command()
def survey_collect(
    post_url: str = typer.Argument(..., help="Reddit post URL containing the survey"),
    survey_id: str = typer.Option("couple_app_v1", "--id", help="Survey identifier"),
    output: str = typer.Option("surveys/responses.csv", "--output", "-o", help="Output CSV"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Collect survey responses from a Reddit post's comments."""
    setup_logging("DEBUG" if verbose else settings.log_level)

    from src.survey.collector import SurveyCollector

    async def _run() -> None:
        collector = SurveyCollector()
        try:
            responses = await collector.collect_from_post(post_url, survey_id)

            typer.echo(f"\n📋 Collected {len(responses)} survey responses")

            if responses:
                await collector.export_responses(responses, output)
                typer.echo(f"💾 Saved to {output}")
            else:
                typer.echo("⚠️  No parseable responses found.")
        finally:
            await collector._client.close()

    asyncio.run(_run())


# ── App management ───────────────────────────────────────────────────────────


@app.command()
def list_apps() -> None:
    """Show all tracked apps grouped by niche."""
    from src.apps import TRACKED_APPS
    from src.models import AppNiche

    typer.echo("\n📱 Tracked Apps:")
    for niche in AppNiche:
        niche_apps = [a for a in TRACKED_APPS if a.niche == niche]
        if not niche_apps:
            continue
        typer.echo(f"\n  {niche.value}")
        typer.echo("  " + "─" * 40)
        for app_cfg in niche_apps:
            typer.echo(f"    • {app_cfg.name}")
    typer.echo()


@app.command()
def list_categories() -> None:
    """Show all review categories."""
    from src.analytics.categorizer import CATEGORY_KEYWORDS

    typer.echo("\n📂 Review Categories:")
    typer.echo("─" * 45)
    for cat, keywords in CATEGORY_KEYWORDS.items():
        typer.echo(f"  {cat.value}")
        kws = ", ".join(keywords[:5])
        typer.echo(f"    Keywords: {kws}...")
    typer.echo()


# ── Entry point ──────────────────────────────────────────────────────────────


def main() -> None:
    app()


if __name__ == "__main__":
    main()
