# ruff: noqa: RUF001 E501
"""
Text pattern analysis — N-grams, TF-IDF keywords, word frequency.

Used by the dashboard to show patterns in review texts.
"""
from __future__ import annotations

import re
from collections import Counter


def get_ngrams(texts: list[str], n: int = 2, top_k: int = 30) -> list[tuple[str, int]]:
    """Extract top N-grams from texts."""
    _STOP = frozenset({
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "shall", "can",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "into", "through", "during", "before", "after", "above",
        "below", "between", "out", "off", "over", "under", "again",
        "further", "then", "once", "here", "there", "when", "where",
        "why", "how", "all", "each", "every", "both", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only",
        "own", "same", "so", "than", "too", "very", "just", "don",
        "should", "now", "and", "but", "or", "if", "that", "this",
        "it", "its", "i", "me", "my", "we", "our", "you", "your",
        "he", "him", "his", "she", "her", "they", "them", "their",
        "what", "which", "who", "whom", "these", "those", "am",
        "about", "up", "also", "like", "even", "get", "got",
        "going", "go", "re", "ve", "ll", "don", "didn", "doesn",
        "wasn", "weren", "hasn", "haven", "isn", "aren", "won",
        "couldn", "wouldn", "shouldn", "s", "t", "m", "d",
        "submitted", "comments", "link", "https", "http", "www",
        "com", "reddit", "deleted", "removed",
    })

    counter: Counter = Counter()
    for text in texts:
        words = re.findall(r"\b[a-z]{2,}\b", text.lower())
        words = [w for w in words if w not in _STOP]
        for i in range(len(words) - n + 1):
            gram = " ".join(words[i:i + n])
            counter[gram] += 1

    return counter.most_common(top_k)


def get_word_freq(texts: list[str], top_k: int = 100) -> dict[str, int]:
    """Get word frequencies for word cloud generation."""
    _STOP = frozenset({
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "can", "to", "of", "in",
        "for", "on", "with", "at", "by", "from", "as", "into",
        "through", "during", "before", "after", "out", "off",
        "over", "under", "again", "then", "here", "there",
        "when", "where", "why", "how", "all", "each", "every",
        "both", "few", "more", "most", "other", "some", "such",
        "no", "nor", "not", "only", "own", "same", "so", "than",
        "too", "very", "just", "now", "and", "but", "or", "if",
        "that", "this", "it", "its", "i", "me", "my", "we", "our",
        "you", "your", "he", "him", "his", "she", "her", "they",
        "them", "their", "what", "which", "who", "whom", "about",
        "up", "also", "like", "even", "get", "got", "going", "go",
        "re", "ve", "ll", "don", "didn", "doesn", "wasn", "weren",
        "hasn", "haven", "isn", "aren", "won", "t", "s", "m", "d",
        "submitted", "comments", "link", "https", "http", "www",
        "com", "reddit", "deleted", "removed", "really", "much",
        "been", "being", "one", "two", "still", "well", "back",
        "think", "know", "make", "use", "using", "used",
    })

    counter: Counter = Counter()
    for text in texts:
        words = re.findall(r"\b[a-z]{3,}\b", text.lower())
        for w in words:
            if w not in _STOP:
                counter[w] += 1
    return dict(counter.most_common(top_k))


def get_tfidf_keywords(texts: list[str], top_k: int = 20) -> list[tuple[str, float]]:
    """Extract top TF-IDF keywords across all texts."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        return []

    if len(texts) < 3:
        return []

    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.8,
    )
    try:
        matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return []

    feature_names = vectorizer.get_feature_names_out()
    scores = matrix.mean(axis=0).A1  # type: ignore[union-attr]

    top_indices = scores.argsort()[-top_k:][::-1]
    return [(feature_names[i], round(float(scores[i]), 4)) for i in top_indices]
