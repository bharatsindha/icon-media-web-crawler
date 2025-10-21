-- Migration: Add precise service extraction support
-- Description: Adds service_detail and service_listing section types, plus source URL tracking

-- Add new section types for precise service extraction
INSERT INTO section_types (code, name, description)
VALUES
    ('service_detail', 'Service Detail Pages', 'Keywords from individual service/solution pages via H1 and meta tags'),
    ('service_listing', 'Service Listing Pages', 'Keywords from main services hub pages')
ON CONFLICT (code) DO NOTHING;

-- Add source URL tracking to domain_keywords table
ALTER TABLE domain_keywords ADD COLUMN IF NOT EXISTS source_url VARCHAR(500);
ALTER TABLE domain_keywords ADD COLUMN IF NOT EXISTS extraction_method VARCHAR(50);
ALTER TABLE domain_keywords ADD COLUMN IF NOT EXISTS confidence_score NUMERIC(3,2);

-- Create index on source_url for faster queries
CREATE INDEX IF NOT EXISTS idx_domain_keywords_source_url ON domain_keywords(source_url);

-- Display all section types
SELECT code, name, description FROM section_types ORDER BY created_at;
