-- Migration: 002_seed_data.sql
-- Description: Seed initial data for web crawler
-- Author: Web Crawler Team
-- Date: 2025-10-20

-- =============================================================================
-- SECTION TYPES - Initial Data
-- Description: Predefined section types for content categorization
-- =============================================================================

-- Insert section types (using ON CONFLICT to make idempotent)
INSERT INTO section_types (code, name, description) VALUES
    ('menu', 'Navigation Menu', 'Main navigation and menu items')
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description;

-- Verify section types were inserted
DO $$
DECLARE
    section_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO section_count FROM section_types WHERE code = 'menu';

    IF section_count = 0 THEN
        RAISE EXCEPTION 'Failed to insert section_types data';
    END IF;

    RAISE NOTICE 'Section types seeded successfully: % rows', section_count;
END $$;

-- =============================================================================
-- SAMPLE DATA (Optional - for testing)
-- Description: Sample companies for testing the crawler
-- Uncomment to add sample domains for testing
-- =============================================================================

/*
-- Sample companies for testing
INSERT INTO companies (domain, crawl_status, is_active) VALUES
    ('example.com', 'pending', true),
    ('github.com', 'pending', true),
    ('stackoverflow.com', 'pending', true),
    ('wikipedia.org', 'pending', true),
    ('reddit.com', 'pending', true)
ON CONFLICT (domain) DO NOTHING;

RAISE NOTICE 'Sample companies added for testing';
*/

-- =============================================================================
-- DATA VALIDATION
-- Description: Validate seeded data
-- =============================================================================

DO $$
DECLARE
    menu_section_id INTEGER;
BEGIN
    -- Verify section_types
    SELECT id INTO menu_section_id FROM section_types WHERE code = 'menu';

    IF menu_section_id IS NULL THEN
        RAISE EXCEPTION 'Section type "menu" not found after seeding';
    END IF;

    RAISE NOTICE 'Data validation passed';
    RAISE NOTICE 'Section type "menu" has ID: %', menu_section_id;
END $$;

-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration 002_seed_data.sql completed successfully';
END $$;
