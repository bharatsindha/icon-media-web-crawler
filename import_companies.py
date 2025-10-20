"""
Import company domains from CSV file into the web crawler database.

Usage:
    python import_companies.py -f domains.csv
    python import_companies.py -f domains.csv --dry-run
    python import_companies.py -f domains.csv --update-existing --batch-size 500
"""

import sys
import csv
import argparse
import logging
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from database import DatabaseManager
from utils import normalize_domain

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CSVDomainImporter:
    """Import domains from CSV file into database."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        batch_size: int = 1000,
        update_existing: bool = False,
        dry_run: bool = False
    ):
        """
        Initialize CSV importer.

        Args:
            db_manager: Database manager instance
            batch_size: Number of domains to insert per batch
            update_existing: Whether to update existing domains
            dry_run: Preview mode without actual import
        """
        self.db = db_manager
        self.batch_size = batch_size
        self.update_existing = update_existing
        self.dry_run = dry_run

        # Statistics
        self.stats = {
            'total_rows': 0,
            'valid_domains': 0,
            'invalid_domains': 0,
            'imported': 0,
            'updated': 0,
            'skipped_duplicate': 0,
            'skipped_invalid': 0,
            'errors': 0
        }

        self.invalid_entries = []
        self.start_time = None

    def detect_has_header(self, file_path: str, sample_size: int = 5) -> bool:
        """
        Auto-detect if CSV has a header row.

        Args:
            file_path: Path to CSV file
            sample_size: Number of rows to sample

        Returns:
            True if header detected, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sniffer = csv.Sniffer()
                sample = f.read(1024)
                return sniffer.has_header(sample)
        except Exception as e:
            logger.warning(f"Could not detect header, assuming no header: {e}")
            return False

    def read_csv(
        self,
        file_path: str,
        has_header: Optional[bool] = None,
        column: Optional[str] = None
    ) -> List[str]:
        """
        Read domains from CSV file.

        Args:
            file_path: Path to CSV file
            has_header: Whether CSV has header (None = auto-detect)
            column: Column name or index (None = first column)

        Returns:
            List of raw domain strings
        """
        domains = []

        # Auto-detect header if not specified
        if has_header is None:
            has_header = self.detect_has_header(file_path)
            logger.info(f"Auto-detected header: {has_header}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)

                # Skip header if present
                if has_header:
                    header = next(reader, None)
                    logger.info(f"Header row: {header}")

                    # Determine column index
                    if column:
                        if column.isdigit():
                            col_idx = int(column)
                        else:
                            try:
                                col_idx = header.index(column)
                            except ValueError:
                                logger.error(f"Column '{column}' not found in header")
                                raise ValueError(f"Column '{column}' not found")
                    else:
                        col_idx = 0
                else:
                    # Use first column or specified index
                    col_idx = int(column) if column and column.isdigit() else 0

                # Read domains
                for row_num, row in enumerate(reader, start=2 if has_header else 1):
                    self.stats['total_rows'] += 1

                    if not row:  # Skip empty rows
                        continue

                    if col_idx >= len(row):
                        logger.warning(f"Row {row_num}: Column index {col_idx} out of range")
                        continue

                    domain = row[col_idx].strip()
                    if domain:
                        domains.append(domain)

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            raise

        return domains

    def validate_domain(self, domain: str) -> Optional[str]:
        """
        Validate and normalize domain.

        Args:
            domain: Raw domain string

        Returns:
            Normalized domain or None if invalid
        """
        if not domain or not domain.strip():
            return None

        # Remove common prefixes
        domain = domain.strip().lower()
        domain = domain.replace('http://', '')
        domain = domain.replace('https://', '')
        domain = domain.rstrip('/')

        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]

        # Basic validation
        if not domain:
            return None

        # Check for valid characters
        if not all(c.isalnum() or c in '.-' for c in domain):
            return None

        # Must contain at least one dot
        if '.' not in domain:
            return None

        # Must not start or end with dot or hyphen
        if domain.startswith(('.', '-')) or domain.endswith(('.', '-')):
            return None

        # Reasonable length check
        if len(domain) < 4 or len(domain) > 253:
            return None

        return domain

    def process_domains(self, raw_domains: List[str]) -> List[str]:
        """
        Process and validate list of domains.

        Args:
            raw_domains: List of raw domain strings

        Returns:
            List of valid, normalized domains
        """
        valid_domains = []

        for idx, raw_domain in enumerate(raw_domains, start=1):
            normalized = self.validate_domain(raw_domain)

            if normalized:
                valid_domains.append(normalized)
                self.stats['valid_domains'] += 1
            else:
                self.stats['invalid_domains'] += 1
                self.stats['skipped_invalid'] += 1
                self.invalid_entries.append({
                    'row': idx,
                    'value': raw_domain,
                    'reason': 'Invalid domain format'
                })
                logger.debug(f"Invalid domain at row {idx}: {raw_domain}")

        return valid_domains

    def import_batch(self, domains: List[str]) -> Tuple[int, int]:
        """
        Import a batch of domains into database.

        Args:
            domains: List of normalized domains

        Returns:
            Tuple of (imported_count, updated_count)
        """
        imported = 0
        updated = 0

        if self.dry_run:
            logger.info(f"[DRY RUN] Would import {len(domains)} domains")
            return len(domains), 0

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                for domain in domains:
                    try:
                        if self.update_existing:
                            # Insert or update
                            cur.execute("""
                                INSERT INTO companies (domain, crawl_status, is_active, created_at, updated_at)
                                VALUES (%s, 'pending', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                                ON CONFLICT (domain) DO UPDATE SET
                                    crawl_status = 'pending',
                                    is_active = true,
                                    updated_at = CURRENT_TIMESTAMP
                                RETURNING (xmax = 0) AS inserted
                            """, (domain,))

                            result = cur.fetchone()
                            if result and result[0]:
                                imported += 1
                            else:
                                updated += 1
                        else:
                            # Insert only, skip duplicates
                            cur.execute("""
                                INSERT INTO companies (domain, crawl_status, is_active, created_at, updated_at)
                                VALUES (%s, 'pending', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                                ON CONFLICT (domain) DO NOTHING
                                RETURNING id
                            """, (domain,))

                            result = cur.fetchone()
                            if result:
                                imported += 1
                            else:
                                self.stats['skipped_duplicate'] += 1

                    except Exception as e:
                        logger.error(f"Error importing domain {domain}: {e}")
                        self.stats['errors'] += 1

        return imported, updated

    def import_domains(self, domains: List[str]) -> None:
        """
        Import domains in batches.

        Args:
            domains: List of validated domains
        """
        total = len(domains)
        logger.info(f"Importing {total} domains in batches of {self.batch_size}")

        for i in range(0, total, self.batch_size):
            batch = domains[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total + self.batch_size - 1) // self.batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} domains)")

            imported, updated = self.import_batch(batch)

            self.stats['imported'] += imported
            self.stats['updated'] += updated

            # Show progress
            progress = min(i + self.batch_size, total)
            pct = (progress / total * 100) if total > 0 else 0
            logger.info(f"Progress: {progress}/{total} ({pct:.1f}%)")

    def print_summary(self) -> None:
        """Print import summary report."""
        elapsed = time.time() - self.start_time if self.start_time else 0

        print("\n" + "=" * 70)
        if self.dry_run:
            print("DRY RUN SUMMARY (No changes made)")
        else:
            print("IMPORT SUMMARY")
        print("=" * 70)

        print(f"\nFile Statistics:")
        print(f"  Total rows processed:     {self.stats['total_rows']}")
        print(f"  Valid domains found:      {self.stats['valid_domains']}")
        print(f"  Invalid domains:          {self.stats['invalid_domains']}")

        print(f"\nImport Results:")
        if self.dry_run:
            print(f"  Would import:             {self.stats['valid_domains']}")
        else:
            print(f"  Domains imported:         {self.stats['imported']}")
            if self.update_existing:
                print(f"  Domains updated:          {self.stats['updated']}")
            else:
                print(f"  Skipped (duplicates):     {self.stats['skipped_duplicate']}")
        print(f"  Skipped (invalid):        {self.stats['skipped_invalid']}")
        print(f"  Errors:                   {self.stats['errors']}")

        print(f"\nPerformance:")
        print(f"  Time taken:               {elapsed:.2f} seconds")
        if elapsed > 0 and self.stats['imported'] > 0:
            rate = self.stats['imported'] / elapsed
            print(f"  Import rate:              {rate:.1f} domains/second")

        # Show invalid entries if any
        if self.invalid_entries and len(self.invalid_entries) <= 20:
            print(f"\nInvalid Entries:")
            for entry in self.invalid_entries[:20]:
                print(f"  Row {entry['row']}: '{entry['value']}' - {entry['reason']}")
            if len(self.invalid_entries) > 20:
                print(f"  ... and {len(self.invalid_entries) - 20} more")

        print("\n" + "=" * 70)

    def run(
        self,
        file_path: str,
        has_header: Optional[bool] = None,
        column: Optional[str] = None
    ) -> bool:
        """
        Run the import process.

        Args:
            file_path: Path to CSV file
            has_header: Whether CSV has header
            column: Column name or index

        Returns:
            True if successful, False otherwise
        """
        self.start_time = time.time()

        try:
            # Verify file exists
            if not Path(file_path).exists():
                logger.error(f"File not found: {file_path}")
                return False

            logger.info(f"Reading CSV file: {file_path}")
            logger.info(f"Batch size: {self.batch_size}")
            logger.info(f"Update existing: {self.update_existing}")
            logger.info(f"Dry run: {self.dry_run}")

            # Read CSV
            raw_domains = self.read_csv(file_path, has_header, column)
            logger.info(f"Read {len(raw_domains)} domain entries from CSV")

            # Validate and normalize
            logger.info("Validating and normalizing domains...")
            valid_domains = self.process_domains(raw_domains)
            logger.info(f"Found {len(valid_domains)} valid domains")

            if not valid_domains:
                logger.warning("No valid domains to import")
                self.print_summary()
                return False

            # Import
            if self.dry_run:
                logger.info("[DRY RUN MODE] - No actual import will occur")
                logger.info(f"Would import {len(valid_domains)} domains")
            else:
                self.import_domains(valid_domains)

            # Print summary
            self.print_summary()

            return True

        except Exception as e:
            logger.error(f"Import failed: {e}", exc_info=True)
            self.print_summary()
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Import company domains from CSV file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic import
  python import_companies.py -f domains.csv

  # Dry run to preview
  python import_companies.py -f domains.csv --dry-run

  # Update existing domains
  python import_companies.py -f domains.csv --update-existing

  # Specify column and batch size
  python import_companies.py -f domains.csv --column domain --batch-size 500

  # CSV with no header, use second column
  python import_companies.py -f domains.csv --no-header --column 1
        """
    )

    parser.add_argument(
        '-f', '--file',
        required=True,
        help='Path to CSV file containing domains'
    )

    parser.add_argument(
        '--has-header',
        action='store_true',
        default=None,
        help='CSV file has header row (default: auto-detect)'
    )

    parser.add_argument(
        '--no-header',
        action='store_true',
        help='CSV file has no header row'
    )

    parser.add_argument(
        '--column',
        default=None,
        help='Column name or index for domains (default: first column)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview import without making changes'
    )

    parser.add_argument(
        '--update-existing',
        action='store_true',
        help='Update existing domains to pending status'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Number of domains per batch insert (default: 1000)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine has_header
    has_header = None
    if args.has_header:
        has_header = True
    elif args.no_header:
        has_header = False

    # Validate arguments
    if args.batch_size < 1:
        logger.error("Batch size must be at least 1")
        sys.exit(1)

    # Initialize database manager
    try:
        db_manager = DatabaseManager()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

    # Create importer
    importer = CSVDomainImporter(
        db_manager=db_manager,
        batch_size=args.batch_size,
        update_existing=args.update_existing,
        dry_run=args.dry_run
    )

    # Run import
    try:
        success = importer.run(
            file_path=args.file,
            has_header=has_header,
            column=args.column
        )

        if success:
            logger.info("Import completed successfully")
            sys.exit(0)
        else:
            logger.error("Import failed or no domains imported")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Import cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db_manager.close_pool()


if __name__ == '__main__':
    main()
