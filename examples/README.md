# Example CSV Files

This directory contains sample CSV files demonstrating different formats for importing domains.

## Files

### domains_simple.csv
Simple CSV with header row and single column.
- Format: One column named "domain"
- Domains: 10 entries
- Use case: Basic import with header detection

**Usage:**
```bash
python import_companies.py -f examples/domains_simple.csv
```

### domains_no_header.csv
CSV without header row.
- Format: Single column, no header
- Domains: 10 entries
- Use case: Import from headerless CSV

**Usage:**
```bash
python import_companies.py -f examples/domains_no_header.csv --no-header
```

### domains_multi_column.csv
CSV with multiple columns.
- Format: Three columns (company_name, domain, industry)
- Domains: 10 entries in second column
- Mix of formats: http://, https://, www., plain domains
- Use case: Extract domains from specific column

**Usage:**
```bash
# By column name
python import_companies.py -f examples/domains_multi_column.csv --column domain

# By column index (0-based)
python import_companies.py -f examples/domains_multi_column.csv --column 1
```

### domains_mixed.csv
CSV with mixed valid and invalid domains for testing validation.
- Format: Single column with header
- Contains:
  - Valid domains
  - URLs with paths (will extract domain)
  - Invalid formats (spaces, missing TLD, etc.)
  - IP addresses
- Use case: Test validation and error handling

**Usage:**
```bash
# Dry run to see validation results
python import_companies.py -f examples/domains_mixed.csv --dry-run

# Import with verbose output
python import_companies.py -f examples/domains_mixed.csv --verbose
```

## Expected Results

### domains_simple.csv
```
Total rows: 10
Valid domains: 10
Invalid domains: 0
Domains imported: 10
```

### domains_multi_column.csv
```
Total rows: 10
Valid domains: 10
Invalid domains: 0
Domains imported: 10
Note: Prefixes (http://, https://, www.) are automatically removed
```

### domains_mixed.csv
```
Total rows: 15
Valid domains: ~8-9
Invalid domains: ~6-7
Skipped (invalid):
  - "not-a-domain" (no TLD)
  - "invalid domain with spaces" (contains spaces)
  - "google" (no TLD)
  - ".invalid.com" (starts with dot)
  - "192.168.1.1" (IP address)
  - "-invalid.com" (starts with hyphen)
```

## Testing Import Features

### Dry Run
Preview import without making changes:
```bash
python import_companies.py -f examples/domains_simple.csv --dry-run
```

### Update Existing
Update domains that already exist:
```bash
python import_companies.py -f examples/domains_simple.csv --update-existing
```

### Custom Batch Size
Control batch insert size:
```bash
python import_companies.py -f examples/domains_simple.csv --batch-size 5
```

### Verbose Output
See detailed processing information:
```bash
python import_companies.py -f examples/domains_simple.csv --verbose
```

## Creating Your Own CSV

### Single Column (Recommended)
```csv
domain
example.com
github.com
stackoverflow.com
```

### No Header
```csv
example.com
github.com
stackoverflow.com
```

### Multiple Columns
```csv
name,website,status
Example,example.com,active
GitHub,github.com,active
```

## Tips

1. **Domain Format**: Domains can include:
   - Plain: `example.com`
   - With www: `www.example.com`
   - With protocol: `https://example.com`
   - With path: `https://example.com/page` (path will be removed)

2. **Validation**: The importer will:
   - Remove `http://`, `https://`, `www.` prefixes
   - Remove trailing slashes
   - Convert to lowercase
   - Skip invalid domains
   - Log all skipped entries

3. **Performance**: Use larger batch sizes for big files:
   ```bash
   python import_companies.py -f large_file.csv --batch-size 5000
   ```

4. **Safety**: Always test with dry-run first:
   ```bash
   python import_companies.py -f your_file.csv --dry-run
   ```
