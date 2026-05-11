CREATE TABLE IF NOT EXISTS news_clusters (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    representative_article_id BIGINT NULL,
    search_keyword VARCHAR(255) NOT NULL,
    cluster_title TEXT,
    cluster_summary TEXT,
    normalized_title TEXT,
    normalized_description TEXT,
    title_hash CHAR(64),
    content_hash CHAR(64),
    main_keywords TEXT,
    parties TEXT,
    regions TEXT,
    people TEXT,
    first_published_at DATETIME,
    last_published_at DATETIME,
    article_count BIGINT NOT NULL DEFAULT 0,
    duplicate_count BIGINT NOT NULL DEFAULT 0,
    created_at DATETIME,
    updated_at DATETIME,
    KEY idx_news_clusters_representative_article_id (representative_article_id),
    KEY idx_news_clusters_title_hash (title_hash),
    KEY idx_news_clusters_content_hash (content_hash),
    KEY idx_news_clusters_first_published_at (first_published_at),
    KEY idx_news_clusters_last_published_at (last_published_at),
    KEY idx_news_clusters_keyword_last_published_at (search_keyword, last_published_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS articles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    api_source VARCHAR(100) NOT NULL,
    search_keyword VARCHAR(255) NOT NULL,
    title_raw TEXT,
    title TEXT,
    normalized_title TEXT,
    title_hash CHAR(64),
    description_raw TEXT,
    description TEXT,
    normalized_description TEXT,
    original_url TEXT,
    naver_url TEXT,
    canonical_url TEXT,
    canonical_url_hash CHAR(64),
    external_article_id VARCHAR(255) NOT NULL,
    source_name VARCHAR(255),
    published_at DATETIME,
    fetched_at DATETIME,
    raw_payload JSON,
    summary TEXT,
    main_keywords TEXT,
    parties TEXT,
    regions TEXT,
    people TEXT,
    content_hash CHAR(64),
    cluster_id BIGINT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_articles_api_external_id (api_source, external_article_id),
    UNIQUE KEY uq_articles_canonical_url_hash (canonical_url_hash),
    KEY idx_articles_title_hash (title_hash),
    KEY idx_articles_content_hash (content_hash),
    KEY idx_articles_published_at (published_at),
    KEY idx_articles_cluster_id (cluster_id),
    KEY idx_articles_keyword_published_at (search_keyword, published_at),
    CONSTRAINT fk_articles_cluster
        FOREIGN KEY (cluster_id) REFERENCES news_clusters(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
