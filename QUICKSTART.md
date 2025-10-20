# Quick Start Guide

Get the web crawler up and running in 5 minutes.

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- A PostgreSQL database created

## Step 1: Install Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

## Step 2: Configure Database

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your database credentials
nano .env  # or use your preferred editor
```

Required settings in `.env`:
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
```

## Step 3: Run Migrations

```bash
# Check migration status
python migrate.py status

# Run all migrations to create tables
python migrate.py up
```

This will:
- Create all required tables (companies, section_types, keywords_master, domain_keywords, crawl_jobs)
- Add necessary indexes
- Create helper views
- Seed initial data (section_types)

## Step 4: Add Domains

### Option A: Quick Test (Few Domains)

```bash
# Add a few test domains
python add_domains.py example.com github.com stackoverflow.com

# Or from a text file
echo "example.com" > domains.txt
echo "github.com" >> domains.txt
echo "stackoverflow.com" >> domains.txt
python add_domains.py -f domains.txt
```

### Option B: Bulk Import (Hundreds/Thousands)

```bash
# Use sample CSV file
python import_companies.py -f examples/domains_simple.csv --dry-run

# If dry-run looks good, import for real
python import_companies.py -f examples/domains_simple.csv

# Or use your own CSV file
python import_companies.py -f your_domains.csv
```

## Step 5: Run the Crawler

```bash
python main.py
```

The crawler will:
1. Process domains one by one
2. Extract navigation menu items
3. Store keywords in the database
4. Log progress to console and files

## Step 6: Monitor Progress

Open a new terminal (keep the crawler running) and check status:

```bash
# View all statistics
python check_status.py

# View just stats
python check_status.py stats

# View recent jobs
python check_status.py jobs

# View top keywords
python check_status.py keywords
```

## Graceful Shutdown

Press `Ctrl+C` to stop the crawler gracefully. It will:
- Complete the current domain
- Update all database records
- Clean up resources

## What's Next?

### Add More Domains

```bash
# Small batch: text file
python add_domains.py -f large_domain_list.txt

# Large batch: CSV import (recommended for 1000+)
python import_companies.py -f large_domains.csv --batch-size 5000

# CSV import with validation preview
python import_companies.py -f domains.csv --dry-run --verbose
```

### Schedule Regular Runs

Use cron (Linux/Mac) or Task Scheduler (Windows):

```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/web_crawler && source venv/bin/activate && python main.py
```

### Monitor Logs

```bash
# Follow logs in real-time
tail -f logs/crawler_$(date +%Y-%m-%d).log
```

### Query the Database

```sql
-- View crawl statistics
SELECT * FROM v_crawl_statistics;

-- View top keywords
SELECT * FROM v_top_keywords LIMIT 20;

-- View recent jobs
SELECT * FROM v_recent_crawl_jobs LIMIT 10;

-- Find keywords for a specific domain
SELECT km.keyword, dk.total_frequency
FROM domain_keywords dk
JOIN keywords_master km ON km.id = dk.keyword_id
JOIN companies c ON c.id = dk.company_id
WHERE c.domain = 'example.com'
ORDER BY dk.total_frequency DESC;
```

## Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL is running
psql -h localhost -U your_username -d your_database_name

# Verify credentials in .env match your PostgreSQL setup
```

### No Domains Being Crawled

```bash
# Check if domains were added
psql -h localhost -U your_username -d your_database_name -c "SELECT COUNT(*) FROM companies WHERE crawl_status = 'pending';"

# Reset stuck jobs
python check_status.py reset
```

### SSL Errors

```bash
# Temporarily disable SSL verification (not for production)
# Add to .env:
VERIFY_SSL=false
```

### Rate Limiting

```bash
# Adjust rate limits in .env:
RATE_LIMIT_MIN=2.0
RATE_LIMIT_MAX=5.0
```

## Full Workflow Example

```bash
# 1. Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials

# 2. Initialize database
python migrate.py up

# 3. Add domains
python add_domains.py example.com github.com stackoverflow.com wikipedia.org reddit.com

# 4. Check status
python check_status.py stats

# 5. Run crawler
python main.py

# 6. Monitor (in another terminal)
python check_status.py
tail -f logs/crawler_$(date +%Y-%m-%d).log

# 7. View results in database
psql -h localhost -U your_user -d your_db -c "SELECT * FROM v_crawl_statistics;"
```

## Next Steps

- Read [README.md](README.md) for complete documentation
- Review database schema in [migrations/001_create_tables.sql](migrations/001_create_tables.sql)
- Customize crawler settings in `.env`
- Set up monitoring and alerting
- Schedule automated runs

## Support

For detailed documentation, see [README.md](README.md).
