from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_KEYWORDS = ("지방선거", "지방 선거")


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    name: str
    user: str
    password: str
    sslmode: str | None = None


@dataclass(frozen=True)
class NaverConfig:
    client_id: str
    client_secret: str
    display: int = 100
    max_pages: int = 1


@dataclass(frozen=True)
class EnrichmentConfig:
    openai_api_key: str | None
    openai_model: str = "gpt-4.1-mini"
    request_timeout_seconds: int = 30
    article_fetch_timeout_seconds: int = 10
    max_article_chars: int = 12000


@dataclass(frozen=True)
class AppConfig:
    database: DatabaseConfig
    naver: NaverConfig
    enrichment: EnrichmentConfig
    search_keywords: tuple[str, ...]
    ingestion_interval_seconds: int = 3600


def load_config() -> AppConfig:
    load_dotenv()

    client_id = _required("NAVER_CLIENT_ID")
    client_secret = _required("NAVER_CLIENT_SECRET")

    keywords = tuple(
        keyword.strip()
        for keyword in os.getenv("SEARCH_KEYWORDS", ",".join(DEFAULT_KEYWORDS)).split(",")
        if keyword.strip()
    )

    display = _bounded_int("NAVER_DISPLAY", default=100, minimum=1, maximum=100)
    max_pages = _bounded_int("NAVER_MAX_PAGES", default=1, minimum=1, maximum=10)

    return AppConfig(
        database=DatabaseConfig(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=_int("DB_PORT", 5432),
            name=_required("DB_NAME"),
            user=_required("DB_USER"),
            password=_required("DB_PASSWORD"),
            sslmode=_sslmode_from_env(os.getenv("DB_SSL")),
        ),
        naver=NaverConfig(
            client_id=client_id,
            client_secret=client_secret,
            display=display,
            max_pages=max_pages,
        ),
        enrichment=EnrichmentConfig(
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            request_timeout_seconds=_int("OPENAI_REQUEST_TIMEOUT_SECONDS", 30),
            article_fetch_timeout_seconds=_int("ARTICLE_FETCH_TIMEOUT_SECONDS", 10),
            max_article_chars=_int("ENRICHMENT_MAX_ARTICLE_CHARS", 12000),
        ),
        search_keywords=keywords,
        ingestion_interval_seconds=_int("INGESTION_INTERVAL_SECONDS", 3600),
    )


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    value = _int(name, default)
    if value < minimum or value > maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return value


def _sslmode_from_env(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "require"}:
        return "require"
    if normalized in {"0", "false", "no", "disable"}:
        return "disable"
    return normalized


def load_dotenv(path: str = ".env") -> None:
    try:
        from dotenv import load_dotenv as python_dotenv_load
    except ImportError:
        _load_dotenv_fallback(path)
        return

    python_dotenv_load(path)


def _load_dotenv_fallback(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as env_file:
        for line in env_file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))
