# Installation Guide

## Python Version Compatibility

This web crawler supports both modern and older Python versions by using compatible database drivers.

### Python 3.12+ (Recommended)

For Python 3.12 and newer (including 3.13), the project uses **psycopg3**, which is the modern, actively developed PostgreSQL adapter.

```bash
# Install dependencies (psycopg3 will be installed)
pip install -r requirements.txt
```

### Python 3.8-3.11

If you're using Python 3.8 through 3.11, you can use either psycopg3 or psycopg2-binary.

**Option 1: Use psycopg3 (recommended)**
```bash
pip install -r requirements.txt
```

**Option 2: Use psycopg2-binary**
```bash
# Edit requirements.txt and uncomment the psycopg2-binary line
# Comment out the psycopg lines
pip install -r requirements.txt
```

## Installation Steps

### 1. Clone or Navigate to Project

```bash
cd /path/to/web_crawler
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your settings
nano .env  # or use your preferred editor
```

Required settings in `.env`:
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crawler_db
DB_USER=your_username
DB_PASSWORD=your_password
```

### 5. Run Migrations

```bash
# Initialize database schema
python migrate.py up
```

### 6. Verify Installation

```bash
# Check migration status
python migrate.py status

# Check database connection
python check_status.py stats
```

## Troubleshooting Installation

### Issue: psycopg Installation Fails

**Problem**: Building psycopg or psycopg2-binary fails on your system.

**Solutions**:

#### Solution 1: Install PostgreSQL Development Libraries

**macOS (Homebrew)**:
```bash
brew install postgresql
```

**Ubuntu/Debian**:
```bash
sudo apt-get install libpq-dev python3-dev
```

**RHEL/CentOS**:
```bash
sudo yum install postgresql-devel python3-devel
```

#### Solution 2: Use Pre-built Wheels

Try installing with pre-built binary wheels:

```bash
# For psycopg3
pip install --only-binary :all: psycopg[binary] psycopg-pool

# Or for psycopg2
pip install --only-binary :all: psycopg2-binary
```

#### Solution 3: Switch Database Drivers

Edit `requirements.txt`:

**If psycopg3 fails, try psycopg2**:
```txt
# Comment out:
# psycopg[binary]==3.2.3
# psycopg-pool==3.2.5

# Uncomment:
psycopg2-binary==2.9.9
```

**If psycopg2 fails, try psycopg3**:
```txt
# Uncomment:
psycopg[binary]==3.2.3
psycopg-pool==3.2.5

# Comment out:
# psycopg2-binary==2.9.9
```

Then reinstall:
```bash
pip install -r requirements.txt
```

### Issue: Python 3.13 Compatibility

**Problem**: psycopg2-binary doesn't have pre-built wheels for Python 3.13.

**Solution**: Use psycopg3 (default in requirements.txt):
```bash
pip install psycopg[binary]==3.2.3 psycopg-pool==3.2.5
```

The project automatically detects which version is installed and uses the correct API.

### Issue: SSL Certificate Errors

**Problem**: SSL errors when connecting to PostgreSQL.

**Solution**: Check PostgreSQL SSL settings:
```bash
# In .env, temporarily disable SSL verification
VERIFY_SSL=false
```

### Issue: Connection Refused

**Problem**: Cannot connect to PostgreSQL.

**Solutions**:
1. Verify PostgreSQL is running:
   ```bash
   # Check status
   brew services list  # macOS
   systemctl status postgresql  # Linux
   ```

2. Test connection manually:
   ```bash
   psql -h localhost -U your_user -d your_db
   ```

3. Check firewall settings
4. Verify credentials in `.env`

## Platform-Specific Notes

### macOS

On Apple Silicon (M1/M2), you may need:
```bash
# Install PostgreSQL via Homebrew
brew install postgresql

# Set compiler flags if needed
export LDFLAGS="-L/opt/homebrew/opt/postgresql/lib"
export CPPFLAGS="-I/opt/homebrew/opt/postgresql/include"

# Then install
pip install -r requirements.txt
```

### Windows

On Windows, you may need Microsoft Visual C++ Build Tools:
1. Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Install "Desktop development with C++"
3. Restart terminal
4. Run `pip install -r requirements.txt`

Alternatively, use WSL (Windows Subsystem for Linux) for easier setup.

### Linux

Most Linux distributions require development packages:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-dev libpq-dev build-essential

# Fedora
sudo dnf install python3-devel postgresql-devel gcc

# Arch
sudo pacman -S python postgresql-libs base-devel
```

## Verifying Installation

After installation, verify everything works:

```bash
# 1. Check Python packages
pip list | grep psycopg

# 2. Test database connection
python -c "from database import DatabaseManager; db = DatabaseManager(); print('✓ Database connection works')"

# 3. Check migration status
python migrate.py status

# 4. View statistics
python check_status.py stats
```

Expected output:
```
✓ Database connection works

DATABASE MIGRATION STATUS
=========================
Database: crawler_db@localhost
Total migrations: 2
Applied: 2
Pending: 0
```

## Docker Installation (Alternative)

If you prefer Docker, create a `Dockerfile`:

```dockerfile
FROM python:3.13-slim

# Install PostgreSQL client
RUN apt-get update && apt-get install -y libpq-dev gcc

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run crawler
CMD ["python", "main.py"]
```

Then use docker-compose:

```yaml
version: '3.8'

services:
  crawler:
    build: .
    env_file: .env
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: crawler_db
      POSTGRES_USER: crawler
      POSTGRES_PASSWORD: your_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Next Steps

After successful installation:

1. Read [QUICKSTART.md](QUICKSTART.md) for usage guide
2. Review [README.md](README.md) for full documentation
3. Add domains with `python add_domains.py`
4. Run crawler with `python main.py`
5. Monitor with `python check_status.py`

## Getting Help

If you encounter issues:

1. Check this installation guide
2. Review error messages carefully
3. Search for similar issues online
4. Check PostgreSQL and Python versions
5. Try alternative database drivers (psycopg2 vs psycopg3)
6. Verify PostgreSQL is running and accessible
