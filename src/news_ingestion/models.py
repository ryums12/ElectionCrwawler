from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NaverNewsItem:
    title: str
    originallink: str
    link: str
    description: str
    pubDate: str


@dataclass(frozen=True)
class Article:
    source: str
    search_keyword: str
    original_url: str | None
    original_url_hash: str | None
    canonical_url: str
    canonical_url_hash: str
    title: str
    normalized_title: str
    title_hash: str
    content_hash: str | None
    body: str | None
    published_at: datetime | None
    crawled_at: datetime
    summary: str | None = None
    cluster_id: int | None = None
    duplicate_of: int | None = None


@dataclass(frozen=True)
class SaveResult:
    inserted: bool
    article_id: int | None
    reason: str | None = None
