from __future__ import annotations

import json
import unittest
from datetime import datetime

from src.news_ingestion.config import EnrichmentConfig
from src.news_ingestion.duplicate_checker import DuplicateChecker
from src.news_ingestion.enricher import ArticleEnricher, parse_enrichment_json
from src.news_ingestion.ingestion_service import NewsIngestionService
from src.news_ingestion.models import (
    CandidateCluster,
    ExistingArticle,
    NaverNewsItem,
    NaverNewsResponse,
    SaveResult,
)
from src.news_ingestion.normalizer import (
    API_SOURCE,
    ArticleNormalizer,
    clean_html_text,
    generate_external_article_id,
    parse_pub_date,
)


class NormalizerTests(unittest.TestCase):
    def test_title_b_tags_are_removed(self) -> None:
        self.assertEqual(
            clean_html_text("‘충주맨’ 김선태, 6·3 <b>지방선거</b> 개표방송"),
            "‘충주맨’ 김선태, 6·3 지방선거 개표방송",
        )

    def test_description_b_tags_are_removed(self) -> None:
        self.assertEqual(
            clean_html_text("전 공무원이 <b>지방선거</b> 방송에 출연한다."),
            "전 공무원이 지방선거 방송에 출연한다.",
        )

    def test_pub_date_is_parsed_as_utc_naive_datetime(self) -> None:
        parsed = parse_pub_date("Mon, 11 May 2026 08:49:00 +0900")
        self.assertEqual(parsed, datetime(2026, 5, 10, 23, 49, 0))

    def test_external_article_id_prefers_naver_article_path(self) -> None:
        self.assertEqual(
            generate_external_article_id(
                "https://n.news.naver.com/mnews/article/009/0005677914?sid=102",
                "https://www.mk.co.kr/article/12042878",
                "title",
                datetime(2026, 5, 10, 23, 49, 0),
                "mk.co.kr",
            ),
            "NAVER_009_0005677914",
        )


class DuplicateCheckerTests(unittest.TestCase):
    def test_substantially_identical_articles_match_existing_cluster(self) -> None:
        article = _article(
            title="충주맨 김선태 6 3 지방선거 개표방송 출연 지역 소멸 논의",
            description="김선태가 지방선거 개표방송에 출연해 지역 소멸 문제를 논의한다",
        )
        repository = FakeRepository(
            candidate_clusters=[
                CandidateCluster(
                    id=15,
                    representative_article_id=7,
                    cluster_summary=None,
                    normalized_title="충주맨 김선태 6 3 지방선거 개표방송 출연 지역 소멸 논의",
                    normalized_description="김선태가 지방선거 개표방송에 출연해 지역 소멸 문제를 논의한다",
                    title_hash=None,
                    content_hash=None,
                    main_keywords=None,
                    parties=None,
                    regions=None,
                    people=None,
                    first_published_at=article.published_at,
                    last_published_at=article.published_at,
                )
            ]
        )

        result = DuplicateChecker().find_duplicate_cluster(article, repository)

        self.assertTrue(result.is_duplicate)
        self.assertEqual(result.matched_cluster_id, 15)

    def test_same_keyword_only_does_not_match_existing_cluster(self) -> None:
        article = _article(
            title="부산 후보 교통 공약 발표",
            description="부산시장 후보가 지방선거 교통 공약을 공개했다",
        )
        repository = FakeRepository(
            candidate_clusters=[
                CandidateCluster(
                    id=15,
                    representative_article_id=7,
                    cluster_summary=None,
                    normalized_title="충주맨 김선태 개표방송 출연 지역 소멸 논의",
                    normalized_description="김선태가 지방선거 개표방송에 출연한다",
                    title_hash=None,
                    content_hash=None,
                    main_keywords=None,
                    parties=None,
                    regions=None,
                    people=None,
                    first_published_at=article.published_at,
                    last_published_at=article.published_at,
                )
            ]
        )

        result = DuplicateChecker().find_duplicate_cluster(article, repository)

        self.assertFalse(result.is_duplicate)


class EnricherTests(unittest.TestCase):
    def test_missing_openai_api_key_leaves_article_unchanged(self) -> None:
        article = _article("Title", "Description")
        enricher = ArticleEnricher(_enrichment_config(api_key=None))

        self.assertEqual(enricher.enrich(article), article)

    def test_original_article_fetch_failure_falls_back_to_api_text(self) -> None:
        article = _article("Title", "Description")
        client = FakeOpenAIClient(
            {
                "summary": "요약",
                "main_keywords": ["공약"],
                "parties": [],
                "people": [],
                "regions": [],
            }
        )
        enricher = ArticleEnricher(
            _enrichment_config(),
            body_fetcher=lambda _url: (_ for _ in ()).throw(RuntimeError("blocked")),
            llm_client=client,
        )

        enriched = enricher.enrich(article)

        self.assertEqual(enriched.summary, "요약")
        self.assertEqual(json.loads(enriched.main_keywords), ["공약"])
        self.assertEqual(client.call_count, 1)

    def test_parse_enrichment_json_supports_multiple_entities(self) -> None:
        result = parse_enrichment_json(
            json.dumps(
                {
                    "summary": "요약",
                    "main_keywords": ["선거", "공약"],
                    "parties": ["A당", "B당"],
                    "people": ["홍길동", "김철수"],
                    "regions": ["서울", "부산"],
                },
                ensure_ascii=False,
            )
        )

        self.assertEqual(result.parties, ["A당", "B당"])
        self.assertEqual(result.people, ["홍길동", "김철수"])
        self.assertEqual(result.regions, ["서울", "부산"])


class IngestionServiceTests(unittest.TestCase):
    def test_same_canonical_url_is_not_inserted_and_increments_cluster(self) -> None:
        item = _item("Title", "Description", article_no="0005677914", original_url="https://example.com/a")
        article = ArticleNormalizer().from_naver_item(item, "지방선거")
        repository = FakeRepository(existing_by_canonical={article.canonical_url_hash: ExistingArticle(1, 10)})
        service = _service([_response([item])], repository)

        stats = service.ingest_keywords(("지방선거",))

        self.assertEqual(stats.inserted, 0)
        self.assertEqual(stats.skipped_existing, 1)
        self.assertEqual(repository.incremented_clusters, [10])

    def test_same_content_hash_is_not_inserted_and_increments_cluster(self) -> None:
        item = _item("Title", "Description", article_no="0005677915", original_url="https://example.com/b")
        article = ArticleNormalizer().from_naver_item(item, "지방선거")
        repository = FakeRepository(existing_by_content={article.content_hash: ExistingArticle(2, 11)})
        service = _service([_response([item])], repository)

        stats = service.ingest_keywords(("지방선거",))

        self.assertEqual(stats.inserted, 0)
        self.assertEqual(stats.skipped_existing, 1)
        self.assertEqual(repository.incremented_clusters, [11])

    def test_duplicate_cluster_is_not_inserted_and_counts_are_incremented(self) -> None:
        item = _item(
            "충주맨 김선태 지방선거 개표방송 출연",
            "김선태가 지방선거 개표방송에 출연해 지역 소멸을 논의한다",
            article_no="0005677916",
            original_url="https://example.com/c",
        )
        article = ArticleNormalizer().from_naver_item(item, "지방선거")
        repository = FakeRepository(
            candidate_clusters=[
                CandidateCluster(
                    id=20,
                    representative_article_id=3,
                    cluster_summary=None,
                    normalized_title=article.normalized_title,
                    normalized_description=article.normalized_description,
                    title_hash=article.title_hash,
                    content_hash=None,
                    main_keywords=None,
                    parties=None,
                    regions=None,
                    people=None,
                    first_published_at=article.published_at,
                    last_published_at=article.published_at,
                )
            ]
        )
        service = _service([_response([item])], repository)

        stats = service.ingest_keywords(("지방선거",))

        self.assertEqual(stats.inserted, 0)
        self.assertEqual(stats.skipped_existing, 1)
        self.assertEqual(repository.incremented_clusters, [20])
        self.assertEqual(len(repository.duplicate_logs), 1)

    def test_stops_when_previous_checkpoint_is_seen(self) -> None:
        first = _item("새 기사", "새 설명", article_no="0005677917", original_url="https://example.com/d")
        previous = _item("이전 기사", "이전 설명", article_no="0005677918", original_url="https://example.com/e")
        repository = FakeRepository(previous_checkpoint_id="NAVER_009_0005677918")
        service = _service([_response([first, previous])], repository)

        stats = service.ingest_keywords(("지방선거",))

        self.assertEqual(stats.inserted, 1)
        self.assertEqual(len(repository.saved_articles), 1)

    def test_first_item_is_saved_as_new_checkpoint(self) -> None:
        first = _item("첫 기사", "첫 설명", article_no="0005677919", original_url="https://example.com/f")
        second = _item("둘째 기사", "둘째 설명", article_no="0005677920", original_url="https://example.com/g")
        repository = FakeRepository()
        service = _service([_response([first, second])], repository)

        service.ingest_keywords(("지방선거",))

        self.assertEqual(repository.crawl_state_article.external_article_id, "NAVER_009_0005677919")

    def test_new_article_is_saved_with_enrichment_arrays(self) -> None:
        item = _item("Title", "Description", article_no="0005677921", original_url="https://example.com/h")
        repository = FakeRepository()
        service = _service(
            [_response([item])],
            repository,
            enricher=StaticEnricher(
                summary="요약",
                main_keywords=["선거", "공약"],
                parties=["A당", "B당"],
                people=["홍길동", "김철수"],
                regions=["서울", "부산"],
            ),
        )

        stats = service.ingest_keywords(("keyword",))

        self.assertEqual(stats.inserted, 1)
        saved = repository.saved_articles[0]
        self.assertEqual(saved.summary, "요약")
        self.assertEqual(json.loads(saved.parties), ["A당", "B당"])
        self.assertEqual(json.loads(saved.people), ["홍길동", "김철수"])
        self.assertEqual(json.loads(saved.regions), ["서울", "부산"])

    def test_summarized_duplicate_cluster_skips_enrichment_call(self) -> None:
        item = _item("Title", "Description", article_no="0005677922", original_url="https://example.com/i")
        article = ArticleNormalizer().from_naver_item(item, "keyword")
        repository = FakeRepository(
            candidate_clusters=[
                CandidateCluster(
                    id=30,
                    representative_article_id=4,
                    cluster_summary="이미 요약됨",
                    normalized_title=article.normalized_title,
                    normalized_description=article.normalized_description,
                    title_hash=article.title_hash,
                    content_hash=None,
                    main_keywords='["선거"]',
                    parties="[]",
                    regions="[]",
                    people="[]",
                    first_published_at=article.published_at,
                    last_published_at=article.published_at,
                )
            ],
            cluster_enriched=True,
        )
        enricher = CountingEnricher()
        service = _service([_response([item])], repository, enricher=enricher)

        stats = service.ingest_keywords(("keyword",))

        self.assertEqual(stats.skipped_existing, 1)
        self.assertEqual(enricher.call_count, 0)


class FakeClient:
    def __init__(self, responses: list[NaverNewsResponse]) -> None:
        self._responses = responses

    def search_pages(self, _query: str):
        yield from self._responses


class FakeOpenAIClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.call_count = 0
        self.chat = self
        self.completions = self

    def create(self, **_kwargs):
        self.call_count += 1
        content = json.dumps(self.payload, ensure_ascii=False)
        return _OpenAIResponse(content)


class _OpenAIResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_OpenAIChoice(content)]


class _OpenAIChoice:
    def __init__(self, content: str) -> None:
        self.message = _OpenAIMessage(content)


class _OpenAIMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class StaticEnricher:
    def __init__(
        self,
        summary: str,
        main_keywords: list[str],
        parties: list[str],
        people: list[str],
        regions: list[str],
    ) -> None:
        self.summary = summary
        self.main_keywords = main_keywords
        self.parties = parties
        self.people = people
        self.regions = regions

    def enrich(self, article):
        from dataclasses import replace

        return replace(
            article,
            summary=self.summary,
            main_keywords=json.dumps(self.main_keywords, ensure_ascii=False),
            parties=json.dumps(self.parties, ensure_ascii=False),
            people=json.dumps(self.people, ensure_ascii=False),
            regions=json.dumps(self.regions, ensure_ascii=False),
        )


class CountingEnricher:
    def __init__(self) -> None:
        self.call_count = 0

    def enrich(self, article):
        self.call_count += 1
        return article


class FakeRepository:
    def __init__(
        self,
        previous_checkpoint_id: str | None = None,
        existing_by_canonical: dict[str | None, ExistingArticle] | None = None,
        existing_by_content: dict[str | None, ExistingArticle] | None = None,
        candidate_clusters: list[CandidateCluster] | None = None,
        cluster_enriched: bool = False,
    ) -> None:
        self.previous_checkpoint_id = previous_checkpoint_id
        self.existing_by_canonical = existing_by_canonical or {}
        self.existing_by_content = existing_by_content or {}
        self.candidate_clusters = candidate_clusters or []
        self.cluster_enriched = cluster_enriched
        self.incremented_clusters: list[int] = []
        self.saved_articles = []
        self.duplicate_logs = []
        self.cluster_enrichment_updates = []
        self.crawl_state_article = None
        self.fetch_log_id = 0

    def get_last_seen_external_article_id(self, _api_source: str, _search_keyword: str) -> str | None:
        return self.previous_checkpoint_id

    def upsert_crawl_state(self, article) -> None:
        self.crawl_state_article = article

    def create_fetch_log(self, *_args) -> int:
        self.fetch_log_id += 1
        return self.fetch_log_id

    def update_fetch_log(self, *_args) -> None:
        return None

    def find_duplicate_article(self, article):
        return self.existing_by_canonical.get(article.canonical_url_hash) or self.existing_by_content.get(
            article.content_hash
        )

    def find_candidate_clusters(self, *_args):
        return self.candidate_clusters

    def increment_cluster_duplicate_count(self, cluster_id: int, _published_at) -> None:
        self.incremented_clusters.append(cluster_id)

    def cluster_has_enrichment(self, _cluster_id: int) -> bool:
        return self.cluster_enriched

    def update_cluster_enrichment(self, cluster_id: int, article) -> None:
        self.cluster_enrichment_updates.append((cluster_id, article))

    def save_duplicate_log(self, article, result) -> None:
        self.duplicate_logs.append((article, result))

    def save_article(self, article):
        self.saved_articles.append(article)
        return SaveResult(inserted=True, article_id=len(self.saved_articles))

    def create_cluster_from_article(self, article_id: int, _article) -> int:
        return article_id + 100

    def update_article_cluster_id(self, _article_id: int, _cluster_id: int) -> None:
        return None


def _service(
    responses: list[NaverNewsResponse],
    repository: FakeRepository,
    enricher=None,
) -> NewsIngestionService:
    return NewsIngestionService(
        client=FakeClient(responses),
        normalizer=ArticleNormalizer(),
        duplicate_checker=DuplicateChecker(),
        repository=repository,
        enricher=enricher,
    )


def _enrichment_config(api_key: str | None = "test-key") -> EnrichmentConfig:
    return EnrichmentConfig(
        openai_api_key=api_key,
        openai_model="test-model",
        request_timeout_seconds=1,
        article_fetch_timeout_seconds=1,
        max_article_chars=2000,
    )


def _article(title: str, description: str):
    return ArticleNormalizer().from_naver_item(
        _item(title, description, article_no="0005677914", original_url="https://example.com/a"),
        "지방선거",
    )


def _item(title: str, description: str, article_no: str, original_url: str) -> NaverNewsItem:
    return NaverNewsItem(
        title=title,
        originallink=original_url,
        link=f"https://n.news.naver.com/mnews/article/009/{article_no}?sid=102",
        description=description,
        pubDate="Mon, 11 May 2026 08:49:00 +0900",
        raw_payload={
            "title": title,
            "originallink": original_url,
            "link": f"https://n.news.naver.com/mnews/article/009/{article_no}?sid=102",
            "description": description,
            "pubDate": "Mon, 11 May 2026 08:49:00 +0900",
        },
    )


def _response(items: list[NaverNewsItem]) -> NaverNewsResponse:
    return NaverNewsResponse(
        lastBuildDate="Mon, 11 May 2026 10:22:17 +0900",
        total=len(items),
        start=1,
        display=len(items),
        items=tuple(items),
        raw_payload={"items": [item.raw_payload for item in items]},
    )


if __name__ == "__main__":
    unittest.main()
