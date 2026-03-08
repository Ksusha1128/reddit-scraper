"""
Export scraped reviews to CSV, JSON, and Markdown reports.

This replaces the tangled save logic that was mixed into the scraper.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.logging import get_logger
from src.models import Review

logger = get_logger(__name__)


class ReviewExporter:
    """
    Exports a list of Review models to various formats.

    Usage:
        exporter = ReviewExporter(reviews, output_dir="reviews")
        exporter.export_all()
    """

    def __init__(self, reviews: list[Review], output_dir: str = "reviews") -> None:
        self._reviews = reviews
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(self) -> dict[str, Path]:
        """Run all export formats. Returns mapping of format → file path."""
        if not self._reviews:
            logger.warning("no_reviews_to_export")
            return {}

        df = self._to_dataframe()
        paths: dict[str, Path] = {}

        paths["all_reviews"] = self._export_csv(df)
        paths.update(self._export_by_app(df))
        paths["by_category"] = self._export_by_category(df)
        paths["text_only"] = self._export_text_only(df)
        paths["stats"] = self._export_stats_json(df)
        paths["report"] = self._export_markdown_report(df)

        logger.info(
            "export_complete",
            files=len(paths),
            total_reviews=len(df),
        )
        return paths

    def _to_dataframe(self) -> pd.DataFrame:
        """Convert Review models to a DataFrame."""
        records = []
        for r in self._reviews:
            records.append({
                "app_name": r.app_name,
                "source": r.source.value,
                "author": r.author,
                "title": r.title,
                "text": r.text,
                "subreddit": r.subreddit,
                "permalink": r.permalink,
                "date": r.date.isoformat() if r.date else "",
                "sentiment_score": r.sentiment_score,
                "sentiment_label": r.sentiment_label.value,
                "categories": " | ".join(c.value for c in r.categories),
                "primary_category": r.primary_category.value,
            })
        return pd.DataFrame(records)

    def _export_csv(self, df: pd.DataFrame) -> Path:
        path = self._output_dir / "all_reviews.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig")
        logger.info("exported", file=str(path), rows=len(df))
        return path

    def _export_by_app(self, df: pd.DataFrame) -> dict[str, Path]:
        paths: dict[str, Path] = {}
        for app_name in df["app_name"].unique():
            app_df = df[df["app_name"] == app_name]
            safe_name = re.sub(r"[^\w\-]", "_", app_name)
            path = self._output_dir / f"reviews_{safe_name}.csv"
            app_df.to_csv(path, index=False, encoding="utf-8-sig")
            paths[f"app_{safe_name}"] = path
        return paths

    def _export_by_category(self, df: pd.DataFrame) -> Path:
        rows = []
        for _, row in df.iterrows():
            for cat in str(row["categories"]).split(" | "):
                rows.append({
                    "category": cat.strip(),
                    "app_name": row["app_name"],
                    "text": row["text"],
                    "sentiment_label": row["sentiment_label"],
                    "sentiment_score": row["sentiment_score"],
                    "author": row["author"],
                    "subreddit": row["subreddit"],
                    "permalink": row["permalink"],
                    "date": row["date"],
                })

        path = self._output_dir / "reviews_by_category.csv"
        pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
        return path

    def _export_text_only(self, df: pd.DataFrame) -> Path:
        cols = [
            "app_name", "primary_category", "sentiment_label",
            "text", "author", "subreddit", "permalink",
        ]
        path = self._output_dir / "reviews_text_only.csv"
        df[cols].to_csv(path, index=False, encoding="utf-8-sig")
        return path

    def _export_stats_json(self, df: pd.DataFrame) -> Path:
        stats = {
            "total_reviews": len(df),
            "posts_count": int((df["source"] == "post").sum()),
            "comments_count": int((df["source"] == "comment").sum()),
            "apps": {},
            "categories": {},
            "sentiment": {},
            "subreddits": {},
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        for app_name, grp in df.groupby("app_name"):
            stats["apps"][app_name] = {
                "total": len(grp),
                "avg_sentiment": round(float(grp["sentiment_score"].mean()), 3),
                "positive": int((grp["sentiment_label"] == "positive").sum()),
                "negative": int((grp["sentiment_label"] == "negative").sum()),
                "neutral": int((grp["sentiment_label"] == "neutral").sum()),
                "top_categories": {
                    k: int(v)
                    for k, v in grp["primary_category"].value_counts().head(5).items()
                },
            }

        stats["categories"] = {k: int(v) for k, v in df["primary_category"].value_counts().items()}
        stats["sentiment"] = {k: int(v) for k, v in df["sentiment_label"].value_counts().items()}
        stats["subreddits"] = {k: int(v) for k, v in df["subreddit"].value_counts().items()}

        path = self._output_dir / "stats_summary.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        return path

    def _export_markdown_report(self, df: pd.DataFrame) -> Path:
        stats_path = self._output_dir / "stats_summary.json"
        with open(stats_path, encoding="utf-8") as f:
            stats = json.load(f)

        lines: list[str] = []
        lines.append("# 💑 Couple Apps Review Report\n")
        lines.append(f"**Generated:** {stats['generated_at']}\n")
        lines.append(f"**Total reviews:** {stats['total_reviews']}  ")
        lines.append(
            f"**Posts:** {stats['posts_count']} "
            f"| **Comments:** {stats['comments_count']}\n"
        )
        lines.append("\n---\n")

        # By app
        lines.append("## 📱 By App\n")
        lines.append("| App | Reviews | Avg Sentiment | 😊 | 😞 | 😐 |")
        lines.append("|---|---|---|---|---|---|")
        for app, s in sorted(stats["apps"].items(), key=lambda x: x[1]["total"], reverse=True):
            lines.append(
                f"| {app} | {s['total']} | {s['avg_sentiment']:.2f} "
                f"| {s['positive']} | {s['negative']} | {s['neutral']} |"
            )

        lines.append("\n---\n")

        # By category
        lines.append("## 📂 By Category\n")
        lines.append("| Category | Count |")
        lines.append("|---|---|")
        for cat, cnt in sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True):
            lines.append(f"| {cat} | {cnt} |")

        lines.append("\n---\n")

        # Top positive
        lines.append("## ⭐ Top Positive Reviews\n")
        pos = df[df["sentiment_label"] == "positive"].nlargest(10, "sentiment_score")
        for _, row in pos.iterrows():
            lines.append(f"**{row['app_name']}** (r/{row['subreddit']})")
            clean = str(row["text"])[:300].replace("\n", " ")
            lines.append(f"> {clean}...\n")

        lines.append("\n---\n")

        # Top negative
        lines.append("## 😞 Top Negative Reviews\n")
        neg = df[df["sentiment_label"] == "negative"].nsmallest(10, "sentiment_score")
        for _, row in neg.iterrows():
            lines.append(f"**{row['app_name']}** (r/{row['subreddit']})")
            clean = str(row["text"])[:300].replace("\n", " ")
            lines.append(f"> {clean}...\n")

        path = self._output_dir / "REPORT.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return path
