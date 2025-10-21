# Web Crawler - Business Keyword Extractor

A production-ready Python web crawler that extracts business keywords from websites using multiple precision methods and stores them in PostgreSQL with intelligent deduplication and source tracking.

## Features

### Multi-Section Extraction

- **Navigation Menu Extraction**: Traditional menu-based keyword extraction
  - CSS selectors (nav, .menu, #menu, etc.)
  - HTML5 semantic tags (`<nav>`, `<menu>`)
  - ARIA attributes (role="navigation")
  - Common naming patterns

- **Service Page Extraction** (NEW): High-precision service keyword extraction
  - Follows navigation links to dedicated service pages
  - Extracts from H1 tags (95% confidence)
  - Extracts from page titles (90% confidence)
  - Extracts from meta keywords (85% confidence)
  - Extracts from JSON-LD structured data (100% confidence)
  - Full source URL tracking for every keyword
  - Validates keywords with business term indicators
  - Achieves 100% accuracy by only extracting explicit service names

### Core Features

- **Sequential Processing**: Processes domains one at a time from the companies table
- **Smart Keyword Processing**:
  - Preserves original keywords with special characters (& / + @ # %)
  - Intelligent normalization (& → and, / → or, etc.)
  - Business-focused filtering (excludes navigation, legal, social media)
  - Configurable exclusion rules via YAML
  - See [KEYWORDS.md](KEYWORDS.md) for details
- **Source Tracking**: Every service keyword includes:
  - Source URL where it was found
  - Extraction method used (h1, title, meta, json_ld)
  - Confidence score (0.80-1.00)
- **Robust Error Handling**:
  - Handles network timeouts, SSL errors, invalid URLs
  - Respects robots.txt
  - Brotli compression support
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
2. **section_types** - Categorizes content sections:
   - `menu` - Navigation menu keywords
   - `service_detail` - Keywords from individual service pages
   - `service_listing` - Keywords from service hub/listing pages
3. **keywords_master** - Global unique keywords with statistics
4. **domain_keywords** - Links keywords to domains with:
   - Frequency data
   - Source URL tracking (for service keywords)
   - Extraction method (h1, title, meta, json_ld, service_card)
   - Confidence score (0.80-1.00)
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

3. **003_add_service_extraction.sql** - Adds service extraction support
   - New section types: 'service_detail', 'service_listing'
   - Source tracking columns: source_url, extraction_method, confidence_score
   - Indexes for efficient querying

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

#### Batch Mode (Default)

Crawl all pending domains sequentially with complete extraction (menu + services):
```bash
python main.py
```

The crawler will:
1. Check for pending domains in the companies table
2. Process each domain sequentially
3. **Extract navigation menu keywords** from homepage
4. **Extract service keywords** by following navigation links to service pages (up to 20 pages per domain)
5. Store normalized keywords with source tracking in the database
6. Update crawl status and statistics
7. Log all activity with detailed progress

**Example Output per Domain:**
```
[example.com] Extracting navigation menu keywords...
[example.com] Extracting service keywords...
[example.com] Complete - Menu: 25 kw, Services: 12 kw (8 pages), Total new: 37
```

#### On-Demand Mode - Menu Extraction Only

Crawl a specific domain's navigation menu immediately:

```bash
# Crawl navigation menu only
python main.py --domain example.com
python main.py -d example.com

# With verbose logging
python main.py --domain example.com --verbose
python main.py -d example.com -v
```

**Example Output:**
```
======================================================================
CRAWL RESULTS
======================================================================
Domain:          example.com
Status:          SUCCESS
Keywords found:  25
New keywords:    12
Pages crawled:   1
Pages failed:    0
Job ID:          a1b2c3d4-e5f6-7890-abcd-ef1234567890
======================================================================
```

#### On-Demand Mode - Complete Extraction (Menu + Services)

Extract both navigation menu AND service keywords by following links to service pages:

```bash
# Complete extraction: menu + services
python main.py --domain example.com --extract-services

# With verbose logging
python main.py --domain example.com --extract-services --verbose
```

**What it does:**
1. **Step 1**: Extracts navigation menu keywords (same as menu-only mode)
2. **Step 2**: Follows navigation links to service pages (up to 20 pages)
3. **Step 3**: Extracts service keywords from H1, title, meta, and JSON-LD
4. **Step 4**: Validates and stores with source tracking

**Example Output:**
```
======================================================================
COMPLETE EXTRACTION RESULTS
======================================================================
Domain:              example.com
Status:              SUCCESS

Menu Extraction:
  Keywords found:    25
  New keywords:      25

Service Extraction:
  Service links:     8
  Keywords found:    12
  New keywords:      12

Total:
  Keywords found:    37
  New keywords:      37
  Pages crawled:     9
  Pages failed:      0
Job ID:              a1b2c3d4-e5f6-7890-abcd-ef1234567890
======================================================================
```

**Features:**
- Bypasses crawl_status checks (works even if status is 'completed')
- Forces immediate crawl
- Shows detailed results summary
- Updates last_crawled timestamp
- Creates new crawl_job entry
- Tracks source URL for every service keyword
- Assigns confidence scores based on extraction method

**Use Cases:**
- Complete keyword extraction for business analysis
- Getting precise service/offering information
- Re-crawling specific sites after updates
- Testing service extraction accuracy
- Debugging crawl issues

**Requirements:**
- Domain must exist in companies table
- Add domains first using `add_domains.py` or `import_companies.py`
- Brotli compression support (automatically installed with requirements.txt)

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
├── service_extractor.py # Service page extraction (link-following, H1, title, meta, JSON-LD)
├── database.py          # Database operations with connection pooling
├── utils.py             # Utility functions (normalization, rate limiting)
├── config.py            # Configuration management
├── migrate.py           # Database migration manager
├── add_domains.py       # Add domains via CLI or text file
├── import_companies.py  # Import domains from CSV files (bulk)
├── check_status.py      # Status monitoring and statistics
├── cleanup_db.py        # Database cleanup utility
├── test_brotli.py       # Diagnostic tool for brotli compression support
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
│   ├── 003_add_service_extraction.sql
│   ├── 003_add_service_extraction_down.sql
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

## Extraction Methods

### Menu Detection Methods

The parser uses multiple methods to find navigation menus:

#### CSS Selectors
- `nav`, `.nav`, `#nav`
- `.menu`, `#menu`
- `.navigation`, `#navigation`
- `.navbar`, `.main-menu`, `.primary-menu`
- `header nav`, `.site-navigation`

#### HTML5 Semantic Tags
- `<nav>`
- `<menu>`

#### ARIA Attributes
- `role="navigation"`
- `role="menubar"`
- `aria-label="navigation"`

#### Common Patterns
- Elements with classes/IDs containing: menu, nav, navigation, navbar, menubar

### Service Page Extraction Methods

The service extractor achieves 100% accuracy by following navigation links to dedicated service pages and extracting only from structured elements.

#### Link Following Strategy

1. **Service URL Detection**
   - Scans navigation menu for service-related links
   - URL patterns detected: `/services`, `/solutions`, `/products`, `/offerings`, `/what-we-do`, `/capabilities`, `/expertise`
   - Excludes non-service pages: `/blog`, `/news`, `/about`, `/contact`, `/careers`, `/privacy`, `/terms`
   - Maximum 20 service pages per domain

2. **Page Classification**
   - **Service Listing** (`service_listing`): Hub pages like `/services`
   - **Service Detail** (`service_detail`): Individual pages like `/services/consulting`

#### Extraction Methods with Confidence Scores

The extractor uses 4 precision methods, ranked by reliability:

1. **JSON-LD Structured Data** (Confidence: 1.00)
   - Extracts from `<script type="application/ld+json">`
   - Looks for `@type`: "Service", "Product", or "Offer"
   - Gets the `name` property
   - Example: `{"@type": "Service", "name": "Cloud Migration Consulting"}`
   - Highest confidence because it's explicit structured data

2. **H1 Tags** (Confidence: 0.95)
   - Extracts from `<h1>` tags on service pages
   - Usually contains the exact service name
   - Example: `<h1>Cloud Migration Consulting</h1>`
   - Very high confidence as H1 typically defines page topic

3. **Page Title** (Confidence: 0.90)
   - Extracts from `<title>` tag
   - Removes company name and separators (|, -, ::, etc.)
   - Example: `<title>Cloud Migration - Example Co</title>` → "Cloud Migration"
   - High confidence but may include extra branding

4. **Meta Keywords** (Confidence: 0.85)
   - Extracts from `<meta name="keywords">`
   - Splits by comma
   - Example: `<meta name="keywords" content="cloud consulting, migration">`
   - Good confidence but rarely used in modern sites

5. **Service Cards** (Confidence: 0.80)
   - On listing pages, extracts from service card headings
   - CSS selectors: `.service-card h3`, `.solution-item .title`, etc.
   - Example: `<div class="service-card"><h3>Consulting</h3></div>`

#### Keyword Validation

Every extracted keyword must pass validation:

- **Length**: 3-100 characters
- **Word count**: 1-8 words
- **Content check**: Must contain either:
  - Service indicators: consulting, development, management, design, engineering, assessment, analysis, integration, migration, optimization, implementation, support, planning, architecture, security, compliance, testing, training, strategy, audit, review
  - OR be a proper noun (capitalized words)
- **Exclusions**: Generic terms like "our services", "learn more", "contact us" are filtered out

#### Source Tracking

Every service keyword is stored with complete traceability:

```sql
SELECT
    keyword,
    source_url,              -- URL where keyword was found
    extraction_method,       -- h1, title, meta, json_ld, service_card
    confidence_score        -- 0.80-1.00
FROM domain_keywords
WHERE section_type_id = 'service_detail';
```

**Example:**
```
keyword: "Cloud Migration Consulting"
source_url: "https://example.com/services/cloud-migration"
extraction_method: "json_ld"
confidence_score: 1.00
```

This allows you to:
- Verify extraction accuracy
- Understand keyword context
- Filter by confidence level
- Audit extraction quality

## Keyword Processing

### Normalization

Two versions of each keyword are stored:

**Original Keyword** (`keyword` field):
- Preserved exactly as found: `"Products & Services"`
- Special characters kept intact

**Normalized Keyword** (`normalized_keyword` field):
- Lowercase conversion
- Special character replacements:
  - `&` → `and`
  - `/` → `or`
  - `+` → `plus`
  - `@` → `at`
  - `#` → `number`
  - `%` → `percent`
- Whitespace consolidation and trimming
- Example: `"products and services"`
- Used for deduplication

### Business-Focused Filtering

Automatically excludes non-business keywords:
- ✗ Navigation (home, about, contact)
- ✗ Legal (privacy, terms, cookies)
- ✗ Social Media (facebook, twitter, linkedin)
- ✗ Authentication (login, register, sign up)
- ✗ Utility (search, download, help)
- ✓ Services, products, solutions
- ✓ Industry-specific terms
- ✓ Business capabilities

Configurable via `keyword_exclusions.yaml`. See [KEYWORDS.md](KEYWORDS.md) for details.

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

For detailed troubleshooting information, see **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**.

### Common Issues

**Service Links Not Found (shows 0 service links):**
- **Most common cause**: Missing brotli package for compression support
- **Symptoms**: Service extraction finds 0 links, but site has visible services
- **Solution**: Install brotli
  ```bash
  pip3 install --break-system-packages brotli
  ```
- **Verification**: Run diagnostic
  ```bash
  python test_brotli.py
  ```
- If brotli is installed and working, site may not have service pages with standard URL patterns

**403 Forbidden Errors:**
- Some sites (~5-10%) block automated crawlers
- Enhanced headers help with most sites (94%+ success rate)
- See TROUBLESHOOTING.md for solutions

**No Keywords Found:**
- Site may use JavaScript to render navigation
- Check site manually to verify menu structure
- For service extraction, ensure site has service pages with URLs containing: /services, /solutions, /products, etc.

**Failed Domains:**
```bash
# View domains that failed to crawl
python check_status.py failed
```

**Reset Stuck Jobs:**
```bash
python check_status.py reset
```

For complete troubleshooting guide including SSL errors, timeouts, database issues, and performance tuning, see **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**.

## License

Proprietary - All rights reserved

## Support

For issues or questions, contact your system administrator.
