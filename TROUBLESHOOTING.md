# Troubleshooting Guide

This guide helps resolve common issues when crawling websites.

## Common Issues

### 1. 403 Forbidden Errors

**Symptom:**
```
HTTP error fetching https://example.com: 403 Client Error: Forbidden
```

**Causes:**
- Website is blocking bot traffic
- Anti-bot protection (Cloudflare, sitedistrict, etc.)
- IP-based blocking or rate limiting

**Solutions:**

#### Option 1: Enhanced Headers (Already Configured)
The crawler includes browser-like headers to avoid detection:
- Real browser User-Agent (Chrome on macOS)
- Sec-Fetch-* headers for Chrome compatibility
- Complete Accept headers for images, webp, etc.

These work for ~90-95% of websites.

#### Option 2: Adjust Rate Limiting
Some sites block if you request too quickly. In `.env`:
```bash
RATE_LIMIT_MIN=2.0  # Increase from 1.0
RATE_LIMIT_MAX=5.0  # Increase from 2.0
```

#### Option 3: Accept the Limitation
Some websites (~5-10%) have aggressive bot protection that cannot be bypassed without:
- Browser automation (Selenium/Playwright) - slow and resource-intensive
- Proxy rotation - expensive
- CAPTCHA solving - not feasible for automation

**Recommendation:** Track which domains fail and handle them manually if they're high priority.

### 2. SSL Certificate Errors

**Symptom:**
```
SSL error for example.com: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**Solution:**
In `.env`, temporarily disable SSL verification (not recommended for production):
```bash
VERIFY_SSL=false
```

### 3. Timeout Errors

**Symptom:**
```
Request timeout for example.com
```

**Solution:**
Increase timeout in `.env`:
```bash
REQUEST_TIMEOUT=60  # Increase from 30 seconds
```

### 4. No Keywords Found

**Symptom:**
```
No menu keywords found for example.com
```

**Causes:**
- Website uses JavaScript to render navigation (React, Vue, etc.)
- Navigation menu uses non-standard HTML structure
- Menu is in an iframe

**Solution:**
Check the website manually. If the menu is JavaScript-rendered, the crawler won't see it (requires headless browser).

### 5. Database Connection Errors

**Symptom:**
```
Failed to initialize database pool: connection refused
```

**Solution:**
1. Verify PostgreSQL is running:
   ```bash
   psql -h localhost -U your_username -d your_database_name
   ```

2. Check credentials in `.env`:
   ```bash
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=your_database_name
   DB_USER=your_username
   DB_PASSWORD=your_password
   ```

### 6. Stuck Jobs

**Symptom:**
Jobs showing "in_progress" but crawler isn't running.

**Solution:**
Reset stuck jobs:
```bash
python check_status.py reset
```

## Checking Failed Domains

View domains that failed to crawl:
```bash
python check_status.py failed
```

## Success Rate Expectations

**Normal Success Rates:**
- 90-95%: Excellent (most sites crawl successfully)
- 85-90%: Good (some bot protection encountered)
- Below 85%: Investigate rate limiting or IP blocking

**Why Some Sites Fail:**
- Cloudflare bot protection
- Geographic restrictions
- Request rate limiting
- Sites that require JavaScript rendering
- Sites behind authentication

## Advanced Solutions (Not Implemented)

For sites with aggressive bot protection, consider:

### Option 1: Selenium/Playwright
Use headless browser automation:
- **Pros:** Bypasses most bot detection, executes JavaScript
- **Cons:** 10-100x slower, resource-intensive, complex

### Option 2: Proxy Rotation
Rotate IP addresses:
- **Pros:** Avoids IP-based blocking
- **Cons:** Expensive, requires proxy service

### Option 3: Manual Collection
For high-value domains that can't be automated:
- Crawl manually in browser
- Copy navigation menu items
- Use `add_domains.py` to add keywords manually

## Monitoring

### Check Crawler Status
```bash
python check_status.py
```

### View Logs
```bash
tail -f logs/crawler_$(date +%Y-%m-%d).log
```

### View Statistics
```bash
python check_status.py stats
```

### View Failed Domains
```bash
python check_status.py failed
```

## Performance Tuning

### For Large Batches (10,000+ domains)

1. **Increase connection pool:**
   ```bash
   DB_MAX_CONN=20  # Increase from 10
   ```

2. **Batch processing:**
   ```bash
   BATCH_SIZE=500  # Increase from 100
   ```

3. **Monitor system resources:**
   - CPU usage
   - Memory usage
   - Database connections
   - Network bandwidth

### For Rate-Limited Sites

If many sites are blocking:
1. Increase delays: `RATE_LIMIT_MIN=3.0`, `RATE_LIMIT_MAX=7.0`
2. Reduce batch size: `BATCH_SIZE=50`
3. Add retries: `MAX_RETRIES=5`

## Getting Help

1. Check logs in `logs/` directory
2. Run database health check: `python check_status.py`
3. Verify configuration: `python -c "from config import Config; Config.validate()"`
4. Test specific domain: `python main.py --domain example.com --verbose`

## Known Limitations

1. **JavaScript-Rendered Sites:** Cannot crawl sites that build menus with JavaScript
2. **Bot Protection:** 5-10% of sites use aggressive anti-bot measures
3. **Authentication:** Cannot crawl sites requiring login
4. **Geographic Restrictions:** Some sites block certain countries/IPs
5. **Rate Limits:** Aggressive crawling may trigger IP bans

These limitations are inherent to HTTP-based web scraping and would require browser automation to overcome.
