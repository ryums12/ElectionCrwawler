from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .hash_generator import sha256_text
from .models import Article, NaverNewsItem


TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


class ArticleNormalizer:
    def from_naver_item(self, item: NaverNewsItem, search_keyword: str) -> Article:
        title = _clean_text(item.title)
        body = _clean_text(item.description) or None
        original_url = item.originallink or None
        canonical_url = item.link or item.originallink
        normalized_title = normalize_title(title)

        return Article(
            source="naver_news_search",
            search_keyword=search_keyword,
            original_url=original_url,
            original_url_hash=sha256_text(original_url),
            canonical_url=canonical_url,
            canonical_url_hash=sha256_text(canonical_url),
            title=title,
            normalized_title=normalized_title,
            title_hash=sha256_text(normalized_title),
            content_hash=sha256_text(body),
            body=body,
            published_at=parse_naver_datetime(item.pubDate),
            crawled_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )


def normalize_title(title: str) -> str:
    return WHITESPACE_RE.sub(" ", title).strip().casefold()


def parse_naver_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    unescaped = html.unescape(value)
    without_tags = TAG_RE.sub("", unescaped)
    return WHITESPACE_RE.sub(" ", without_tags).strip()
