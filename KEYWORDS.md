# Keyword Extraction and Filtering

This document explains how the web crawler extracts, normalizes, and filters keywords from navigation menus.

## Overview

The crawler extracts keywords from website navigation menus and applies intelligent filtering to focus on business-relevant terms while excluding common navigation, legal, and utility items.

## Keyword Processing Pipeline

```
Menu HTML → Extract Text (Preserve Original) → Filter → Store with Normalization
```

### 1. **Extraction**
Menu items are extracted from HTML using multiple detection methods:
- CSS selectors (`nav`, `.menu`, etc.)
- HTML5 semantic tags (`<nav>`, `<menu>`)
- ARIA attributes (`role="navigation"`)
- Common patterns (classes/IDs containing "menu", "nav", etc.)

**Important:** Original text is preserved during extraction, including special characters like `&`, `/`, `+`, etc. This ensures the `keyword` field stores exactly what appears on the website.

### 2. **Normalization**
Keywords are normalized **only during database storage** for consistency and deduplication:

**Original Keyword** (stored in `keyword` field):
- Preserved exactly as found on the website
- Special characters and capitalization retained
- Example: "Products & Services", "Energy/Utilities", "C++ Development"

**Normalized Keyword** (stored in `normalized_keyword` field):
- Created during database insertion from the original keyword
- Lowercase conversion
- Special character replacement:
  - `&` → `and`
  - `/` → `or`
  - `+` → `plus`
  - `@` → `at`
  - `#` → `number`
  - `%` → `percent`
- Removes remaining special characters
- Trims whitespace and hyphens
- Example: "products and services", "energy or utilities", "c plus plus development"

**Purpose:** The `normalized_keyword` field is used for deduplication and matching, while the `keyword` field preserves the exact text as it appears on the website.

### 3. **Filtering**
Business-focused filtering removes non-business keywords:

**Excluded Categories:**
- Navigation (home, about, contact)
- Legal (privacy, terms, disclaimer)
- Support (help, faq, documentation)
- Social Media (facebook, twitter, linkedin)
- Authentication (login, register, sign up)
- Language/Region selectors
- Generic actions (search, download, subscribe)
- Footer utility items

**Kept Keywords:**
- Services and solutions
- Products
- Industry-specific terms
- Technology/software names
- Business capabilities
- Professional services

## Configuration

### Enable/Disable Filtering

Set in `.env` file:
```bash
# Enable keyword filtering (default: true)
ENABLE_KEYWORD_FILTER=true

# Path to exclusions file (default: keyword_exclusions.yaml)
KEYWORD_EXCLUSIONS_FILE=keyword_exclusions.yaml
```

### Exclusion Rules

Edit `keyword_exclusions.yaml` to customize:

```yaml
# Exact matches (case-insensitive)
navigation:
  - home
  - about
  - contact

# Pattern matching (supports wildcards)
patterns:
  - "copyright*"
  - "*rights reserved*"

# Configuration
config:
  enabled: true
  case_insensitive: true
  log_excluded: true
  min_length: 2
  max_length: 50
```

## Examples

### Example 1: Special Characters

**Menu Item**: "Cloud & DevOps"

**Processing**:
- Original: `Cloud & DevOps` (stored in `keyword` field)
- Normalized: `cloud and devops` (stored in `normalized_keyword` field)
- Filtered: ✓ Kept (business keyword)

### Example 2: Navigation Item

**Menu Item**: "Contact Us"

**Processing**:
- Original: `Contact Us`
- Normalized: `contact us`
- Filtered: ✗ Excluded (navigation category)

### Example 3: Service with Slash

**Menu Item**: "Software/Hardware"

**Processing**:
- Original: `Software/Hardware` (stored as-is)
- Normalized: `software or hardware`
- Filtered: ✓ Kept (business keyword)

### Example 4: Social Media

**Menu Item**: "Follow us on Twitter"

**Processing**:
- Original: `Follow us on Twitter`
- Normalized: `follow us on twitter`
- Filtered: ✗ Excluded (social/actions categories)

## Database Schema

```sql
-- keywords_master table
keyword               VARCHAR(255)  -- Original text: "Products & Services"
normalized_keyword    VARCHAR(255)  -- Normalized: "products and services"
                                    -- (UNIQUE constraint)
```

## Statistics

The crawler logs filtering statistics:

```
2025-10-20 10:30:45 - INFO - Extracted 45 raw keywords from menu items
2025-10-20 10:30:45 - INFO - Filtered 23 non-business keywords (22 remaining)
2025-10-20 10:30:45 - INFO - Successfully crawled example.com: 22 keywords (15 new)
```

## Customization

### Adding Exclusions

Add new terms to `keyword_exclusions.yaml`:

```yaml
# Your custom category
custom_exclusions:
  - custom term 1
  - custom term 2
```

Then add the category to the filter loader in `utils.py`:

```python
for category in ['navigation', 'legal', 'custom_exclusions']:
    # ...
```

### Disabling Filtering

To disable filtering entirely:

**Option 1: Environment Variable**
```bash
# In .env
ENABLE_KEYWORD_FILTER=false
```

**Option 2: YAML Configuration**
```yaml
# In keyword_exclusions.yaml
config:
  enabled: false
```

## Best Practices

1. **Review Exclusions**: Periodically review excluded keywords in logs to ensure important terms aren't filtered out

2. **Industry-Specific**: Customize exclusions for your target industries

3. **Test First**: Use a small sample of domains to test filtering before full-scale crawl

4. **Monitor Statistics**: Check filtering stats to ensure reasonable exclusion rates (typically 30-50%)

5. **Keep Original**: The original keyword is always preserved, allowing post-processing if needed

## Troubleshooting

### Too Many Keywords Excluded

**Problem**: Filtering is too aggressive

**Solution**:
1. Review `keyword_exclusions.yaml`
2. Remove overly broad patterns
3. Decrease `min_length` if short keywords are important

### Not Enough Filtering

**Problem**: Too many non-business keywords

**Solution**:
1. Add more terms to exclusion categories
2. Add patterns for common footers/headers
3. Adjust `max_length` to filter very long menu items

### Filtering Not Working

**Problem**: Exclusions not being applied

**Check**:
1. `ENABLE_KEYWORD_FILTER=true` in `.env`
2. `keyword_exclusions.yaml` file exists
3. Check logs for "Keyword filtering enabled" message
4. Verify YAML syntax is correct

## Performance Impact

- **Minimal overhead**: Filtering adds <10ms per domain
- **Reduces storage**: 30-50% fewer keywords stored
- **Improves quality**: Better keyword relevance for analysis
- **Cacheable**: Exclusion rules loaded once at startup

## Future Enhancements

Potential improvements:
- Machine learning-based classification
- Domain-specific exclusion rules
- Weighted keywords (relevance scores)
- Multi-language support
- Dynamic exclusion updates
