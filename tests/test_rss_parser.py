"""Tests for RSS parser."""

from __future__ import annotations

from src.scraper.rss_parser import clean_html, parse_rss_feed

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Reddit Search Results</title>
  <entry>
    <title>Best couple apps 2024?</title>
    <link href="https://www.reddit.com/r/relationships/comments/abc123/best_couple_apps/"/>
    <content type="html">&lt;p&gt;Looking for a good couple app.&lt;/p&gt;</content>
    <author><name>/u/testuser</name></author>
    <updated>2024-01-15T10:30:00Z</updated>
    <category term="relationships"/>
  </entry>
  <entry>
    <title>Deleted post</title>
    <link href="https://www.reddit.com/r/test/comments/xyz/deleted/"/>
    <content type="html">[deleted]</content>
    <author><name>/u/gone</name></author>
    <updated>2024-01-14T08:00:00Z</updated>
    <category term="test"/>
  </entry>
  <entry>
    <title>Subreddit link</title>
    <link href="https://www.reddit.com/r/relationships/"/>
    <content type="html">&lt;p&gt;Some content&lt;/p&gt;</content>
    <author><name>/u/bot</name></author>
    <updated>2024-01-13T12:00:00Z</updated>
    <category term="relationships"/>
  </entry>
</feed>
"""


class TestCleanHTML:
    def test_strips_tags(self):
        assert clean_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_decodes_entities(self):
        assert clean_html("&amp; &lt; &gt;") == "& < >"

    def test_empty_string(self):
        assert clean_html("") == ""

    def test_none_returns_empty(self):
        assert clean_html(None) == ""  # type: ignore[arg-type]

    def test_normalises_whitespace(self):
        assert clean_html("hello   \n\t  world") == "hello world"


class TestParseRSSFeed:
    def test_parses_valid_entry(self):
        entries = parse_rss_feed(SAMPLE_RSS)
        assert len(entries) == 1  # deleted and subreddit-link entries should be skipped

    def test_entry_fields(self):
        entries = parse_rss_feed(SAMPLE_RSS)
        entry = entries[0]
        assert entry.title == "Best couple apps 2024?"
        assert "couple app" in entry.body.lower() or "good" in entry.body.lower()
        assert entry.author == "testuser"  # /u/ prefix stripped
        assert entry.subreddit == "relationships"

    def test_invalid_xml(self):
        entries = parse_rss_feed("not xml at all")
        assert entries == []

    def test_empty_feed(self):
        xml = '<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        entries = parse_rss_feed(xml)
        assert entries == []
