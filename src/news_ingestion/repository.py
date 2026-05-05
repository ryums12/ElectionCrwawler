from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from .config import DatabaseConfig
from .models import Article, SaveResult

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

    def save_article(self, article: Article) -> SaveResult:
        sql = """
            INSERT INTO articles (
                source,
                search_keyword,
                original_url,
                original_url_hash,
                canonical_url,
                canonical_url_hash,
                title,
                normalized_title,
                title_hash,
                content_hash,
                body,
                summary,
                published_at,
                crawled_at,
                cluster_id,
                duplicate_of
            ) VALUES (
                %(source)s,
                %(search_keyword)s,
                %(original_url)s,
                %(original_url_hash)s,
                %(canonical_url)s,
                %(canonical_url_hash)s,
                %(title)s,
                %(normalized_title)s,
                %(title_hash)s,
                %(content_hash)s,
                %(body)s,
                %(summary)s,
                %(published_at)s,
                %(crawled_at)s,
                %(cluster_id)s,
                %(duplicate_of)s
            )
        """

        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(sql, article.__dict__)
                    return SaveResult(inserted=True, article_id=cursor.lastrowid)
        except Exception as exc:
            if not _is_integrity_error(exc):
                raise
            return SaveResult(
                inserted=False,
                article_id=None,
                reason="canonical_url_already_seen",
            )


def _is_integrity_error(exc: Exception) -> bool:
    return exc.__class__.__name__ == "IntegrityError"
