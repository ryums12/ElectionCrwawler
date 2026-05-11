from __future__ import annotations

import logging
from dataclasses import dataclass

from .duplicate_checker import DuplicateChecker
from .models import Article, ProcessResult, SaveResult
from .naver_client import NaverNewsClient
from .normalizer import API_SOURCE, ArticleNormalizer
from .repository import ArticleRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionStats:
    fetched: int = 0
    inserted: int = 0
    skipped_existing: int = 0


class NewsIngestionService:
    def __init__(
        self,
        client: NaverNewsClient,
        normalizer: ArticleNormalizer,
        duplicate_checker: DuplicateChecker,
        repository: ArticleRepository,
    ) -> None:
        self._client = client
        self._normalizer = normalizer
        self._duplicate_checker = duplicate_checker
        self._repository = repository

    def ingest_keywords(self, keywords: tuple[str, ...]) -> IngestionStats:
        fetched = 0
        inserted = 0
        skipped_existing = 0

        for keyword in keywords:
            logger.info("Fetching Naver news for keyword=%s", keyword)
            previous_checkpoint_id = self._repository.get_last_seen_external_article_id(
                API_SOURCE,
                keyword,
            )
            new_checkpoint_article: Article | None = None
            stopped_by_checkpoint = False

            for response in self._client.search_pages(keyword):
                result, checkpoint_article = self._process_response(
                    keyword,
                    response,
                    previous_checkpoint_id,
                    new_checkpoint_article,
                )
                fetched += len(response.items)
                inserted += result.inserted_count
                skipped_existing += result.duplicate_count
                new_checkpoint_article = checkpoint_article or new_checkpoint_article

                if result.stopped_by_checkpoint:
                    stopped_by_checkpoint = True
                    break

            if new_checkpoint_article is not None:
                self._repository.upsert_crawl_state(new_checkpoint_article)

            logger.info(
                "Keyword ingestion finished: keyword=%s stopped_by_checkpoint=%s",
                keyword,
                stopped_by_checkpoint,
            )

        stats = IngestionStats(
            fetched=fetched,
            inserted=inserted,
            skipped_existing=skipped_existing,
        )
        logger.info("Ingestion finished: %s", stats)
        return stats

    def _process_response(
        self,
        keyword: str,
        response,
        previous_checkpoint_id: str | None,
        checkpoint_article: Article | None,
    ) -> tuple[ProcessResult, Article | None]:
        fetch_log_id = self._repository.create_fetch_log(response, API_SOURCE, keyword)
        inserted_count = 0
        duplicate_count = 0
        stopped_by_checkpoint = False
        new_checkpoint_article = checkpoint_article

        for item in response.items:
            article = self._normalizer.from_naver_item(item, keyword)
            if new_checkpoint_article is None:
                new_checkpoint_article = article

            if article.external_article_id == previous_checkpoint_id:
                stopped_by_checkpoint = True
                break

            if self._handle_exact_duplicate(article):
                duplicate_count += 1
                continue

            if self._handle_cluster_duplicate(article):
                duplicate_count += 1
                continue

            result = self._insert_article_and_cluster(article)
            if _inserted(result):
                inserted_count += 1
            else:
                duplicate_count += 1

        self._repository.update_fetch_log(fetch_log_id, inserted_count, duplicate_count)

        return (
            ProcessResult(
                inserted_count=inserted_count,
                duplicate_count=duplicate_count,
                stopped_by_checkpoint=stopped_by_checkpoint,
            ),
            new_checkpoint_article,
        )

    def _handle_exact_duplicate(self, article: Article) -> bool:
        existing_article = self._repository.find_duplicate_article(article)
        if not existing_article:
            return False
        if existing_article.cluster_id is not None:
            self._repository.increment_cluster_duplicate_count(
                existing_article.cluster_id,
                article.published_at,
            )
        return True

    def _handle_cluster_duplicate(self, article: Article) -> bool:
        result = self._duplicate_checker.find_duplicate_cluster(article, self._repository)
        if not result.is_duplicate or result.matched_cluster_id is None:
            return False
        self._repository.increment_cluster_duplicate_count(
            result.matched_cluster_id,
            article.published_at,
        )
        self._repository.save_duplicate_log(article, result)
        return True

    def _insert_article_and_cluster(self, article: Article) -> SaveResult:
        result = self._repository.save_article(article)
        if not result.inserted or result.article_id is None:
            return result

        cluster_id = self._repository.create_cluster_from_article(result.article_id, article)
        self._repository.update_article_cluster_id(result.article_id, cluster_id)
        return result


def _inserted(result: SaveResult) -> bool:
    return result.inserted
