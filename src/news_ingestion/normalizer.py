from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

from .hash_generator import sha256_text
from .models import Article, NaverNewsItem


TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
SPECIAL_RE = re.compile(r"[^0-9a-zA-Z가-힣]+")
NAVER_ARTICLE_RE = re.compile(r"/article/([0-9]{3})/([0-9]+)")
WEAK_LABELS = {
    "단독",
    "속보",
    "종합",
    "영상",
    "포토",
    "사진",
    "인터뷰",
    "exclusive",
    "breaking",
    "comprehensive",
    "video",
    "photo",
    "interview",
}
TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "yclid",
    "sid",
}
API_SOURCE = "NAVER_NEWS"


class ArticleNormalizer:
    def from_naver_item(self, item: NaverNewsItem, search_keyword: str) -> Article:
        title = clean_html_text(item.title)
        description = clean_html_text(item.description) or None
        original_url = item.originallink or None
        naver_url = item.link or None
        canonical_url = normalize_url(item.originallink or item.link)
        normalized_title = normalize_title(title)
        normalized_description = normalize_description(description or "")
        published_at = parse_pub_date(item.pubDate)
        source_name = extract_source_name(canonical_url)
        external_article_id = generate_external_article_id(
            naver_url=naver_url,
            canonical_url=canonical_url,
            title=title,
            published_at=published_at,
            source_name=source_name,
        )
        raw_payload = json.dumps(
            item.raw_payload
            or {
                "title": item.title,
                "originallink": item.originallink,
                "link": item.link,
                "description": item.description,
                "pubDate": item.pubDate,
            },
            ensure_ascii=False,
            sort_keys=True,
        )

        return Article(
            api_source=API_SOURCE,
            search_keyword=search_keyword,
            title_raw=item.title,
            title=title,
            normalized_title=normalized_title,
            title_hash=generate_hash(normalized_title),
            description_raw=item.description,
            description=description,
            normalized_description=normalized_description,
            original_url=original_url,
            naver_url=naver_url,
            canonical_url=canonical_url,
            canonical_url_hash=generate_hash(canonical_url),
            external_article_id=external_article_id,
            source_name=source_name,
            published_at=published_at,
            fetched_at=datetime.now(timezone.utc).replace(tzinfo=None),
            raw_payload=raw_payload,
            summary=None,
            main_keywords=None,
            parties=None,
            regions=None,
            people=None,
            content_hash=generate_hash(f"{normalized_title} {normalized_description}".strip()),
        )


def clean_html_text(value: str | None) -> str:
    if not value:
        return ""
    unescaped = html.unescape(value)
    without_tags = TAG_RE.sub("", unescaped)
    return WHITESPACE_RE.sub(" ", without_tags).strip()


def normalize_title(title: str) -> str:
    return _normalize_for_comparison(title)


def normalize_description(description: str) -> str:
    return _normalize_for_comparison(description)


def normalize_url(value: str | None) -> str:
    if not value:
        return ""
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return value.strip()
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    path = quote(unquote(parts.path), safe="/:%@")
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    query_pairs = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS and not key.lower().startswith("utm_")
    ]
    query = urlencode(query_pairs, doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def generate_external_article_id(
    naver_url: str | None,
    canonical_url: str | None,
    title: str,
    published_at: datetime | None,
    source_name: str | None,
) -> str:
    if naver_url:
        match = NAVER_ARTICLE_RE.search(naver_url)
        if match:
            return f"NAVER_{match.group(1)}_{match.group(2)}"
    if canonical_url:
        return f"URL_HASH_{generate_hash(canonical_url)}"
    fingerprint = "|".join(
        [
            normalize_title(title),
            published_at.isoformat() if published_at else "",
            source_name or "",
        ]
    )
    return f"CONTENT_{generate_hash(fingerprint)}"


def parse_pub_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def parse_naver_datetime(value: str) -> datetime | None:
    return parse_pub_date(value)


def extract_source_name(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = urlsplit(url).netloc.lower()
    except ValueError:
        return None
    if host.startswith("www."):
        host = host[4:]
    return host or None


def generate_hash(value: str | None) -> str | None:
    return sha256_text(value)


def tokenize_normalized(value: str | None) -> set[str]:
    if not value:
        return set()
    return {token for token in value.split() if token and token not in WEAK_LABELS}


def _normalize_for_comparison(value: str | None) -> str:
    cleaned = clean_html_text(value)
    lowered = cleaned.casefold()
    without_special = SPECIAL_RE.sub(" ", lowered)
    tokens = [
        token
        for token in WHITESPACE_RE.sub(" ", without_special).strip().split(" ")
        if token and token not in WEAK_LABELS
    ]
    return " ".join(tokens)
