from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, replace
from html import unescape
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import EnrichmentConfig
from .models import Article
from .normalizer import clean_html_text
from .metadata_aliases import merge_regions, normalize_party_values, normalize_regions_from_text

logger = logging.getLogger(__name__)

SCRIPT_STYLE_RE = re.compile(r"<(script|style|noscript)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
ARTICLE_RE = re.compile(r"<article\b[^>]*>(.*?)</article>", re.IGNORECASE | re.DOTALL)
MAIN_RE = re.compile(r"<main\b[^>]*>(.*?)</main>", re.IGNORECASE | re.DOTALL)
BODY_RE = re.compile(r"<body\b[^>]*>(.*?)</body>", re.IGNORECASE | re.DOTALL)
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class EnrichmentResult:
    summary: str | None
    main_keywords: list[str]
    parties: list[str]
    people: list[str]
    regions: list[str]


class ArticleEnricher:
    def __init__(
        self,
        config: EnrichmentConfig,
        body_fetcher: Callable[[str], str | None] | None = None,
        llm_client: Any | None = None,
    ) -> None:
        self._config = config
        self._body_fetcher = body_fetcher or self._fetch_article_body
        self._llm_client = llm_client

    def enrich(self, article: Article) -> Article:
        if not self._config.openai_api_key:
            logger.info("OPENAI_API_KEY is not set; saving article without enrichment.")
            return article

        source_text = self._source_text(article)
        if not source_text:
            return article

        try:
            result = self._request_enrichment(article, source_text)
        except Exception:
            logger.exception("Article enrichment failed: external_article_id=%s", article.external_article_id)
            return article

        alias_regions = normalize_regions_from_text(
            "\n".join(
                value
                for value in (
                    article.title,
                    article.description or "",
                    result.summary or "",
                    source_text,
                )
                if value
            )
        )
        regions = merge_regions(result.regions, alias_regions)
        parties = normalize_party_values(result.parties)

        return replace(
            article,
            summary=result.summary,
            main_keywords=_json_array(result.main_keywords),
            parties=_json_array(parties),
            people=_json_array(result.people),
            regions=_json_array(regions),
        )

    def _source_text(self, article: Article) -> str:
        body = None
        if article.canonical_url:
            try:
                body = self._body_fetcher(article.canonical_url)
            except Exception:
                logger.warning("Original article fetch failed; falling back to API text: url=%s", article.canonical_url)

        fallback = "\n".join(
            value for value in (article.title, article.description or "") if value
        ).strip()
        selected = (body or "").strip() or fallback
        return selected[: self._config.max_article_chars]

    def _request_enrichment(self, article: Article, source_text: str) -> EnrichmentResult:
        client = self._client()
        prompt = _build_prompt(article, source_text)
        response = client.chat.completions.create(
            model=self._config.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract metadata from Korean election news. "
                        "Return strict JSON only, with no markdown or commentary."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            timeout=self._config.request_timeout_seconds,
        )
        content = response.choices[0].message.content
        return parse_enrichment_json(content)

    def _client(self):
        if self._llm_client is not None:
            return self._llm_client
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("The openai package is required for enrichment.") from exc
        self._llm_client = OpenAI(api_key=self._config.openai_api_key)
        return self._llm_client

    def _fetch_article_body(self, url: str) -> str | None:
        request = Request(
            url,
            headers={
                "User-Agent": "ElectionCrawler/1.0 (+news enrichment)",
                "Accept": "text/html,application/xhtml+xml",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self._config.article_fetch_timeout_seconds) as response:
                content_type = response.headers.get("Content-Type", "")
                if "html" not in content_type.lower():
                    return None
                html = response.read(1_500_000).decode(_charset(content_type), errors="replace")
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            logger.warning("Original article request failed: url=%s error=%s", url, exc)
            return None

        try:
            return extract_article_text(html)
        except Exception:
            logger.exception("Original article parsing failed: url=%s", url)
            return None


def parse_enrichment_json(content: str | None) -> EnrichmentResult:
    if not content:
        raise ValueError("LLM response was empty.")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM response was not valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ValueError("LLM response JSON must be an object.")

    return EnrichmentResult(
        summary=_clean_optional_string(parsed.get("summary")),
        main_keywords=_clean_string_list(parsed.get("main_keywords")),
        parties=_clean_string_list(parsed.get("parties")),
        people=_clean_string_list(parsed.get("people")),
        regions=_clean_string_list(parsed.get("regions")),
    )


def extract_article_text(html: str) -> str | None:
    cleaned = SCRIPT_STYLE_RE.sub(" ", html)
    candidates = ARTICLE_RE.findall(cleaned) or MAIN_RE.findall(cleaned) or BODY_RE.findall(cleaned)
    selected = max(candidates, key=len) if candidates else cleaned
    text = clean_html_text(unescape(selected))
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text if len(text) >= 80 else None


def _build_prompt(article: Article, source_text: str) -> str:
    return json.dumps(
        {
            "instructions": {
                "summary": "Write a concise Korean summary in 1-3 sentences.",
                "arrays": "Return arrays of strings. Use [] when no value is present.",
                "schema": ["summary", "main_keywords", "parties", "people", "regions"],
            },
            "article": {
                "title": article.title,
                "description": article.description,
                "source_name": article.source_name,
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "text": source_text,
            },
        },
        ensure_ascii=False,
    )


def _clean_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    seen = set()
    items = []
    for raw in value:
        item = str(raw).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        items.append(item)
    return items


def _json_array(value: list[str]) -> str:
    return json.dumps(value, ensure_ascii=False)


def _charset(content_type: str) -> str:
    match = re.search(r"charset=([\w.-]+)", content_type, re.IGNORECASE)
    return match.group(1) if match else "utf-8"
