"""
Database operations for the web crawler.
"""

import logging
import psycopg2
from psycopg2 import pool, extras, sql
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from contextlib import contextmanager

from config import Config

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self):
        """Initialize database connection pool."""
        self.connection_pool = None
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Initialize the PostgreSQL connection pool."""
        try:
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                Config.DB_MIN_CONN,
                Config.DB_MAX_CONN,
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Yields:
            Database connection from the pool
        """
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def close_pool(self) -> None:
        """Close all connections in the pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connection pool closed")

    # Company operations

    def get_next_pending_domain(self) -> Optional[Dict]:
        """
        Get the next pending domain to crawl.

        Returns:
            Dictionary with company info or None
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, domain, last_crawled, crawl_status
                    FROM companies
                    WHERE crawl_status = 'pending' AND is_active = true
                    ORDER BY created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                """)
                return cur.fetchone()

    def update_company_status(
        self,
        company_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update company crawl status.

        Args:
            company_id: Company ID
            status: New status
            error_message: Optional error message
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if status == 'completed':
                    cur.execute("""
                        UPDATE companies
                        SET crawl_status = %s,
                            last_crawled = CURRENT_TIMESTAMP,
                            next_crawl_date = CURRENT_TIMESTAMP + INTERVAL '30 days',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (status, company_id))
                else:
                    cur.execute("""
                        UPDATE companies
                        SET crawl_status = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (status, company_id))

                if error_message:
                    logger.error(f"Company {company_id} error: {error_message}")

    def reset_stuck_jobs(self) -> int:
        """
        Reset companies stuck in 'in_progress' status.

        Returns:
            Number of companies reset
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE companies
                    SET crawl_status = 'pending'
                    WHERE crawl_status = 'in_progress'
                    AND updated_at < CURRENT_TIMESTAMP - INTERVAL '1 hour'
                """)
                count = cur.rowcount
                logger.info(f"Reset {count} stuck companies to pending status")
                return count

    # Crawl job operations

    def create_crawl_job(self, company_id: int) -> str:
        """
        Create a new crawl job.

        Args:
            company_id: Company ID

        Returns:
            Job UUID
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO crawl_jobs (company_id, status, started_at)
                    VALUES (%s, 'running', CURRENT_TIMESTAMP)
                    RETURNING job_id
                """, (company_id,))
                job_id = cur.fetchone()[0]
                logger.info(f"Created crawl job {job_id} for company {company_id}")
                return str(job_id)

    def update_crawl_job(
        self,
        job_id: str,
        status: str,
        pages_crawled: int = 0,
        pages_failed: int = 0,
        new_keywords_found: int = 0,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update crawl job status and statistics.

        Args:
            job_id: Job UUID
            status: Job status
            pages_crawled: Number of pages crawled
            pages_failed: Number of pages failed
            new_keywords_found: Number of new keywords found
            error_message: Optional error message
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if status in ('completed', 'failed', 'cancelled'):
                    cur.execute("""
                        UPDATE crawl_jobs
                        SET status = %s,
                            completed_at = CURRENT_TIMESTAMP,
                            pages_crawled = %s,
                            pages_failed = %s,
                            new_keywords_found = %s,
                            error_message = %s
                        WHERE job_id = %s
                    """, (status, pages_crawled, pages_failed, new_keywords_found,
                          error_message, job_id))
                else:
                    cur.execute("""
                        UPDATE crawl_jobs
                        SET status = %s,
                            pages_crawled = %s,
                            pages_failed = %s,
                            new_keywords_found = %s
                        WHERE job_id = %s
                    """, (status, pages_crawled, pages_failed, new_keywords_found, job_id))

    # Section type operations

    def get_section_type_id(self, code: str = 'menu') -> Optional[int]:
        """
        Get section type ID by code.

        Args:
            code: Section type code

        Returns:
            Section type ID or None
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM section_types WHERE code = %s",
                    (code,)
                )
                result = cur.fetchone()
                return result[0] if result else None

    # Keyword operations

    def get_or_create_keyword(self, keyword: str, normalized: str) -> int:
        """
        Get existing keyword ID or create new keyword.

        Args:
            keyword: Original keyword
            normalized: Normalized keyword

        Returns:
            Keyword ID
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Try to get existing keyword
                cur.execute("""
                    SELECT id FROM keywords_master
                    WHERE normalized_keyword = %s
                """, (normalized,))

                result = cur.fetchone()
                if result:
                    return result[0]

                # Create new keyword
                cur.execute("""
                    INSERT INTO keywords_master (keyword, normalized_keyword)
                    VALUES (%s, %s)
                    ON CONFLICT (normalized_keyword) DO UPDATE
                    SET last_seen = CURRENT_TIMESTAMP
                    RETURNING id
                """, (keyword, normalized))

                return cur.fetchone()[0]

    def store_keywords_batch(
        self,
        company_id: int,
        keywords: List[str],
        section_type_id: int
    ) -> Tuple[int, int]:
        """
        Store multiple keywords for a company in batch.

        Args:
            company_id: Company ID
            keywords: List of keywords
            section_type_id: Section type ID

        Returns:
            Tuple of (total_keywords, new_keywords)
        """
        if not keywords:
            return 0, 0

        new_keywords = 0
        total_keywords = len(keywords)

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for keyword in keywords:
                    from utils import normalize_keyword
                    normalized = normalize_keyword(keyword)

                    if not normalized:
                        continue

                    # Get or create keyword in master table
                    keyword_id = self.get_or_create_keyword(keyword, normalized)

                    # Check if this is a new keyword for this company
                    cur.execute("""
                        SELECT id FROM domain_keywords
                        WHERE company_id = %s
                        AND keyword_id = %s
                        AND section_type_id = %s
                    """, (company_id, keyword_id, section_type_id))

                    if cur.fetchone():
                        # Update existing record
                        cur.execute("""
                            UPDATE domain_keywords
                            SET page_count = page_count + 1,
                                total_frequency = total_frequency + 1,
                                last_seen = CURRENT_TIMESTAMP
                            WHERE company_id = %s
                            AND keyword_id = %s
                            AND section_type_id = %s
                        """, (company_id, keyword_id, section_type_id))
                    else:
                        # Insert new record
                        cur.execute("""
                            INSERT INTO domain_keywords
                            (company_id, keyword_id, section_type_id)
                            VALUES (%s, %s, %s)
                        """, (company_id, keyword_id, section_type_id))
                        new_keywords += 1

                # Update keyword statistics
                self._update_keyword_statistics(cur, company_id)

        return total_keywords, new_keywords

    def _update_keyword_statistics(self, cur, company_id: int) -> None:
        """
        Update keyword master statistics.

        Args:
            cur: Database cursor
            company_id: Company ID
        """
        cur.execute("""
            UPDATE keywords_master km
            SET unique_domains_count = (
                    SELECT COUNT(DISTINCT company_id)
                    FROM domain_keywords
                    WHERE keyword_id = km.id
                ),
                total_occurrences = (
                    SELECT COALESCE(SUM(total_frequency), 0)
                    FROM domain_keywords
                    WHERE keyword_id = km.id
                ),
                last_seen = CURRENT_TIMESTAMP
            WHERE id IN (
                SELECT keyword_id
                FROM domain_keywords
                WHERE company_id = %s
            )
        """, (company_id,))

    # Utility operations

    def get_pending_count(self) -> int:
        """
        Get count of pending domains.

        Returns:
            Number of pending domains
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM companies
                    WHERE crawl_status = 'pending' AND is_active = true
                """)
                return cur.fetchone()[0]

    def get_statistics(self) -> Dict:
        """
        Get crawler statistics.

        Returns:
            Dictionary with statistics
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) FILTER (WHERE crawl_status = 'pending') as pending,
                        COUNT(*) FILTER (WHERE crawl_status = 'in_progress') as in_progress,
                        COUNT(*) FILTER (WHERE crawl_status = 'completed') as completed,
                        COUNT(*) FILTER (WHERE crawl_status = 'failed') as failed,
                        COUNT(*) FILTER (WHERE crawl_status = 'paused') as paused,
                        COUNT(*) as total
                    FROM companies
                    WHERE is_active = true
                """)

                stats = cur.fetchone()

                cur.execute("SELECT COUNT(*) FROM keywords_master")
                total_keywords = cur.fetchone()[0]

                cur.execute("""
                    SELECT COUNT(*)
                    FROM crawl_jobs
                    WHERE status = 'running'
                """)
                active_jobs = cur.fetchone()[0]

                return {
                    'pending': stats[0],
                    'in_progress': stats[1],
                    'completed': stats[2],
                    'failed': stats[3],
                    'paused': stats[4],
                    'total': stats[5],
                    'total_keywords': total_keywords,
                    'active_jobs': active_jobs
                }

    def health_check(self) -> bool:
        """
        Check database connection health.

        Returns:
            True if healthy, False otherwise
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return cur.fetchone()[0] == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
