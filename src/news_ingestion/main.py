from __future__ import annotations

import argparse
import logging

from .config import load_config
from .duplicate_checker import DuplicateChecker
from .ingestion_service import NewsIngestionService
from .naver_client import NaverNewsClient
from .normalizer import ArticleNormalizer
from .repository import ArticleRepository
from .scheduler import HourlyScheduler


def build_service() -> tuple[NewsIngestionService, tuple[str, ...], int]:
    config = load_config()
    service = NewsIngestionService(
        client=NaverNewsClient(config.naver),
        normalizer=ArticleNormalizer(),
        duplicate_checker=DuplicateChecker(),
        repository=ArticleRepository(config.database),
    )
    return service, config.search_keywords, config.ingestion_interval_seconds


def main() -> None:
    parser = argparse.ArgumentParser(description="Naver news ingestion pipeline")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run ingestion once and exit instead of scheduling hourly.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    service, keywords, interval_seconds = build_service()
    if args.once:
        service.ingest_keywords(keywords)
        return

    HourlyScheduler(
        service=service,
        keywords=keywords,
        interval_seconds=interval_seconds,
    ).run_forever(run_immediately=True)


if __name__ == "__main__":
    main()
