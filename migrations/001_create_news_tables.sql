CREATE TABLE IF NOT EXISTS news_clusters (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    representative_article_id BIGINT,
    representative_title TEXT,
    representative_summary TEXT,
    main_keywords TEXT,
    parties TEXT,
    regions TEXT,
    people TEXT,
    created_at DATETIME,
    updated_at DATETIME
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS articles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    source VARCHAR(100),
    search_keyword VARCHAR(255),
    original_url TEXT,
    original_url_hash CHAR(64),
    canonical_url TEXT,
    canonical_url_hash CHAR(64),
    title TEXT,
    normalized_title TEXT,
    title_hash CHAR(64),
    content_hash CHAR(64),
    body TEXT,
    summary TEXT,
    published_at DATETIME,
    crawled_at DATETIME,
    cluster_id BIGINT,
    duplicate_of BIGINT NULL,
    UNIQUE KEY uq_articles_canonical_url_hash (canonical_url_hash),
    KEY idx_articles_published_at (published_at),
    KEY idx_articles_crawled_at (crawled_at),
    KEY idx_articles_title_hash (title_hash),
    KEY idx_articles_content_hash (content_hash),
    KEY idx_articles_cluster_id (cluster_id),
    KEY idx_articles_duplicate_of (duplicate_of),
    CONSTRAINT fk_articles_cluster
        FOREIGN KEY (cluster_id) REFERENCES news_clusters(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_articles_duplicate_of
        FOREIGN KEY (duplicate_of) REFERENCES articles(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
