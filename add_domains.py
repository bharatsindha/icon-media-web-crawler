"""
Utility script to add domains to the companies table for crawling.
"""

import sys
import logging
from database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_domains(domains):
    """
    Add domains to the companies table.

    Args:
        domains: List of domain names
    """
    db = DatabaseManager()

    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                added = 0
                skipped = 0

                for domain in domains:
                    domain = domain.strip()
                    if not domain:
                        continue

                    # Remove protocol if present
                    domain = domain.replace('https://', '').replace('http://', '')
                    # Remove trailing slash
                    domain = domain.rstrip('/')
                    # Remove www. prefix
                    if domain.startswith('www.'):
                        domain = domain[4:]

                    try:
                        cur.execute("""
                            INSERT INTO companies (domain, crawl_status, is_active)
                            VALUES (%s, 'pending', true)
                            ON CONFLICT (domain) DO NOTHING
                            RETURNING id
                        """, (domain,))

                        result = cur.fetchone()
                        if result:
                            logger.info(f"Added domain: {domain} (ID: {result[0]})")
                            added += 1
                        else:
                            logger.warning(f"Domain already exists: {domain}")
                            skipped += 1

                    except Exception as e:
                        logger.error(f"Error adding domain {domain}: {e}")
                        skipped += 1

                logger.info(f"\nSummary: {added} domains added, {skipped} skipped")

    except Exception as e:
        logger.error(f"Database error: {e}")
        sys.exit(1)

    finally:
        db.close_pool()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python add_domains.py domain1.com domain2.com ...")
        print("  python add_domains.py -f domains.txt")
        sys.exit(1)

    domains = []

    # Read from file
    if sys.argv[1] == '-f':
        if len(sys.argv) < 3:
            print("Error: Please specify a file path")
            sys.exit(1)

        try:
            with open(sys.argv[2], 'r') as f:
                domains = [line.strip() for line in f if line.strip()]
            logger.info(f"Read {len(domains)} domains from file")
        except FileNotFoundError:
            logger.error(f"File not found: {sys.argv[2]}")
            sys.exit(1)
    else:
        # Read from command line arguments
        domains = sys.argv[1:]

    if not domains:
        logger.error("No domains to add")
        sys.exit(1)

    add_domains(domains)


if __name__ == '__main__':
    main()
