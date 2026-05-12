from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class NaverNewsItem:
    title: str
    originallink: str
    link: str
    description: str
    pubDate: str
    raw_payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class NaverNewsResponse:
    lastBuildDate: str
    total: int
    start: int
    display: int
    items: tuple[NaverNewsItem, ...]
    raw_payload: dict[str, Any]


@dataclass(frozen=True)
class Article:
    api_source: str
    search_keyword: str
    title_raw: str
    title: str
    normalized_title: str
    title_hash: str | None
    description_raw: str
    description: str | None
    normalized_description: str
    original_url: str | None
    naver_url: str | None
    canonical_url: str
    canonical_url_hash: str | None
    external_article_id: str
    source_name: str | None
    published_at: datetime | None
    fetched_at: datetime
    raw_payload: str
    summary: str | None
    main_keywords: str | None
    parties: str | None
    regions: str | None
    people: str | None
    content_hash: str | None
    cluster_id: int | None = None


@dataclass(frozen=True)
class ExistingArticle:
    id: int
    cluster_id: int | None


@dataclass(frozen=True)
class CandidateCluster:
    id: int
    representative_article_id: int | None
    cluster_summary: str | None
    normalized_title: str
    normalized_description: str
    title_hash: str | None
    content_hash: str | None
    main_keywords: str | None
    parties: str | None
    regions: str | None
    people: str | None
    first_published_at: datetime | None
    last_published_at: datetime | None


@dataclass(frozen=True)
class DuplicateClusterResult:
    is_duplicate: bool
    matched_cluster_id: int | None = None
    representative_article_id: int | None = None
    similarity_score: float = 0.0
    duplicate_reason: str | None = None


@dataclass(frozen=True)
class SaveResult:
    inserted: bool
    article_id: int | None
    reason: str | None = None


@dataclass(frozen=True)
class ProcessResult:
    inserted_count: int
    duplicate_count: int
    stopped_by_checkpoint: bool
