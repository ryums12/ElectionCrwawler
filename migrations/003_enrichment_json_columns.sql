-- PostgreSQL/Supabase note:
-- Enrichment metadata columns are JSONB in 001_create_news_tables.sql and
-- postgresql_integrated_news_schema.sql. This no-op keeps the historical
-- migration sequence directly executable in PostgreSQL.
SELECT 1;
