# ElectionCrawler

Hourly Naver News Search ingestion for local election coverage.

The current pipeline only fetches and stores articles. Summarization, tagging,
clustering, richer duplicate detection, and UI work are intentionally left for
later components.

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

The starter schema is kept, with small additions:

- `search_keyword`: records which configured keyword produced the article.
- `original_url_hash` and `canonical_url_hash`: make exact URL storage idempotent without relying on indexing `TEXT` columns.
- Indexes on timestamps, hashes, cluster IDs, and duplicate pointers.
- Foreign keys for future cluster and duplicate relationships.

Exact same canonical URLs are skipped by the repository. This is not the future
article duplicate detection system; it only prevents the hourly API job from
inserting the same API result repeatedly.

## Hourly Flow

1. `main.py` loads `.env` configuration.
2. `HourlyScheduler` starts a run immediately and then sleeps for the configured interval.
3. `NaverNewsClient` fetches date-sorted news results for each keyword.
4. `ArticleNormalizer` removes Naver highlight tags, decodes HTML entities, parses `pubDate`, and computes normalized fields.
5. Hashes are generated for URLs, title, and snippet content.
6. `DuplicateChecker.mark_duplicate()` is called as a clearly separated placeholder for future duplicate detection.
7. `ArticleRepository` inserts the article. Existing canonical URLs are skipped.

## Project Structure

```text
src/news_ingestion/
  config.py             # .env loading and validation
  naver_client.py       # Naver News Search API client
  normalizer.py         # title/body cleanup and date parsing
  hash_generator.py     # SHA-256 helpers
  duplicate_checker.py  # future duplicate detection hook
  repository.py         # database writes
  ingestion_service.py  # application workflow
  scheduler.py          # hourly runner
  main.py               # CLI entry point
```
