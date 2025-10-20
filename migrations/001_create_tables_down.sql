-- Rollback Migration: 001_create_tables_down.sql
-- Description: Rollback schema creation for web crawler
-- Author: Web Crawler Team
-- Date: 2025-10-20

-- WARNING: This will drop all tables and data!

-- =============================================================================
-- DROP VIEWS
-- =============================================================================

DROP VIEW IF EXISTS v_recent_crawl_jobs;
DROP VIEW IF EXISTS v_top_keywords;
DROP VIEW IF EXISTS v_crawl_statistics;
DROP VIEW IF EXISTS v_pending_companies;

-- =============================================================================
-- DROP TRIGGERS
-- =============================================================================

DROP TRIGGER IF EXISTS trigger_companies_updated_at ON companies;
DROP FUNCTION IF EXISTS update_updated_at_column();

-- =============================================================================
-- DROP TABLES (in reverse order of dependencies)
-- =============================================================================

DROP TABLE IF EXISTS crawl_jobs CASCADE;
DROP TABLE IF EXISTS domain_keywords CASCADE;
DROP TABLE IF EXISTS keywords_master CASCADE;
DROP TABLE IF EXISTS section_types CASCADE;
DROP TABLE IF EXISTS companies CASCADE;

-- =============================================================================
-- DROP EXTENSIONS (optional - only if not used elsewhere)
-- =============================================================================

-- DROP EXTENSION IF EXISTS "uuid-ossp";

-- =============================================================================
-- ROLLBACK COMPLETE
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Rollback 001_create_tables_down.sql completed successfully';
    RAISE NOTICE 'All tables, views, triggers, and functions have been dropped';
END $$;
