# ElectionCrawler

Hourly Naver News Search ingestion for local election coverage.

The pipeline fetches Naver News Search API results, stores representative
articles, groups substantially identical items into clusters, and records fetch
logs plus crawl checkpoints for hourly updates.

## What It Fetches

Default search keywords:

- `지방선거`
- `지방 선거`

The pipeline uses the Naver News Search JSON API:

- Endpoint: `https://openapi.naver.com/v1/search/news.json`
- Auth headers: `X-Naver-Client-Id`, `X-Naver-Client-Secret`
- Sort order: `date`
- Page size: up to `100`

## Setup

1. Create and activate a virtual environment.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

3. Create your `.env`.

```powershell
Copy-Item .env.example .env
```

Fill in the Naver API credentials and database settings in `.env`.

4. Create the database and run the migration.

```sql
CREATE DATABASE election_news CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Then run:

```powershell
mysql -u election_user -p election_news < migrations/001_create_news_tables.sql
```

## Running

Run one ingestion pass and exit:

```powershell
.\.venv\Scripts\python -m src.news_ingestion --once
```

Run continuously. The first pass runs immediately, then repeats every hour:

```powershell
.\.venv\Scripts\python -m src.news_ingestion
```

The interval can be changed with `INGESTION_INTERVAL_SECONDS` in `.env`.

## Environment Variables

See `.env.example` for the full list.

- `NAVER_CLIENT_ID`: Naver application client ID
- `NAVER_CLIENT_SECRET`: Naver application client secret
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_CHARSET`: MySQL or MariaDB connection settings
- `SEARCH_KEYWORDS`: comma-separated search terms
- `NAVER_DISPLAY`: number of results per request, from `1` to `100`
- `NAVER_MAX_PAGES`: pages per keyword per run
- `INGESTION_INTERVAL_SECONDS`: scheduler interval, default `3600`

## Schema Notes

The schema stores only representative service-visible articles in `articles`.
Duplicate API items are counted on `news_clusters` and optionally recorded in
`news_duplicate_logs` for tuning.

- `articles`: raw and cleaned titles/descriptions, original and Naver URLs, generated external IDs, normalized comparison fields, hashes, raw payloads, summary/keyword fields, and cluster links.
- `news_clusters`: representative article metadata, normalized comparison fields, first/last publication times, `article_count`, and `duplicate_count`.
- `news_api_fetch_logs`: per API page bookkeeping, including inserted and duplicate counts.
- `news_crawl_state`: latest-first checkpoint per `api_source` and `search_keyword`.

For existing databases created from the starter migration, apply
`migrations/002_expand_news_api_storage.sql`.

## Hourly Flow

1. `main.py` loads `.env` configuration.
2. `HourlyScheduler` starts a run immediately and then sleeps for the configured interval.
3. `NaverNewsClient` fetches date-sorted news result pages for each keyword.
4. `ArticleNormalizer` stores raw API text, removes HTML tags, decodes entities, normalizes URLs/text, parses RFC-822 dates, and generates external article IDs.
5. Exact duplicate checks use `api_source + external_article_id`, canonical URL hash, and content hash.
6. `DuplicateChecker` compares candidate clusters using local title/description token similarity, keyword overlap, and publication time.
7. New articles are inserted and assigned a new cluster; duplicate items update cluster counts and duplicate logs.
8. `news_crawl_state` is updated with the first item seen in the successful run so later pages can stop at the previous checkpoint.

## Project Structure

```text
src/news_ingestion/
  config.py             # .env loading and validation
  naver_client.py       # Naver News Search API client
  normalizer.py         # title/body cleanup and date parsing
  hash_generator.py     # SHA-256 helpers
  duplicate_checker.py  # exact and cluster-level duplicate decisions
  repository.py         # database reads/writes for articles, clusters, logs, state
  ingestion_service.py  # application workflow
  scheduler.py          # hourly runner
  main.py               # CLI entry point
```
