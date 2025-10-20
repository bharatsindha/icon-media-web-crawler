"""
Database migration management script for web crawler.

Usage:
    python migrate.py status          # Show migration status
    python migrate.py up              # Run all pending migrations
    python migrate.py up --steps=1    # Run next migration only
    python migrate.py down --steps=1  # Rollback last migration
    python migrate.py reset           # Rollback all and re-run
    python migrate.py create <name>   # Create new migration file
"""

import os
import sys
import re
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

# Try to import psycopg3 first, fall back to psycopg2
try:
    import psycopg
    from psycopg import sql
    PSYCOPG_VERSION = 3
except ImportError:
    import psycopg2 as psycopg
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    PSYCOPG_VERSION = 2

from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database migrations."""

    MIGRATIONS_DIR = 'migrations'
    MIGRATIONS_TABLE = 'schema_migrations'

    def __init__(self):
        """Initialize migration manager."""
        self.conn = None
        self.migrations_dir = Path(self.MIGRATIONS_DIR)

        # Validate migrations directory exists
        if not self.migrations_dir.exists():
            logger.error(f"Migrations directory '{self.MIGRATIONS_DIR}' not found")
            sys.exit(1)

    def connect(self) -> None:
        """Connect to PostgreSQL database."""
        try:
            if PSYCOPG_VERSION == 3:
                conninfo = (
                    f"host={Config.DB_HOST} port={Config.DB_PORT} "
                    f"dbname={Config.DB_NAME} user={Config.DB_USER} "
                    f"password={Config.DB_PASSWORD}"
                )
                self.conn = psycopg.connect(conninfo, autocommit=True)
            else:
                self.conn = psycopg.connect(
                    host=Config.DB_HOST,
                    port=Config.DB_PORT,
                    database=Config.DB_NAME,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD
                )
            logger.info(f"Database connection established (psycopg{PSYCOPG_VERSION})")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            sys.exit(1)

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def ensure_migrations_table(self) -> None:
        """Create migrations tracking table if it doesn't exist."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.MIGRATIONS_TABLE} (
                        id SERIAL PRIMARY KEY,
                        migration VARCHAR(255) UNIQUE NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        execution_time_ms INTEGER,
                        checksum VARCHAR(64)
                    )
                """)

                # Create index
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.MIGRATIONS_TABLE}_migration
                    ON {self.MIGRATIONS_TABLE}(migration)
                """)

                self.conn.commit()
                logger.info("Migrations table verified")

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to create migrations table: {e}")
            raise

    def get_migration_files(self) -> List[str]:
        """
        Get all migration files in order.

        Returns:
            List of migration filenames
        """
        migrations = []
        for file in sorted(self.migrations_dir.glob('*.sql')):
            migrations.append(file.name)
        return migrations

    def get_applied_migrations(self) -> List[str]:
        """
        Get list of applied migrations.

        Returns:
            List of applied migration names
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(f"""
                    SELECT migration
                    FROM {self.MIGRATIONS_TABLE}
                    ORDER BY migration
                """)
                return [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get applied migrations: {e}")
            return []

    def get_pending_migrations(self) -> List[str]:
        """
        Get list of pending migrations.

        Returns:
            List of pending migration filenames
        """
        all_migrations = self.get_migration_files()
        applied = self.get_applied_migrations()
        return [m for m in all_migrations if m not in applied]

    def read_migration_file(self, filename: str) -> str:
        """
        Read migration file content.

        Args:
            filename: Migration filename

        Returns:
            SQL content
        """
        filepath = self.migrations_dir / filename
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read migration file {filename}: {e}")
            raise

    def apply_migration(self, migration_name: str) -> bool:
        """
        Apply a single migration.

        Args:
            migration_name: Name of migration file

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Applying migration: {migration_name}")

        try:
            # Read migration SQL
            sql_content = self.read_migration_file(migration_name)

            # Record start time
            start_time = datetime.now()

            # Execute migration
            with self.conn.cursor() as cur:
                # Execute the migration SQL
                cur.execute(sql_content)

            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            # Record migration as applied
            with self.conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {self.MIGRATIONS_TABLE}
                    (migration, execution_time_ms)
                    VALUES (%s, %s)
                """, (migration_name, int(execution_time)))

            self.conn.commit()

            logger.info(
                f"Migration {migration_name} applied successfully "
                f"(took {execution_time:.0f}ms)"
            )
            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to apply migration {migration_name}: {e}")
            return False

    def rollback_migration(self, migration_name: str) -> bool:
        """
        Rollback a migration.

        Args:
            migration_name: Name of migration to rollback

        Returns:
            True if successful, False otherwise
        """
        logger.warning(f"Rolling back migration: {migration_name}")

        try:
            # Check if rollback file exists
            rollback_file = migration_name.replace('.sql', '_down.sql')
            rollback_path = self.migrations_dir / rollback_file

            if rollback_path.exists():
                # Execute rollback SQL
                sql_content = self.read_migration_file(rollback_file)

                with self.conn.cursor() as cur:
                    cur.execute(sql_content)

                logger.info(f"Executed rollback script: {rollback_file}")
            else:
                logger.warning(
                    f"No rollback script found for {migration_name}. "
                    "Skipping rollback execution."
                )

            # Remove from migrations table
            with self.conn.cursor() as cur:
                cur.execute(f"""
                    DELETE FROM {self.MIGRATIONS_TABLE}
                    WHERE migration = %s
                """, (migration_name,))

            self.conn.commit()
            logger.info(f"Migration {migration_name} rolled back successfully")
            return True

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to rollback migration {migration_name}: {e}")
            return False

    def migrate_up(self, steps: Optional[int] = None) -> None:
        """
        Run pending migrations.

        Args:
            steps: Number of migrations to run (None = all)
        """
        pending = self.get_pending_migrations()

        if not pending:
            logger.info("No pending migrations")
            return

        # Limit to specified steps
        if steps:
            pending = pending[:steps]

        logger.info(f"Running {len(pending)} migration(s)")

        success_count = 0
        for migration in pending:
            if self.apply_migration(migration):
                success_count += 1
            else:
                logger.error("Migration failed. Stopping.")
                break

        logger.info(f"Applied {success_count}/{len(pending)} migration(s)")

    def migrate_down(self, steps: int = 1) -> None:
        """
        Rollback migrations.

        Args:
            steps: Number of migrations to rollback
        """
        applied = self.get_applied_migrations()

        if not applied:
            logger.info("No migrations to rollback")
            return

        # Get last N migrations to rollback
        to_rollback = list(reversed(applied[-steps:]))

        logger.info(f"Rolling back {len(to_rollback)} migration(s)")

        success_count = 0
        for migration in to_rollback:
            if self.rollback_migration(migration):
                success_count += 1
            else:
                logger.error("Rollback failed. Stopping.")
                break

        logger.info(f"Rolled back {success_count}/{len(to_rollback)} migration(s)")

    def show_status(self) -> None:
        """Display migration status."""
        all_migrations = self.get_migration_files()
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()

        print("\n" + "=" * 70)
        print("DATABASE MIGRATION STATUS")
        print("=" * 70)

        print(f"\nDatabase: {Config.DB_NAME}@{Config.DB_HOST}")
        print(f"Total migrations: {len(all_migrations)}")
        print(f"Applied: {len(applied)}")
        print(f"Pending: {len(pending)}")

        if applied:
            print("\n" + "-" * 70)
            print("APPLIED MIGRATIONS:")
            print("-" * 70)

            # Get detailed info from database
            with self.conn.cursor() as cur:
                cur.execute(f"""
                    SELECT migration, applied_at, execution_time_ms
                    FROM {self.MIGRATIONS_TABLE}
                    ORDER BY migration
                """)
                for row in cur.fetchall():
                    status = "✓"
                    time_str = f"{row[2]}ms" if row[2] else "N/A"
                    print(f"  {status} {row[0]:<40} (applied: {row[1]}, took: {time_str})")

        if pending:
            print("\n" + "-" * 70)
            print("PENDING MIGRATIONS:")
            print("-" * 70)
            for migration in pending:
                print(f"  ○ {migration}")

        print("\n" + "=" * 70 + "\n")

    def reset(self) -> None:
        """Reset database by rolling back all migrations and re-running."""
        logger.warning("Resetting database (rollback all + re-run)")

        # Confirm action
        response = input("This will rollback ALL migrations. Continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            logger.info("Reset cancelled")
            return

        # Rollback all
        applied = self.get_applied_migrations()
        if applied:
            logger.info(f"Rolling back {len(applied)} migration(s)")
            self.migrate_down(len(applied))

        # Re-run all
        logger.info("Re-running all migrations")
        self.migrate_up()

    def create_migration(self, name: str) -> None:
        """
        Create a new migration file.

        Args:
            name: Migration name (will be prefixed with number)
        """
        # Get next migration number
        existing = self.get_migration_files()
        if existing:
            # Extract number from last migration
            last = existing[-1]
            match = re.match(r'^(\d+)_', last)
            if match:
                next_num = int(match.group(1)) + 1
            else:
                next_num = 1
        else:
            next_num = 1

        # Format number with leading zeros
        num_str = f"{next_num:03d}"

        # Clean name (remove special chars, replace spaces with underscores)
        clean_name = re.sub(r'[^\w\s-]', '', name)
        clean_name = re.sub(r'[-\s]+', '_', clean_name)

        # Create filenames
        up_filename = f"{num_str}_{clean_name}.sql"
        down_filename = f"{num_str}_{clean_name}_down.sql"

        up_path = self.migrations_dir / up_filename
        down_path = self.migrations_dir / down_filename

        # Create up migration template
        up_template = f"""-- Migration: {up_filename}
-- Description: {name}
-- Date: {datetime.now().strftime('%Y-%m-%d')}

-- Add your migration SQL here

-- Example:
-- CREATE TABLE example (
--     id SERIAL PRIMARY KEY,
--     name VARCHAR(255) NOT NULL
-- );

DO $$
BEGIN
    RAISE NOTICE 'Migration {up_filename} completed successfully';
END $$;
"""

        # Create down migration template
        down_template = f"""-- Rollback: {down_filename}
-- Description: Rollback for {name}
-- Date: {datetime.now().strftime('%Y-%m-%d')}

-- Add your rollback SQL here

-- Example:
-- DROP TABLE IF EXISTS example;

DO $$
BEGIN
    RAISE NOTICE 'Rollback {down_filename} completed successfully';
END $$;
"""

        # Write files
        try:
            with open(up_path, 'w', encoding='utf-8') as f:
                f.write(up_template)

            with open(down_path, 'w', encoding='utf-8') as f:
                f.write(down_template)

            logger.info(f"Created migration files:")
            logger.info(f"  Up:   {up_filename}")
            logger.info(f"  Down: {down_filename}")

        except Exception as e:
            logger.error(f"Failed to create migration files: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Database migration manager')
    parser.add_argument(
        'command',
        choices=['status', 'up', 'down', 'reset', 'create'],
        help='Migration command'
    )
    parser.add_argument(
        'name',
        nargs='?',
        help='Migration name (for create command)'
    )
    parser.add_argument(
        '--steps',
        type=int,
        help='Number of migrations to apply/rollback'
    )

    args = parser.parse_args()

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Initialize migration manager
    manager = MigrationManager()

    try:
        # Connect to database
        manager.connect()

        # Ensure migrations table exists (except for create command)
        if args.command != 'create':
            manager.ensure_migrations_table()

        # Execute command
        if args.command == 'status':
            manager.show_status()

        elif args.command == 'up':
            manager.migrate_up(steps=args.steps)
            manager.show_status()

        elif args.command == 'down':
            steps = args.steps if args.steps else 1
            manager.migrate_down(steps=steps)
            manager.show_status()

        elif args.command == 'reset':
            manager.reset()
            manager.show_status()

        elif args.command == 'create':
            if not args.name:
                logger.error("Migration name required for 'create' command")
                sys.exit(1)
            manager.create_migration(args.name)

    except Exception as e:
        logger.error(f"Migration error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        manager.close()


if __name__ == '__main__':
    main()
