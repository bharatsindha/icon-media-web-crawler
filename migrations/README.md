# Database Migrations

This directory contains all database migration scripts for the web crawler project.

## Migration Files

### Current Migrations

1. **001_create_tables.sql** / **001_create_tables_down.sql**
   - Creates complete database schema
   - Tables: companies, section_types, keywords_master, domain_keywords, crawl_jobs
   - Indexes on all critical columns
   - Views for common queries
   - Triggers for automatic timestamp updates

2. **002_seed_data.sql** / **002_seed_data_down.sql**
   - Seeds initial reference data
   - Inserts section_types: 'menu'
   - Data validation

## File Naming Convention

Migrations follow this naming pattern:
```
NNN_description.sql        # Migration (up)
NNN_description_down.sql   # Rollback (down)
```

Where:
- `NNN` = Sequential number with leading zeros (001, 002, etc.)
- `description` = Snake_case description of changes
- `_down` suffix = Rollback script

## Migration Management

Use the `migrate.py` script in the project root:

```bash
# Show current status
python migrate.py status

# Run all pending migrations
python migrate.py up

# Run specific number of migrations
python migrate.py up --steps=1

# Rollback last migration
python migrate.py down --steps=1

# Rollback all and re-run
python migrate.py reset

# Create new migration
python migrate.py create "add_new_table"
```

## Creating New Migrations

### Method 1: Using migrate.py (Recommended)

```bash
python migrate.py create "add_footer_section_type"
```

This automatically creates:
- `003_add_footer_section_type.sql`
- `003_add_footer_section_type_down.sql`

### Method 2: Manual Creation

1. Find the next number in sequence
2. Create both up and down files
3. Follow the naming convention
4. Add descriptive comments
5. Test locally before committing

## Migration Best Practices

### DO

- ✓ Make migrations idempotent (use IF NOT EXISTS, ON CONFLICT, etc.)
- ✓ Add comments explaining complex changes
- ✓ Test both up and down migrations
- ✓ Include RAISE NOTICE messages for visibility
- ✓ Add validation checks
- ✓ Keep migrations small and focused
- ✓ Always create a matching rollback (down) migration

### DON'T

- ✗ Modify existing migration files after they've been applied
- ✗ Delete migration files
- ✗ Skip sequence numbers
- ✗ Mix schema changes with data changes (use separate migrations)
- ✗ Reference application code or external files
- ✗ Make destructive changes without backups

## Migration Structure Template

### Up Migration (XXX_description.sql)

```sql
-- Migration: XXX_description.sql
-- Description: Brief description of changes
-- Date: YYYY-MM-DD

-- Your SQL changes here
CREATE TABLE IF NOT EXISTS example (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

-- Validation
DO $$
BEGIN
    -- Add validation checks
    RAISE NOTICE 'Migration XXX_description.sql completed successfully';
END $$;
```

### Down Migration (XXX_description_down.sql)

```sql
-- Rollback: XXX_description_down.sql
-- Description: Rollback for XXX_description
-- Date: YYYY-MM-DD

-- Your rollback SQL here
DROP TABLE IF EXISTS example;

-- Confirmation
DO $$
BEGIN
    RAISE NOTICE 'Rollback XXX_description_down.sql completed successfully';
END $$;
```

## Testing Migrations

### Local Testing

```bash
# 1. Apply migration
python migrate.py up --steps=1

# 2. Verify changes
python migrate.py status
python check_status.py stats

# 3. Test rollback
python migrate.py down --steps=1

# 4. Verify rollback
python migrate.py status

# 5. Re-apply
python migrate.py up --steps=1
```

### Validation Checklist

- [ ] Migration runs without errors
- [ ] Rollback runs without errors
- [ ] Can re-apply after rollback
- [ ] Indexes are created correctly
- [ ] Foreign keys work as expected
- [ ] Data integrity is maintained
- [ ] Performance is acceptable
- [ ] No data loss in rollback (if applicable)

## Common Migration Patterns

### Adding a Column

```sql
-- Up
ALTER TABLE companies
ADD COLUMN IF NOT EXISTS new_field VARCHAR(255);

-- Down
ALTER TABLE companies
DROP COLUMN IF EXISTS new_field;
```

### Adding an Index

```sql
-- Up
CREATE INDEX IF NOT EXISTS idx_companies_new_field
ON companies(new_field);

-- Down
DROP INDEX IF EXISTS idx_companies_new_field;
```

### Adding a Table

```sql
-- Up
CREATE TABLE IF NOT EXISTS new_table (
    id SERIAL PRIMARY KEY,
    company_id BIGINT REFERENCES companies(id) ON DELETE CASCADE
);

-- Down
DROP TABLE IF EXISTS new_table CASCADE;
```

### Modifying Data

```sql
-- Up
UPDATE companies
SET crawl_status = 'pending'
WHERE crawl_status IS NULL;

-- Down (if reversible)
-- Note: Data modifications may not be reversible
-- Consider creating a backup or audit table
```

## Migration Tracking

Migrations are tracked in the `schema_migrations` table:

```sql
SELECT * FROM schema_migrations ORDER BY applied_at DESC;
```

Columns:
- `id` - Auto-incrementing ID
- `migration` - Migration filename
- `applied_at` - When it was applied
- `execution_time_ms` - How long it took
- `checksum` - File integrity check

## Troubleshooting

### Migration Stuck or Failed

```bash
# Check status
python migrate.py status

# Reset and try again
python migrate.py down --steps=1
python migrate.py up --steps=1
```

### Manual Intervention Required

If a migration fails and leaves the database in a bad state:

1. Connect to database: `psql -h localhost -U user -d database`
2. Check current state: `SELECT * FROM schema_migrations;`
3. Manually fix issues
4. Update migration tracking if needed
5. Re-run migration

### Force Migration Record

Only in emergency situations:

```sql
-- Mark migration as applied (without running it)
INSERT INTO schema_migrations (migration, applied_at)
VALUES ('XXX_migration_name.sql', CURRENT_TIMESTAMP);

-- Remove migration record
DELETE FROM schema_migrations
WHERE migration = 'XXX_migration_name.sql';
```

## Production Deployment

### Pre-Deployment

1. Test all migrations on staging environment
2. Create database backup
3. Review migration execution time
4. Plan for rollback if needed
5. Schedule maintenance window if necessary

### Deployment Steps

```bash
# 1. Backup database
pg_dump -h localhost -U user database > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Check migration status
python migrate.py status

# 3. Apply migrations
python migrate.py up

# 4. Verify
python check_status.py stats
```

### Post-Deployment

1. Verify all migrations applied successfully
2. Run smoke tests
3. Monitor application logs
4. Check database performance
5. Keep backup for 30 days

## Version Control

### Git Workflow

```bash
# Create migration
python migrate.py create "add_new_feature"

# Add to git
git add migrations/003_add_new_feature*.sql

# Commit
git commit -m "Add migration for new feature"

# Push
git push
```

### Never

- Don't modify migrations after they're merged
- Don't delete migration files
- Don't reorder migrations

## Support

For migration issues:
1. Check logs in `logs/` directory
2. Review migration SQL for errors
3. Consult [README.md](../README.md) for configuration
4. Check database permissions
5. Verify PostgreSQL version compatibility (12+)

## Additional Resources

- Main documentation: [README.md](../README.md)
- Quick start guide: [QUICKSTART.md](../QUICKSTART.md)
- Migration script: [migrate.py](../migrate.py)
- Database operations: [database.py](../database.py)
