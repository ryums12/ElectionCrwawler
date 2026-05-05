from __future__ import annotations

import logging
from dataclasses import dataclass

from .duplicate_checker import DuplicateChecker
from .models import SaveResult
from .naver_client import NaverNewsClient
from .normalizer import ArticleNormalizer
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
            for item in self._client.search(keyword):
                fetched += 1
                article = self._normalizer.from_naver_item(item, keyword)

                # Future duplicate detection hook:
                # This is where title/content/canonical URL similarity checks can
                # assign article.duplicate_of before the repository saves it.
                article = self._duplicate_checker.mark_duplicate(article)

                result = self._repository.save_article(article)
                if _inserted(result):
                    inserted += 1
                else:
                    skipped_existing += 1

        stats = IngestionStats(
            fetched=fetched,
            inserted=inserted,
            skipped_existing=skipped_existing,
        )
        logger.info("Ingestion finished: %s", stats)
        return stats


def _inserted(result: SaveResult) -> bool:
    return result.inserted
