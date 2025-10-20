"""
Cleanup script to reset database to a clean state.
Run this if migrations left the database in a bad state.
"""

import sys

# Try to import psycopg3 first, fall back to psycopg2
try:
    import psycopg
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2 as psycopg
        PSYCOPG_VERSION = 2
    except ImportError:
        print("ERROR: Neither psycopg nor psycopg2 is installed.")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)

from config import Config

print("=" * 70)
print("DATABASE CLEANUP SCRIPT")
print("=" * 70)
print(f"\nUsing: psycopg{PSYCOPG_VERSION}")
print(f"Database: {Config.DB_NAME}@{Config.DB_HOST}")
print("\nWARNING: This will drop all tables and the schema_migrations table!")
print("=" * 70)

response = input("\nDo you want to continue? (yes/no): ")
if response.lower() not in ['yes', 'y']:
    print("Cleanup cancelled.")
    sys.exit(0)

try:
    # Connect to database
    if PSYCOPG_VERSION == 3:
        conninfo = (
            f"host={Config.DB_HOST} port={Config.DB_PORT} "
            f"dbname={Config.DB_NAME} user={Config.DB_USER} "
            f"password={Config.DB_PASSWORD}"
        )
        conn = psycopg.connect(conninfo, autocommit=True)
    else:
        conn = psycopg.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        conn.set_isolation_level(0)  # AUTOCOMMIT

    print("\nConnected to database successfully")

    with conn.cursor() as cur:
        print("\nDropping existing tables...")

        # Drop tables in reverse order of dependencies
        tables = [
            'crawl_jobs',
            'domain_keywords',
            'keywords_master',
            'section_types',
            'companies',
            'schema_migrations'
        ]

        for table in tables:
            try:
                cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                print(f"  ✓ Dropped {table}")
            except Exception as e:
                print(f"  ⚠ Could not drop {table}: {e}")

        # Drop views
        views = [
            'v_recent_crawl_jobs',
            'v_top_keywords',
            'v_crawl_statistics',
            'v_pending_companies'
        ]

        print("\nDropping views...")
        for view in views:
            try:
                cur.execute(f"DROP VIEW IF EXISTS {view} CASCADE")
                print(f"  ✓ Dropped {view}")
            except Exception as e:
                print(f"  ⚠ Could not drop {view}: {e}")

        # Drop functions
        print("\nDropping functions...")
        try:
            cur.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
            print("  ✓ Dropped update_updated_at_column()")
        except Exception as e:
            print(f"  ⚠ Could not drop function: {e}")

    conn.close()

    print("\n" + "=" * 70)
    print("DATABASE CLEANED SUCCESSFULLY")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Run: python migrate.py up")
    print("2. Verify: python migrate.py status")
    print("=" * 70)

except Exception as e:
    print(f"\nERROR: {e}")
    sys.exit(1)
