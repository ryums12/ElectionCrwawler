ALTER TABLE news_clusters
    CHANGE COLUMN representative_title cluster_title TEXT,
    CHANGE COLUMN representative_summary cluster_summary TEXT,
    ADD COLUMN IF NOT EXISTS search_keyword VARCHAR(255) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS normalized_title TEXT,
    ADD COLUMN IF NOT EXISTS normalized_description TEXT,
    ADD COLUMN IF NOT EXISTS title_hash CHAR(64),
    ADD COLUMN IF NOT EXISTS content_hash CHAR(64),
    ADD COLUMN IF NOT EXISTS first_published_at DATETIME,
    ADD COLUMN IF NOT EXISTS last_published_at DATETIME,
    ADD COLUMN IF NOT EXISTS article_count BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS duplicate_count BIGINT NOT NULL DEFAULT 0;

ALTER TABLE articles
    CHANGE COLUMN source api_source VARCHAR(100) NOT NULL,
    CHANGE COLUMN body description TEXT,
    CHANGE COLUMN crawled_at fetched_at DATETIME,
    ADD COLUMN IF NOT EXISTS title_raw TEXT AFTER search_keyword,
    ADD COLUMN IF NOT EXISTS description_raw TEXT AFTER title_hash,
    ADD COLUMN IF NOT EXISTS normalized_description TEXT AFTER description,
    ADD COLUMN IF NOT EXISTS naver_url TEXT AFTER original_url,
    ADD COLUMN IF NOT EXISTS external_article_id VARCHAR(255) AFTER canonical_url_hash,
    ADD COLUMN IF NOT EXISTS source_name VARCHAR(255) AFTER external_article_id,
    ADD COLUMN IF NOT EXISTS raw_payload JSON AFTER fetched_at,
    ADD COLUMN IF NOT EXISTS main_keywords TEXT AFTER summary,
    ADD COLUMN IF NOT EXISTS parties TEXT AFTER main_keywords,
    ADD COLUMN IF NOT EXISTS regions TEXT AFTER parties,
    ADD COLUMN IF NOT EXISTS people TEXT AFTER regions,
    ADD COLUMN IF NOT EXISTS created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

UPDATE articles
SET title_raw = COALESCE(title_raw, title),
    description_raw = COALESCE(description_raw, description),
    normalized_description = COALESCE(normalized_description, normalized_title),
    external_article_id = COALESCE(external_article_id, CONCAT('URL_HASH_', canonical_url_hash))
WHERE external_article_id IS NULL OR title_raw IS NULL OR description_raw IS NULL;

UPDATE articles
SET api_source = 'NAVER_NEWS'
WHERE api_source = 'naver_news_search';

ALTER TABLE articles
    MODIFY COLUMN external_article_id VARCHAR(255) NOT NULL,
    ADD UNIQUE KEY uq_articles_api_external_id (api_source, external_article_id),
    ADD KEY idx_articles_keyword_published_at (search_keyword, published_at);

CREATE TABLE IF NOT EXISTS news_api_fetch_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    api_source VARCHAR(100) NOT NULL,
    search_keyword VARCHAR(255) NOT NULL,
    last_build_date DATETIME,
    total BIGINT,
    start INT,
    display INT,
    fetched_count INT NOT NULL DEFAULT 0,
    inserted_count INT NOT NULL DEFAULT 0,
    duplicate_count INT NOT NULL DEFAULT 0,
    fetched_at DATETIME,
    raw_response JSON
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS news_crawl_state (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    api_source VARCHAR(100) NOT NULL,
    search_keyword VARCHAR(255) NOT NULL,
    last_seen_external_article_id VARCHAR(255),
    last_seen_published_at DATETIME,
    last_seen_title TEXT,
    last_seen_url TEXT,
    updated_at DATETIME,
    UNIQUE KEY uq_news_crawl_state_source_keyword (api_source, search_keyword)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS news_duplicate_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    cluster_id BIGINT NOT NULL,
    representative_article_id BIGINT NULL,
    api_source VARCHAR(100) NOT NULL,
    search_keyword VARCHAR(255) NOT NULL,
    duplicate_external_article_id VARCHAR(255),
    duplicate_title TEXT,
    duplicate_url TEXT,
    duplicate_published_at DATETIME,
    similarity_score DECIMAL(6, 4),
    duplicate_reason VARCHAR(100),
    raw_payload JSON,
    detected_at DATETIME,
    KEY idx_news_duplicate_logs_cluster_id (cluster_id),
    KEY idx_news_duplicate_logs_external_id (api_source, duplicate_external_article_id),
    CONSTRAINT fk_news_duplicate_logs_cluster
        FOREIGN KEY (cluster_id) REFERENCES news_clusters(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_news_duplicate_logs_representative_article
        FOREIGN KEY (representative_article_id) REFERENCES articles(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
