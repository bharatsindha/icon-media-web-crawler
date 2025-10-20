"""
Utility script to check crawler status and view statistics.
"""

import sys
from datetime import datetime
from database import DatabaseManager


def format_timestamp(ts):
    """Format timestamp for display."""
    if ts is None:
        return 'Never'
    if isinstance(ts, str):
        return ts
    return ts.strftime('%Y-%m-%d %H:%M:%S')


def display_statistics(db):
    """Display crawler statistics."""
    stats = db.get_statistics()

    print("\n" + "=" * 60)
    print("CRAWLER STATISTICS")
    print("=" * 60)
    print(f"Total Companies:     {stats['total']}")
    print(f"  - Pending:         {stats['pending']}")
    print(f"  - In Progress:     {stats['in_progress']}")
    print(f"  - Completed:       {stats['completed']}")
    print(f"  - Failed:          {stats['failed']}")
    print(f"  - Paused:          {stats['paused']}")
    print(f"\nTotal Keywords:      {stats['total_keywords']}")
    print(f"Active Jobs:         {stats['active_jobs']}")
    print("=" * 60)


def display_recent_jobs(db, limit=10):
    """Display recent crawl jobs."""
    print(f"\n{'=' * 60}")
    print(f"RECENT CRAWL JOBS (Last {limit})")
    print("=" * 60)

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    cj.job_id,
                    c.domain,
                    cj.status,
                    cj.pages_crawled,
                    cj.pages_failed,
                    cj.new_keywords_found,
                    cj.started_at,
                    cj.completed_at
                FROM crawl_jobs cj
                JOIN companies c ON c.id = cj.company_id
                ORDER BY cj.created_at DESC
                LIMIT %s
            """, (limit,))

            jobs = cur.fetchall()

            if not jobs:
                print("No crawl jobs found")
            else:
                for job in jobs:
                    print(f"\nJob ID: {job[0]}")
                    print(f"  Domain:          {job[1]}")
                    print(f"  Status:          {job[2]}")
                    print(f"  Pages Crawled:   {job[3]}")
                    print(f"  Pages Failed:    {job[4]}")
                    print(f"  New Keywords:    {job[5]}")
                    print(f"  Started:         {format_timestamp(job[6])}")
                    print(f"  Completed:       {format_timestamp(job[7])}")

    print("=" * 60)


def display_top_keywords(db, limit=20):
    """Display top keywords by domain count."""
    print(f"\n{'=' * 60}")
    print(f"TOP KEYWORDS (By Domain Count, Limit {limit})")
    print("=" * 60)

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    keyword,
                    normalized_keyword,
                    unique_domains_count,
                    total_occurrences
                FROM keywords_master
                ORDER BY unique_domains_count DESC, total_occurrences DESC
                LIMIT %s
            """, (limit,))

            keywords = cur.fetchall()

            if not keywords:
                print("No keywords found")
            else:
                print(f"\n{'Keyword':<30} {'Domains':<10} {'Total Uses':<12}")
                print("-" * 60)
                for kw in keywords:
                    print(f"{kw[0]:<30} {kw[2]:<10} {kw[3]:<12}")

    print("=" * 60)


def display_failed_domains(db, limit=10):
    """Display recently failed domains."""
    print(f"\n{'=' * 60}")
    print(f"RECENTLY FAILED DOMAINS (Last {limit})")
    print("=" * 60)

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT domain, updated_at
                FROM companies
                WHERE crawl_status = 'failed'
                ORDER BY updated_at DESC
                LIMIT %s
            """, (limit,))

            domains = cur.fetchall()

            if not domains:
                print("No failed domains")
            else:
                print(f"\n{'Domain':<40} {'Failed At':<20}")
                print("-" * 60)
                for domain in domains:
                    print(f"{domain[0]:<40} {format_timestamp(domain[1]):<20}")

    print("=" * 60)


def reset_stuck_jobs(db):
    """Reset stuck jobs."""
    print("\nResetting stuck jobs...")
    count = db.reset_stuck_jobs()
    print(f"Reset {count} stuck jobs to pending status")


def main():
    """Main entry point."""
    db = DatabaseManager()

    try:
        # Check health
        if not db.health_check():
            print("ERROR: Database connection failed!")
            sys.exit(1)

        # Check command line arguments
        command = sys.argv[1] if len(sys.argv) > 1 else 'all'

        if command == 'stats' or command == 'all':
            display_statistics(db)

        if command == 'jobs' or command == 'all':
            display_recent_jobs(db)

        if command == 'keywords' or command == 'all':
            display_top_keywords(db)

        if command == 'failed' or command == 'all':
            display_failed_domains(db)

        if command == 'reset':
            reset_stuck_jobs(db)

        if command not in ['stats', 'jobs', 'keywords', 'failed', 'reset', 'all']:
            print("Usage: python check_status.py [command]")
            print("\nCommands:")
            print("  stats     - Show crawler statistics")
            print("  jobs      - Show recent crawl jobs")
            print("  keywords  - Show top keywords")
            print("  failed    - Show failed domains")
            print("  reset     - Reset stuck jobs")
            print("  all       - Show all information (default)")

    finally:
        db.close_pool()


if __name__ == '__main__':
    main()
