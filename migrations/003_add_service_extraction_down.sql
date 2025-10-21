-- Rollback: Remove service extraction support
-- Description: Removes service_detail and service_listing section types and source tracking columns

-- Remove indexes
DROP INDEX IF EXISTS idx_domain_keywords_source_url;

-- Remove columns from domain_keywords
ALTER TABLE domain_keywords DROP COLUMN IF EXISTS source_url;
ALTER TABLE domain_keywords DROP COLUMN IF EXISTS extraction_method;
ALTER TABLE domain_keywords DROP COLUMN IF EXISTS confidence_score;

-- Delete section types (will cascade delete domain_keywords entries)
DELETE FROM section_types WHERE code IN ('service_detail', 'service_listing');

-- Display remaining section types
SELECT code, name, description FROM section_types ORDER BY created_at;
