# Web Crawler - Navigation Menu Extractor

A production-ready Python web crawler that extracts navigation menu items from websites and stores them in PostgreSQL with intelligent deduplication.

## Features

- **Sequential Processing**: Processes domains one at a time from the companies table
- **Multi-Method Detection**: Extracts menu items using:
  - CSS selectors (nav, .menu, #menu, etc.)
  - HTML5 semantic tags (`<nav>`, `<menu>`)
  - ARIA attributes (role="navigation")
  - Common naming patterns
- **Robust Error Handling**: Handles network timeouts, SSL errors, invalid URLs, and robots.txt
- **Smart Deduplication**: Normalizes and deduplicates keywords across domains
- **Production-Ready**:
  - Connection pooling
  - Rate limiting (1-2s delay between requests)
  - Resume capability
  - Graceful shutdown
  - Comprehensive logging
  - Progress tracking

## Database Schema

The crawler uses 5 main tables:

1. **companies** - Stores domains with crawl status tracking
2. **section_types** - Categorizes content sections (currently 'menu')
3. **keywords_master** - Global unique keywords with statistics
4. **domain_keywords** - Links keywords to domains with frequency data
5. **crawl_jobs** - Tracks individual crawl job execution

## Installation

### Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher
- pip

### Setup

1. Clone the repository:
```bash
cd /opt/homebrew/var/www/html/web_crawler
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your database credentials and settings
```

5. Run database migrations:
```bash
python migrate.py up
```

This will create all required tables and seed initial data.

## Database Migrations

The project uses a migration system to manage database schema changes.

### Migration Commands

```bash
# Show migration status
python migrate.py status

# Run all pending migrations
python migrate.py up

# Run specific number of migrations
python migrate.py up --steps=1

# Rollback last migration
python migrate.py down --steps=1

# Reset database (rollback all and re-run)
python migrate.py reset

# Create new migration
python migrate.py create "add_new_field"
```

### Available Migrations

1. **001_create_tables.sql** - Creates all database tables, indexes, and views
   - companies table with crawl status tracking
   - section_types for content categorization
   - keywords_master for global keyword storage
   - domain_keywords for domain-keyword relationships
   - crawl_jobs for job tracking
   - Indexes on all foreign keys and frequently queried columns
   - Helper views for common queries

2. **002_seed_data.sql** - Seeds initial data
   - Inserts section_types ('menu')
   - Validates seeded data

### Migration Files

Migrations are stored in the `migrations/` directory:
```
migrations/
├── 001_create_tables.sql      # Schema creation
├── 002_seed_data.sql           # Initial data
└── [future migrations]
```

### Creating Custom Migrations

To create a new migration:
```bash
python migrate.py create "description_of_change"
```

This creates two files:
- `XXX_description_of_change.sql` - The migration (up)
- `XXX_description_of_change_down.sql` - The rollback (down)

Edit these files to add your SQL changes, then run:
```bash
python migrate.py up
```

### Migration Tracking

Migrations are tracked in the `schema_migrations` table, which records:
- Migration name
- When it was applied
- Execution time
- Checksum (for integrity)

## Configuration

Edit the `.env` file to customize:

### Database Settings
- `DB_HOST`: PostgreSQL host (default: localhost)
- `DB_PORT`: PostgreSQL port (default: 5432)
- `DB_NAME`: Database name
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password
- `DB_MIN_CONN`: Minimum connections in pool (default: 2)
- `DB_MAX_CONN`: Maximum connections in pool (default: 10)

### Crawler Settings
- `REQUEST_TIMEOUT`: HTTP request timeout in seconds (default: 30)
- `RATE_LIMIT_MIN`: Minimum delay between requests (default: 1.0)
- `RATE_LIMIT_MAX`: Maximum delay between requests (default: 2.0)
- `MAX_RETRIES`: Number of retry attempts (default: 3)
- `RESPECT_ROBOTS_TXT`: Respect robots.txt (default: true)
- `VERIFY_SSL`: Verify SSL certificates (default: true)

### Logging Settings
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_DIR`: Directory for log files (default: logs)
- `LOG_TO_CONSOLE`: Log to console (default: true)
- `LOG_TO_FILE`: Log to daily files (default: true)

## Usage

### Adding Domains to Crawl

#### Method 1: Command Line / Text File (Small batches)

Use `add_domains.py` for adding a few domains:

```bash
# Add domains from command line
python add_domains.py example.com google.com github.com

# Add domains from a text file
python add_domains.py -f domains.txt
```

The `domains.txt` file should contain one domain per line:
```
example.com
github.com
stackoverflow.com
wikipedia.org
```

#### Method 2: CSV Import (Large batches - Recommended)

Use `import_companies.py` for importing hundreds or thousands of domains from CSV files:

```bash
# Basic import with auto-header detection
python import_companies.py -f domains.csv

# Dry run to preview without importing
python import_companies.py -f domains.csv --dry-run

# Import from specific column
python import_companies.py -f domains.csv --column domain

# Update existing domains to pending status
python import_companies.py -f domains.csv --update-existing

# High-performance batch import
python import_companies.py -f large_domains.csv --batch-size 5000
```

CSV format options:
```csv
# Simple format with header
domain
example.com
github.com

# Multi-column format
company,domain,status
Example Inc,example.com,active
GitHub,github.com,active
```

See [examples/](examples/) directory for sample CSV files.

**Features:**
- Auto-detects CSV header
- Validates and normalizes domains
- Batch inserts for performance
- Handles duplicates gracefully
- Dry-run mode for testing
- Detailed import summary

### Basic Usage

Run the crawler:
```bash
python main.py
```

The crawler will:
1. Check for pending domains in the companies table
2. Process each domain sequentially
3. Extract navigation menu items
4. Store normalized keywords in the database
5. Update crawl status and statistics
6. Log all activity

### Graceful Shutdown

Press `Ctrl+C` to initiate graceful shutdown. The crawler will:
- Complete the current domain being processed
- Update all database records
- Clean up resources
- Exit cleanly

### Resume Capability

The crawler automatically resumes from where it left off:
- Domains with `crawl_status = 'pending'` will be processed
- Stuck jobs (in_progress > 1 hour) are automatically reset to pending

## Project Structure

```
web_crawler/
├── main.py              # Entry point with graceful shutdown
├── crawler.py           # Main crawling logic
├── parser.py            # HTML parsing and menu extraction
├── database.py          # Database operations with connection pooling
├── utils.py             # Utility functions (normalization, rate limiting)
├── config.py            # Configuration management
├── migrate.py           # Database migration manager
├── add_domains.py       # Add domains via CLI or text file
├── import_companies.py  # Import domains from CSV files (bulk)
├── check_status.py      # Status monitoring and statistics
├── cleanup_db.py        # Database cleanup utility
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── .env                 # Your local configuration (not in git)
├── .gitignore           # Git ignore rules
├── QUICKSTART.md        # Quick start guide
├── INSTALL.md           # Installation instructions
├── migrations/          # Database migration scripts
│   ├── 001_create_tables.sql
│   ├── 001_create_tables_down.sql
│   ├── 002_seed_data.sql
│   ├── 002_seed_data_down.sql
│   └── README.md
├── examples/            # Sample CSV files for import
│   ├── domains_simple.csv
│   ├── domains_no_header.csv
│   ├── domains_multi_column.csv
│   ├── domains_mixed.csv
│   └── README.md
├── logs/                # Log files (created automatically)
└── README.md            # This file
```

## Menu Detection Methods

The parser uses multiple methods to find navigation menus:

### CSS Selectors
- `nav`, `.nav`, `#nav`
- `.menu`, `#menu`
- `.navigation`, `#navigation`
- `.navbar`, `.main-menu`, `.primary-menu`
- `header nav`, `.site-navigation`

### HTML5 Semantic Tags
- `<nav>`
- `<menu>`

### ARIA Attributes
- `role="navigation"`
- `role="menubar"`
- `aria-label="navigation"`

### Common Patterns
- Elements with classes/IDs containing: menu, nav, navigation, navbar, menubar

## Keyword Normalization

Keywords are normalized using:
- Lowercase conversion
- Special character removal (keeping spaces, hyphens, underscores)
- Whitespace trimming and consolidation
- Deduplication by normalized form

## Error Handling

The crawler handles:
- **Network Errors**: Timeout, connection failures
- **SSL Errors**: Certificate validation issues
- **HTTP Errors**: 4xx and 5xx status codes
- **Robots.txt**: Respects crawling permissions
- **Invalid URLs**: Validates before crawling
- **Database Errors**: Transaction rollback and logging
- **JavaScript Sites**: Best-effort extraction from static HTML

## Logging

Logs are written to:
- **Console**: Real-time output (if enabled)
- **Files**: Daily rotation in `logs/crawler_YYYY-MM-DD.log`

Log format:
```
2025-10-20 10:30:45 - module_name - LEVEL - message
```

## Performance Considerations

For millions of domains:
- **Connection Pooling**: Reuses database connections (2-10 concurrent)
- **Rate Limiting**: Random delay (1-2s) between requests
- **Sequential Processing**: One domain at a time (configurable)
- **Batch Operations**: Efficient keyword storage
- **Index Optimization**: Database constraints and unique indexes
- **Progress Tracking**: Monitor performance in real-time

## Database Statistics

View crawler statistics:
```python
from database import DatabaseManager

db = DatabaseManager()
stats = db.get_statistics()
print(stats)
```

Returns:
```python
{
    'pending': 1000,
    'in_progress': 1,
    'completed': 500,
    'failed': 50,
    'paused': 0,
    'total': 1551,
    'total_keywords': 12500,
    'active_jobs': 1
}
```

## Monitoring

### Using check_status.py

The `check_status.py` utility provides comprehensive monitoring:

```bash
# Show all statistics
python check_status.py

# Show specific information
python check_status.py stats      # Crawler statistics
python check_status.py jobs       # Recent crawl jobs
python check_status.py keywords   # Top keywords
python check_status.py failed     # Failed domains
python check_status.py reset      # Reset stuck jobs
```

### Manual Monitoring

Monitor the crawler:
1. Check log files in `logs/` directory
2. Query database for statistics
3. Monitor `crawl_jobs` table for job status
4. Check `companies` table for crawl status
5. Use provided views: `v_pending_companies`, `v_crawl_statistics`, `v_top_keywords`, `v_recent_crawl_jobs`

## Troubleshooting

### No domains being crawled
- Check that companies have `crawl_status = 'pending'` and `is_active = true`
- Verify database connection settings in `.env`

### SSL errors
- Set `VERIFY_SSL=false` in `.env` (not recommended for production)
- Update certificates or use HTTP for testing

### Rate limiting issues
- Adjust `RATE_LIMIT_MIN` and `RATE_LIMIT_MAX` in `.env`
- Some sites may block requests; check User-Agent string

### Database connection errors
- Verify PostgreSQL is running
- Check credentials in `.env`
- Ensure database schema is created

## License

Proprietary - All rights reserved

## Support

For issues or questions, contact your system administrator.
