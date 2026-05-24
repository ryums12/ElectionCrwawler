from __future__ import annotations

import json
import unittest
from datetime import datetime

from src.news_ingestion.config import EnrichmentConfig
from src.news_ingestion.enricher import ArticleEnricher
from src.news_ingestion.models import Article
from src.news_ingestion.metadata_aliases import (
    merge_regions,
    normalize_party_values,
    normalize_region_values,
    normalize_regions_from_text,
)


class MetadataAliasTests(unittest.TestCase):
    def test_party_aliases_normalize_single_democratic_party_alias(self) -> None:
        self.assertEqual(normalize_party_values(["민주당"]), ["더불어민주당"])

    def test_party_aliases_keep_canonical_democratic_party_name(self) -> None:
        self.assertEqual(normalize_party_values(["더불어민주당"]), ["더불어민주당"])

    def test_party_aliases_deduplicate_after_normalization(self) -> None:
        self.assertEqual(normalize_party_values(["민주당", "더불어민주당"]), ["더불어민주당"])

    def test_party_aliases_preserve_stable_order_for_unrelated_names(self) -> None:
        self.assertEqual(normalize_party_values(["국민의힘", "민주당"]), ["국민의힘", "더불어민주당"])

    def test_party_aliases_ignore_whitespace_for_alias_lookup(self) -> None:
        self.assertEqual(normalize_party_values(["더불어 민주당", " 민주당 "]), ["더불어민주당"])

    def test_direct_province_aliases_use_short_name(self) -> None:
        self.assertEqual(
            normalize_regions_from_text("경상북도 포항에서 지방선거 관련 기자회견이 열렸다."),
            ["경북"],
        )
        self.assertEqual(normalize_regions_from_text("경북도당은 후보 공천 결과를 발표했다."), ["경북"])

    def test_city_aliases_use_short_name(self) -> None:
        self.assertEqual(normalize_regions_from_text("서울특별시와 부산시 선거 판세"), ["서울", "부산"])

    def test_regional_group_expands_components(self) -> None:
        self.assertEqual(
            normalize_regions_from_text("수도권 선거 판세가 요동치고 있다."),
            ["수도권", "서울", "경기", "인천"],
        )
        self.assertEqual(
            normalize_regions_from_text("부울경 민심이 이번 지방선거의 변수로 떠올랐다."),
            ["부울경", "부산", "울산", "경남"],
        )
        self.assertEqual(
            normalize_regions_from_text("충청 지역 후보들이 공동 공약을 발표했다."),
            ["충청권", "대전", "세종", "충북", "충남"],
        )

    def test_deduplicates_with_stable_order(self) -> None:
        self.assertEqual(
            normalize_regions_from_text("수도권 서울시 인천광역시 경기도"),
            ["수도권", "서울", "경기", "인천"],
        )

    def test_llm_returned_region_values_are_normalized(self) -> None:
        self.assertEqual(
            normalize_region_values(["경상북도", "경북", "서울특별시", "충청"]),
            ["경북", "서울", "충청권", "대전", "세종", "충북", "충남"],
        )

    def test_merge_regions_normalizes_and_deduplicates(self) -> None:
        self.assertEqual(
            merge_regions(["경상북도", "서울"], ["경북도", "수도권"]),
            ["경북", "서울", "수도권", "경기", "인천"],
        )

    def test_university_names_do_not_trigger_region_by_themselves(self) -> None:
        self.assertEqual(normalize_regions_from_text("경북대학교 총학생회가 토론회를 열었다."), [])
        self.assertEqual(normalize_regions_from_text("전남대와 충북대가 공동 연구를 발표했다."), [])

    def test_llm_false_positive_region_values_are_ignored(self) -> None:
        self.assertEqual(normalize_region_values(["중구", "경북대", "경남대학교", "서울시"]), ["서울"])


class EnricherMetadataAliasTests(unittest.TestCase):
    def test_enricher_normalizes_party_aliases_before_save(self) -> None:
        client = FakeOpenAIClient(
            {
                "summary": "정당 공천 결과가 발표됐다.",
                "main_keywords": [],
                "parties": ["국민의힘", "민주당", "더불어 민주당"],
                "people": [],
                "regions": [],
            }
        )
        enricher = ArticleEnricher(
            EnrichmentConfig(
                openai_api_key="test-key",
                openai_model="test-model",
                request_timeout_seconds=1,
                article_fetch_timeout_seconds=1,
                max_article_chars=2000,
            ),
            body_fetcher=lambda _url: "정당 공천 결과가 발표됐고 국민의힘과 민주당이 입장을 냈다.",
            llm_client=client,
        )

        enriched = enricher.enrich(_article())

        self.assertEqual(json.loads(enriched.parties or "[]"), ["국민의힘", "더불어민주당"])

    def test_enricher_merges_llm_regions_with_alias_regions_before_save(self) -> None:
        client = FakeOpenAIClient(
            {
                "summary": "수도권 판세가 핵심 변수로 떠올랐다.",
                "main_keywords": [],
                "parties": [],
                "people": [],
                "regions": ["경상북도"],
            }
        )
        enricher = ArticleEnricher(
            EnrichmentConfig(
                openai_api_key="test-key",
                openai_model="test-model",
                request_timeout_seconds=1,
                article_fetch_timeout_seconds=1,
                max_article_chars=2000,
            ),
            body_fetcher=lambda _url: "부울경 민심과 서울시당 움직임이 함께 주목된다.",
            llm_client=client,
        )

        enriched = enricher.enrich(_article())

        self.assertEqual(
            json.loads(enriched.regions or "[]"),
            ["경북", "강원", "제주", "수도권", "서울", "경기", "인천", "부울경", "부산", "울산", "경남"],
        )


class FakeOpenAIClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.chat = self
        self.completions = self

    def create(self, **_kwargs):
        return _OpenAIResponse(json.dumps(self.payload, ensure_ascii=False))


class _OpenAIResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_OpenAIChoice(content)]


class _OpenAIChoice:
    def __init__(self, content: str) -> None:
        self.message = _OpenAIMessage(content)


class _OpenAIMessage:
    def __init__(self, content: str) -> None:
        self.content = content


def _article() -> Article:
    return Article(
        api_source="naver",
        search_keyword="지방선거",
        title_raw="경북도당 후보 공천 결과 발표",
        title="경북도당 후보 공천 결과 발표",
        normalized_title="경북도당 후보 공천 결과 발표",
        title_hash=None,
        description_raw="강원특별자치도와 제주도 선거 소식",
        description="강원특별자치도와 제주도 선거 소식",
        normalized_description="강원특별자치도와 제주도 선거 소식",
        original_url="https://example.com/article",
        naver_url=None,
        canonical_url="https://example.com/article",
        canonical_url_hash=None,
        external_article_id="article-1",
        source_name="Example",
        published_at=datetime(2026, 5, 18, 0, 0, 0),
        fetched_at=datetime(2026, 5, 18, 0, 0, 0),
        raw_payload="{}",
        summary=None,
        main_keywords=None,
        parties=None,
        regions=None,
        people=None,
        content_hash=None,
    )


if __name__ == "__main__":
    unittest.main()
