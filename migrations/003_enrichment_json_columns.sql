UPDATE articles
SET main_keywords = JSON_ARRAY(main_keywords)
WHERE main_keywords IS NOT NULL AND JSON_VALID(main_keywords) = 0;

UPDATE articles
SET parties = JSON_ARRAY(parties)
WHERE parties IS NOT NULL AND JSON_VALID(parties) = 0;

UPDATE articles
SET regions = JSON_ARRAY(regions)
WHERE regions IS NOT NULL AND JSON_VALID(regions) = 0;

UPDATE articles
SET people = JSON_ARRAY(people)
WHERE people IS NOT NULL AND JSON_VALID(people) = 0;

UPDATE news_clusters
SET main_keywords = JSON_ARRAY(main_keywords)
WHERE main_keywords IS NOT NULL AND JSON_VALID(main_keywords) = 0;

UPDATE news_clusters
SET parties = JSON_ARRAY(parties)
WHERE parties IS NOT NULL AND JSON_VALID(parties) = 0;

UPDATE news_clusters
SET regions = JSON_ARRAY(regions)
WHERE regions IS NOT NULL AND JSON_VALID(regions) = 0;

UPDATE news_clusters
SET people = JSON_ARRAY(people)
WHERE people IS NOT NULL AND JSON_VALID(people) = 0;

ALTER TABLE articles
    MODIFY COLUMN main_keywords JSON NULL,
    MODIFY COLUMN parties JSON NULL,
    MODIFY COLUMN regions JSON NULL,
    MODIFY COLUMN people JSON NULL;

ALTER TABLE news_clusters
    MODIFY COLUMN main_keywords JSON NULL,
    MODIFY COLUMN parties JSON NULL,
    MODIFY COLUMN regions JSON NULL,
    MODIFY COLUMN people JSON NULL;
