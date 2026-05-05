from __future__ import annotations

import logging
import signal
import time
from threading import Event

from .ingestion_service import NewsIngestionService

logger = logging.getLogger(__name__)


class HourlyScheduler:
    def __init__(
        self,
        service: NewsIngestionService,
        keywords: tuple[str, ...],
        interval_seconds: int,
    ) -> None:
        self._service = service
        self._keywords = keywords
        self._interval_seconds = interval_seconds
        self._stop_event = Event()

    def run_forever(self, run_immediately: bool = True) -> None:
        signal.signal(signal.SIGTERM, self._stop)
        signal.signal(signal.SIGINT, self._stop)

        if run_immediately:
            self._run_once()

        while not self._stop_event.wait(self._interval_seconds):
            self._run_once()

        logger.info("Scheduler stopped")

    def _run_once(self) -> None:
        try:
            started_at = time.monotonic()
            self._service.ingest_keywords(self._keywords)
            elapsed = time.monotonic() - started_at
            logger.info("Next ingestion in %s seconds", self._interval_seconds)
            logger.debug("Ingestion elapsed seconds: %.2f", elapsed)
        except Exception:
            logger.exception("Ingestion run failed")

    def _stop(self, signum: int, _frame: object) -> None:
        logger.info("Received signal %s", signum)
        self._stop_event.set()
