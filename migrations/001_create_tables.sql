-- Migration: 001_create_tables.sql
-- Description: Create initial database schema for web crawler
-- Author: Web Crawler Team
-- Date: 2025-10-20

-- Enable UUID extension for crawl_jobs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- TABLE: companies
-- Description: Stores domains to be crawled with their crawl status
-- =============================================================================

CREATE TABLE IF NOT EXISTS companies (
    id BIGSERIAL PRIMARY KEY,
    domain VARCHAR(255) UNIQUE NOT NULL,
    last_crawled TIMESTAMP,
    next_crawl_date TIMESTAMP,
    crawl_status VARCHAR(50) DEFAULT 'pending' NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Constraints
    CONSTRAINT companies_domain_check CHECK (domain <> ''),
    CONSTRAINT companies_crawl_status_check CHECK (
        crawl_status IN ('pending', 'in_progress', 'completed', 'failed', 'paused')
    )
);

-- Indexes for companies table
CREATE INDEX IF NOT EXISTS idx_companies_domain ON companies(domain);
CREATE INDEX IF NOT EXISTS idx_companies_crawl_status ON companies(crawl_status);
CREATE INDEX IF NOT EXISTS idx_companies_is_active ON companies(is_active);
CREATE INDEX IF NOT EXISTS idx_companies_next_crawl_date ON companies(next_crawl_date);
CREATE INDEX IF NOT EXISTS idx_companies_status_active ON companies(crawl_status, is_active);

-- Comments for companies table
COMMENT ON TABLE companies IS 'Stores domains to be crawled with their status and metadata';
COMMENT ON COLUMN companies.domain IS 'Domain name without protocol (e.g., example.com)';
COMMENT ON COLUMN companies.crawl_status IS 'Current crawl status: pending, in_progress, completed, failed, paused';
COMMENT ON COLUMN companies.last_crawled IS 'Timestamp of last successful crawl';
COMMENT ON COLUMN companies.next_crawl_date IS 'Scheduled date for next crawl';
COMMENT ON COLUMN companies.is_active IS 'Whether this domain is active for crawling';

-- =============================================================================
-- TABLE: section_types
-- Description: Categorizes different types of content sections
-- =============================================================================

CREATE TABLE IF NOT EXISTS section_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Constraints
    CONSTRAINT section_types_code_check CHECK (code <> ''),
    CONSTRAINT section_types_name_check CHECK (name <> '')
);

-- Index for section_types table
CREATE INDEX IF NOT EXISTS idx_section_types_code ON section_types(code);

-- Comments for section_types table
COMMENT ON TABLE section_types IS 'Defines types of content sections that can be crawled';
COMMENT ON COLUMN section_types.code IS 'Unique code identifier (e.g., menu, footer, header)';
COMMENT ON COLUMN section_types.name IS 'Human-readable name';
COMMENT ON COLUMN section_types.description IS 'Description of what this section type represents';

-- =============================================================================
-- TABLE: keywords_master
-- Description: Global master list of unique keywords with statistics
-- =============================================================================

CREATE TABLE IF NOT EXISTS keywords_master (
    id BIGSERIAL PRIMARY KEY,
    keyword VARCHAR(255) NOT NULL,
    normalized_keyword VARCHAR(255) NOT NULL,
    unique_domains_count INTEGER DEFAULT 0 NOT NULL,
    total_occurrences BIGINT DEFAULT 0 NOT NULL,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Constraints
    CONSTRAINT keywords_master_keyword_check CHECK (keyword <> ''),
    CONSTRAINT keywords_master_normalized_check CHECK (normalized_keyword <> ''),
    CONSTRAINT keywords_master_unique_domains_check CHECK (unique_domains_count >= 0),
    CONSTRAINT keywords_master_total_occurrences_check CHECK (total_occurrences >= 0),
    CONSTRAINT keywords_master_normalized_unique UNIQUE (normalized_keyword)
);

-- Indexes for keywords_master table
CREATE INDEX IF NOT EXISTS idx_keywords_master_normalized ON keywords_master(normalized_keyword);
CREATE INDEX IF NOT EXISTS idx_keywords_master_unique_domains ON keywords_master(unique_domains_count DESC);
CREATE INDEX IF NOT EXISTS idx_keywords_master_total_occurrences ON keywords_master(total_occurrences DESC);
CREATE INDEX IF NOT EXISTS idx_keywords_master_last_seen ON keywords_master(last_seen DESC);

-- Comments for keywords_master table
COMMENT ON TABLE keywords_master IS 'Global master list of unique keywords found across all domains';
COMMENT ON COLUMN keywords_master.keyword IS 'Original keyword text';
COMMENT ON COLUMN keywords_master.normalized_keyword IS 'Normalized version (lowercase, trimmed, no special chars)';
COMMENT ON COLUMN keywords_master.unique_domains_count IS 'Number of unique domains where this keyword appears';
COMMENT ON COLUMN keywords_master.total_occurrences IS 'Total number of times this keyword has been seen';
COMMENT ON COLUMN keywords_master.first_seen IS 'When this keyword was first discovered';
COMMENT ON COLUMN keywords_master.last_seen IS 'When this keyword was last seen';

-- =============================================================================
-- TABLE: domain_keywords
-- Description: Links keywords to specific domains and section types
-- =============================================================================

CREATE TABLE IF NOT EXISTS domain_keywords (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL,
    keyword_id BIGINT NOT NULL,
    section_type_id INTEGER NOT NULL,
    page_count INTEGER DEFAULT 1 NOT NULL,
    total_frequency INTEGER DEFAULT 1 NOT NULL,
    avg_score NUMERIC(5,3),
    max_score NUMERIC(5,3),
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Foreign Keys
    CONSTRAINT fk_domain_keywords_company
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    CONSTRAINT fk_domain_keywords_keyword
        FOREIGN KEY (keyword_id) REFERENCES keywords_master(id) ON DELETE CASCADE,
    CONSTRAINT fk_domain_keywords_section
        FOREIGN KEY (section_type_id) REFERENCES section_types(id) ON DELETE RESTRICT,

    -- Constraints
    CONSTRAINT domain_keywords_page_count_check CHECK (page_count > 0),
    CONSTRAINT domain_keywords_total_frequency_check CHECK (total_frequency > 0),
    CONSTRAINT domain_keywords_avg_score_check CHECK (avg_score IS NULL OR (avg_score >= 0 AND avg_score <= 100)),
    CONSTRAINT domain_keywords_max_score_check CHECK (max_score IS NULL OR (max_score >= 0 AND max_score <= 100)),
    CONSTRAINT domain_keywords_unique_combination UNIQUE (company_id, keyword_id, section_type_id)
);

-- Indexes for domain_keywords table
CREATE INDEX IF NOT EXISTS idx_domain_keywords_company ON domain_keywords(company_id);
CREATE INDEX IF NOT EXISTS idx_domain_keywords_keyword ON domain_keywords(keyword_id);
CREATE INDEX IF NOT EXISTS idx_domain_keywords_section ON domain_keywords(section_type_id);
CREATE INDEX IF NOT EXISTS idx_domain_keywords_combination ON domain_keywords(company_id, keyword_id, section_type_id);
CREATE INDEX IF NOT EXISTS idx_domain_keywords_frequency ON domain_keywords(total_frequency DESC);
CREATE INDEX IF NOT EXISTS idx_domain_keywords_last_seen ON domain_keywords(last_seen DESC);

-- Comments for domain_keywords table
COMMENT ON TABLE domain_keywords IS 'Links keywords to specific domains and tracks frequency statistics';
COMMENT ON COLUMN domain_keywords.company_id IS 'Reference to the company/domain';
COMMENT ON COLUMN domain_keywords.keyword_id IS 'Reference to the keyword in master table';
COMMENT ON COLUMN domain_keywords.section_type_id IS 'Type of section where keyword was found';
COMMENT ON COLUMN domain_keywords.page_count IS 'Number of pages where this keyword appears';
COMMENT ON COLUMN domain_keywords.total_frequency IS 'Total times this keyword appears across all pages';
COMMENT ON COLUMN domain_keywords.avg_score IS 'Average relevance/importance score';
COMMENT ON COLUMN domain_keywords.max_score IS 'Maximum relevance/importance score';

-- =============================================================================
-- TABLE: crawl_jobs
-- Description: Tracks individual crawl job execution and results
-- =============================================================================

CREATE TABLE IF NOT EXISTS crawl_jobs (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT,
    job_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    pages_crawled INTEGER DEFAULT 0 NOT NULL,
    pages_failed INTEGER DEFAULT 0 NOT NULL,
    new_keywords_found INTEGER DEFAULT 0 NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Foreign Keys
    CONSTRAINT fk_crawl_jobs_company
        FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT crawl_jobs_status_check CHECK (
        status IN ('queued', 'running', 'completed', 'failed', 'cancelled')
    ),
    CONSTRAINT crawl_jobs_pages_crawled_check CHECK (pages_crawled >= 0),
    CONSTRAINT crawl_jobs_pages_failed_check CHECK (pages_failed >= 0),
    CONSTRAINT crawl_jobs_new_keywords_check CHECK (new_keywords_found >= 0)
);

-- Indexes for crawl_jobs table
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_company ON crawl_jobs(company_id);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_status ON crawl_jobs(status);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_job_id ON crawl_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_created_at ON crawl_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_completed_at ON crawl_jobs(completed_at DESC);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_status_created ON crawl_jobs(status, created_at DESC);

-- Comments for crawl_jobs table
COMMENT ON TABLE crawl_jobs IS 'Tracks individual crawl job execution, status, and results';
COMMENT ON COLUMN crawl_jobs.company_id IS 'Reference to the company being crawled';
COMMENT ON COLUMN crawl_jobs.job_id IS 'Unique UUID for this job';
COMMENT ON COLUMN crawl_jobs.status IS 'Job status: queued, running, completed, failed, cancelled';
COMMENT ON COLUMN crawl_jobs.started_at IS 'When the job started executing';
COMMENT ON COLUMN crawl_jobs.completed_at IS 'When the job finished (success or failure)';
COMMENT ON COLUMN crawl_jobs.pages_crawled IS 'Number of pages successfully crawled';
COMMENT ON COLUMN crawl_jobs.pages_failed IS 'Number of pages that failed to crawl';
COMMENT ON COLUMN crawl_jobs.new_keywords_found IS 'Number of new keywords discovered in this job';
COMMENT ON COLUMN crawl_jobs.error_message IS 'Error message if job failed';

-- =============================================================================
-- TRIGGERS
-- Description: Automatic timestamp updates
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for companies table
DROP TRIGGER IF EXISTS trigger_companies_updated_at ON companies;
CREATE TRIGGER trigger_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VIEWS
-- Description: Useful views for common queries
-- =============================================================================

-- View: Active pending companies
CREATE OR REPLACE VIEW v_pending_companies AS
SELECT
    id,
    domain,
    crawl_status,
    last_crawled,
    next_crawl_date,
    created_at
FROM companies
WHERE crawl_status = 'pending'
  AND is_active = true
ORDER BY created_at ASC;

COMMENT ON VIEW v_pending_companies IS 'Active companies waiting to be crawled';

-- View: Crawl statistics summary
CREATE OR REPLACE VIEW v_crawl_statistics AS
SELECT
    COUNT(*) FILTER (WHERE crawl_status = 'pending') as pending_count,
    COUNT(*) FILTER (WHERE crawl_status = 'in_progress') as in_progress_count,
    COUNT(*) FILTER (WHERE crawl_status = 'completed') as completed_count,
    COUNT(*) FILTER (WHERE crawl_status = 'failed') as failed_count,
    COUNT(*) FILTER (WHERE crawl_status = 'paused') as paused_count,
    COUNT(*) as total_companies,
    COUNT(*) FILTER (WHERE is_active = true) as active_companies
FROM companies;

COMMENT ON VIEW v_crawl_statistics IS 'Summary statistics of crawl status across all companies';

-- View: Top keywords by domain count
CREATE OR REPLACE VIEW v_top_keywords AS
SELECT
    km.id,
    km.keyword,
    km.normalized_keyword,
    km.unique_domains_count,
    km.total_occurrences,
    km.last_seen
FROM keywords_master km
ORDER BY km.unique_domains_count DESC, km.total_occurrences DESC
LIMIT 1000;

COMMENT ON VIEW v_top_keywords IS 'Top 1000 keywords by domain count and occurrences';

-- View: Recent crawl jobs
CREATE OR REPLACE VIEW v_recent_crawl_jobs AS
SELECT
    cj.job_id,
    c.domain,
    cj.status,
    cj.pages_crawled,
    cj.pages_failed,
    cj.new_keywords_found,
    cj.started_at,
    cj.completed_at,
    cj.error_message,
    EXTRACT(EPOCH FROM (cj.completed_at - cj.started_at)) as duration_seconds
FROM crawl_jobs cj
LEFT JOIN companies c ON c.id = cj.company_id
ORDER BY cj.created_at DESC
LIMIT 100;

COMMENT ON VIEW v_recent_crawl_jobs IS 'Most recent 100 crawl jobs with details';

-- =============================================================================
-- GRANT PERMISSIONS (Optional - uncomment and modify as needed)
-- =============================================================================

-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO crawler_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO crawler_user;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO crawler_readonly;

-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================

-- Add migration completion marker
DO $$
BEGIN
    RAISE NOTICE 'Migration 001_create_tables.sql completed successfully';
END $$;
