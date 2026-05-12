from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from .config import DatabaseConfig
from .models import (
    Article,
    CandidateCluster,
    DuplicateClusterResult,
    ExistingArticle,
    NaverNewsResponse,
    SaveResult,
)
from .normalizer import parse_pub_date

Connection = object


class ArticleRepository:
    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config

    @contextmanager
    def _connect(self) -> Iterator[Connection]:
        import pymysql

        connection = pymysql.connect(
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password,
            database=self._config.name,
            charset=self._config.charset,
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor,
        )
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get_last_seen_external_article_id(
        self,
        api_source: str,
        search_keyword: str,
    ) -> str | None:
        sql = """
            SELECT last_seen_external_article_id
            FROM news_crawl_state
            WHERE api_source = %s AND search_keyword = %s
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, (api_source, search_keyword))
                row = cursor.fetchone()
                return row["last_seen_external_article_id"] if row else None

    def upsert_crawl_state(self, article: Article) -> None:
        sql = """
            INSERT INTO news_crawl_state (
                api_source,
                search_keyword,
                last_seen_external_article_id,
                last_seen_published_at,
                last_seen_title,
                last_seen_url,
                updated_at
            ) VALUES (
                %(api_source)s,
                %(search_keyword)s,
                %(external_article_id)s,
                %(published_at)s,
                %(title)s,
                %(canonical_url)s,
                %(updated_at)s
            )
            ON DUPLICATE KEY UPDATE
                last_seen_external_article_id = VALUES(last_seen_external_article_id),
                last_seen_published_at = VALUES(last_seen_published_at),
                last_seen_title = VALUES(last_seen_title),
                last_seen_url = VALUES(last_seen_url),
                updated_at = VALUES(updated_at)
        """
        params = {
            **article.__dict__,
            "updated_at": _utc_now(),
        }
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)

    def create_fetch_log(
        self,
        response: NaverNewsResponse,
        api_source: str,
        search_keyword: str,
    ) -> int:
        sql = """
            INSERT INTO news_api_fetch_logs (
                api_source,
                search_keyword,
                last_build_date,
                total,
                start,
                display,
                fetched_count,
                inserted_count,
                duplicate_count,
                fetched_at,
                raw_response
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, 0, 0, %s, %s
            )
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        api_source,
                        search_keyword,
                        parse_pub_date(response.lastBuildDate),
                        response.total,
                        response.start,
                        response.display,
                        len(response.items),
                        _utc_now(),
                        json.dumps(response.raw_payload, ensure_ascii=False, sort_keys=True),
                    ),
                )
                return int(cursor.lastrowid)

    def update_fetch_log(
        self,
        fetch_log_id: int,
        inserted_count: int,
        duplicate_count: int,
    ) -> None:
        sql = """
            UPDATE news_api_fetch_logs
            SET inserted_count = inserted_count + %s,
                duplicate_count = duplicate_count + %s
            WHERE id = %s
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, (inserted_count, duplicate_count, fetch_log_id))

    def find_duplicate_article(self, article: Article) -> ExistingArticle | None:
        sql = """
            SELECT id, cluster_id
            FROM articles
            WHERE (api_source = %s AND external_article_id = %s)
               OR (canonical_url_hash IS NOT NULL AND canonical_url_hash = %s)
               OR (content_hash IS NOT NULL AND content_hash = %s)
            ORDER BY id ASC
            LIMIT 1
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        article.api_source,
                        article.external_article_id,
                        article.canonical_url_hash,
                        article.content_hash,
                    ),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return ExistingArticle(id=int(row["id"]), cluster_id=row["cluster_id"])

    def find_candidate_clusters(
        self,
        article: Article,
        lookback_hours: int = 72,
        limit: int = 100,
    ) -> list[CandidateCluster]:
        sql = """
            SELECT
                id,
                representative_article_id,
                cluster_summary,
                normalized_title,
                normalized_description,
                title_hash,
                content_hash,
                main_keywords,
                parties,
                regions,
                people,
                first_published_at,
                last_published_at
            FROM news_clusters
            WHERE search_keyword = %s
              AND (
                    %s IS NULL
                    OR last_published_at IS NULL
                    OR last_published_at >= DATE_SUB(%s, INTERVAL %s HOUR)
                  )
            ORDER BY
                CASE WHEN title_hash = %s THEN 0 ELSE 1 END,
                last_published_at DESC
            LIMIT %s
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        article.search_keyword,
                        article.published_at,
                        article.published_at,
                        lookback_hours,
                        article.title_hash,
                        limit,
                    ),
                )
                return [_candidate_cluster_from_row(row) for row in cursor.fetchall()]

    def save_article(self, article: Article) -> SaveResult:
        sql = """
            INSERT INTO articles (
                api_source,
                search_keyword,
                title_raw,
                title,
                normalized_title,
                title_hash,
                description_raw,
                description,
                normalized_description,
                original_url,
                naver_url,
                canonical_url,
                canonical_url_hash,
                external_article_id,
                source_name,
                published_at,
                fetched_at,
                raw_payload,
                summary,
                main_keywords,
                parties,
                regions,
                people,
                content_hash,
                cluster_id
            ) VALUES (
                %(api_source)s,
                %(search_keyword)s,
                %(title_raw)s,
                %(title)s,
                %(normalized_title)s,
                %(title_hash)s,
                %(description_raw)s,
                %(description)s,
                %(normalized_description)s,
                %(original_url)s,
                %(naver_url)s,
                %(canonical_url)s,
                %(canonical_url_hash)s,
                %(external_article_id)s,
                %(source_name)s,
                %(published_at)s,
                %(fetched_at)s,
                %(raw_payload)s,
                %(summary)s,
                %(main_keywords)s,
                %(parties)s,
                %(regions)s,
                %(people)s,
                %(content_hash)s,
                %(cluster_id)s
            )
        """
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, article.__dict__)
                    return SaveResult(inserted=True, article_id=int(cursor.lastrowid))
        except Exception as exc:
            if not _is_integrity_error(exc):
                raise
            return SaveResult(inserted=False, article_id=None, reason="article_already_seen")

    def create_cluster_from_article(self, article_id: int, article: Article) -> int:
        sql = """
            INSERT INTO news_clusters (
                representative_article_id,
                search_keyword,
                cluster_title,
                cluster_summary,
                normalized_title,
                normalized_description,
                title_hash,
                content_hash,
                main_keywords,
                parties,
                regions,
                people,
                first_published_at,
                last_published_at,
                article_count,
                duplicate_count,
                created_at,
                updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 0, %s, %s
            )
        """
        now = _utc_now()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        article_id,
                        article.search_keyword,
                        article.title,
                        article.summary,
                        article.normalized_title,
                        article.normalized_description,
                        article.title_hash,
                        article.content_hash,
                        article.main_keywords,
                        article.parties,
                        article.regions,
                        article.people,
                        article.published_at,
                        article.published_at,
                        now,
                        now,
                    ),
                )
                return int(cursor.lastrowid)

    def update_article_cluster_id(self, article_id: int, cluster_id: int) -> None:
        sql = "UPDATE articles SET cluster_id = %s, updated_at = %s WHERE id = %s"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, (cluster_id, _utc_now(), article_id))

    def increment_cluster_duplicate_count(
        self,
        cluster_id: int,
        duplicate_published_at: datetime | None,
    ) -> None:
        sql = """
            UPDATE news_clusters
            SET article_count = article_count + 1,
                duplicate_count = duplicate_count + 1,
                last_published_at = CASE
                    WHEN %s IS NULL THEN last_published_at
                    WHEN last_published_at IS NULL OR %s > last_published_at THEN %s
                    ELSE last_published_at
                END,
                first_published_at = CASE
                    WHEN %s IS NULL THEN first_published_at
                    WHEN first_published_at IS NULL OR %s < first_published_at THEN %s
                    ELSE first_published_at
                END,
                updated_at = %s
            WHERE id = %s
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        duplicate_published_at,
                        duplicate_published_at,
                        duplicate_published_at,
                        duplicate_published_at,
                        duplicate_published_at,
                        duplicate_published_at,
                        _utc_now(),
                        cluster_id,
                    ),
                )

    def cluster_has_enrichment(self, cluster_id: int) -> bool:
        sql = """
            SELECT cluster_summary, main_keywords, parties, regions, people
            FROM news_clusters
            WHERE id = %s
            LIMIT 1
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, (cluster_id,))
                row = cursor.fetchone()
                if not row:
                    return False
                return _has_enrichment(row)

    def update_cluster_enrichment(self, cluster_id: int, article: Article) -> None:
        sql = """
            UPDATE news_clusters
            SET cluster_summary = COALESCE(cluster_summary, %s),
                main_keywords = COALESCE(main_keywords, %s),
                parties = COALESCE(parties, %s),
                regions = COALESCE(regions, %s),
                people = COALESCE(people, %s),
                updated_at = %s
            WHERE id = %s
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        article.summary,
                        article.main_keywords,
                        article.parties,
                        article.regions,
                        article.people,
                        _utc_now(),
                        cluster_id,
                    ),
                )

    def save_duplicate_log(
        self,
        article: Article,
        result: DuplicateClusterResult,
    ) -> None:
        if result.matched_cluster_id is None:
            return
        sql = """
            INSERT INTO news_duplicate_logs (
                cluster_id,
                representative_article_id,
                api_source,
                search_keyword,
                duplicate_external_article_id,
                duplicate_title,
                duplicate_url,
                duplicate_published_at,
                similarity_score,
                duplicate_reason,
                raw_payload,
                detected_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        result.matched_cluster_id,
                        result.representative_article_id,
                        article.api_source,
                        article.search_keyword,
                        article.external_article_id,
                        article.title,
                        article.canonical_url,
                        article.published_at,
                        result.similarity_score,
                        result.duplicate_reason,
                        article.raw_payload,
                        _utc_now(),
                    ),
                )


def _candidate_cluster_from_row(row: dict) -> CandidateCluster:
    return CandidateCluster(
        id=int(row["id"]),
        representative_article_id=row["representative_article_id"],
        cluster_summary=row.get("cluster_summary"),
        normalized_title=row.get("normalized_title") or "",
        normalized_description=row.get("normalized_description") or "",
        title_hash=row.get("title_hash"),
        content_hash=row.get("content_hash"),
        main_keywords=row.get("main_keywords"),
        parties=row.get("parties"),
        regions=row.get("regions"),
        people=row.get("people"),
        first_published_at=row.get("first_published_at"),
        last_published_at=row.get("last_published_at"),
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_integrity_error(exc: Exception) -> bool:
    return exc.__class__.__name__ == "IntegrityError"


def _has_enrichment(row: dict) -> bool:
    return bool(
        row.get("cluster_summary")
        and row.get("main_keywords")
        and row.get("parties") is not None
        and row.get("regions") is not None
        and row.get("people") is not None
    )
