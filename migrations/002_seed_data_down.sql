-- Rollback Migration: 002_seed_data_down.sql
-- Description: Rollback seed data for web crawler
-- Author: Web Crawler Team
-- Date: 2025-10-20

-- =============================================================================
-- DELETE SEEDED DATA
-- =============================================================================

-- Delete section types
DELETE FROM section_types WHERE code = 'menu';

-- Verify deletion
DO $$
DECLARE
    section_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO section_count FROM section_types WHERE code = 'menu';

    IF section_count > 0 THEN
        RAISE WARNING 'Section type "menu" still exists after rollback';
    ELSE
        RAISE NOTICE 'Section type "menu" deleted successfully';
    END IF;
END $$;

-- =============================================================================
-- ROLLBACK COMPLETE
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'Rollback 002_seed_data_down.sql completed successfully';
END $$;
