"""
Main entry point for the web crawler application.
"""

import os
import sys
import signal
import logging
import argparse
from datetime import datetime
from pathlib import Path

from config import Config
from database import DatabaseManager
from crawler import WebCrawler


def setup_logging():
    """Configure logging for the application."""
    # Create logs directory if it doesn't exist
    if Config.LOG_TO_FILE:
        log_dir = Path(Config.LOG_DIR)
        log_dir.mkdir(exist_ok=True)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    if Config.LOG_TO_CONSOLE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler (daily rotation)
    if Config.LOG_TO_FILE:
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = Path(Config.LOG_DIR) / f'crawler_{today}.log'

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def signal_handler(signum, frame):
    """
    Handle shutdown signals gracefully.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")

    # Signal crawler to stop
    if hasattr(signal_handler, 'crawler'):
        signal_handler.crawler.stop()


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Web crawler for extracting navigation menu keywords',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Batch mode - crawl all pending domains
  python main.py

  # On-demand mode - crawl specific domain
  python main.py --domain example.com
  python main.py -d example.com

  # On-demand with verbose logging
  python main.py --domain example.com --verbose
        """
    )

    parser.add_argument(
        '-d', '--domain',
        help='Crawl a specific domain on-demand (bypasses status checks)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )

    parser.add_argument(
        '--extract-services',
        action='store_true',
        help='Extract service keywords by following navigation links to service pages'
    )

    return parser.parse_args()


def crawl_services_on_demand(crawler, db_manager, domain: str) -> bool:
    """
    Crawl services for a specific domain on-demand.

    Args:
        crawler: WebCrawler instance
        db_manager: DatabaseManager instance
        domain: Domain to crawl

    Returns:
        True if successful, False otherwise
    """
    from utils import normalize_domain

    logger = logging.getLogger(__name__)
    logger.info(f"On-demand service extraction requested for: {domain}")

    # Normalize the domain
    normalized_domain = normalize_domain(domain)
    logger.info(f"Normalized domain: {normalized_domain}")

    # Check if domain exists in database
    company = db_manager.get_company_by_domain(normalized_domain)

    if not company:
        logger.error(f"Domain not found in database: {normalized_domain}")
        logger.error("Please add the domain first using add_domains.py or import_companies.py")
        return False

    company_id = company['id']
    current_status = company['crawl_status']

    logger.info(f"Found company ID: {company_id}")
    logger.info(f"Current status: {current_status}")
    logger.info(f"Last crawled: {company.get('last_crawled', 'Never')}")

    # Force crawl regardless of current status
    logger.info("Forcing service extraction (bypassing status check)")

    try:
        # Update status to in_progress
        db_manager.update_company_status(company_id, 'in_progress')

        # Create crawl job
        job_id = db_manager.create_crawl_job(company_id)
        logger.info(f"Created crawl job: {job_id}")

        # First, extract menu keywords
        logger.info("Step 1: Extracting navigation menu keywords...")
        menu_result = crawler.crawl_domain(normalized_domain, company_id)

        # Then, extract service keywords
        logger.info("Step 2: Extracting service keywords from dedicated pages...")
        service_result = crawler.crawl_services(normalized_domain, company_id)

        # Combine results
        result = {
            'success': menu_result['success'] and service_result['success'],
            'menu_keywords': menu_result['keywords_found'],
            'menu_new': menu_result['new_keywords'],
            'service_keywords': service_result['keywords_found'],
            'service_new': service_result['new_keywords'],
            'service_links_found': service_result['service_links_found'],
            'pages_crawled': menu_result['pages_crawled'] + service_result['pages_crawled'],
            'pages_failed': menu_result['pages_failed'] + service_result['pages_failed'],
            'error': menu_result.get('error') or service_result.get('error'),
            'keywords_found': menu_result['keywords_found'] + service_result['keywords_found'],
            'new_keywords': menu_result['new_keywords'] + service_result['new_keywords']
        }

        # Update job and company status
        if result['success']:
            db_manager.update_crawl_job(
                job_id,
                'completed',
                pages_crawled=result['pages_crawled'],
                pages_failed=result['pages_failed'],
                new_keywords_found=result['new_keywords']
            )
            db_manager.update_company_status(company_id, 'completed')

            # Print summary
            print("\n" + "=" * 70)
            print("COMPLETE EXTRACTION RESULTS")
            print("=" * 70)
            print(f"Domain:              {normalized_domain}")
            print(f"Status:              SUCCESS")
            print()
            print("Menu Extraction:")
            print(f"  Keywords found:    {result['menu_keywords']}")
            print(f"  New keywords:      {result['menu_new']}")
            print()
            print("Service Extraction:")
            print(f"  Service links:     {result['service_links_found']}")
            print(f"  Keywords found:    {result['service_keywords']}")
            print(f"  New keywords:      {result['service_new']}")
            print()
            print("Total:")
            print(f"  Keywords found:    {result['keywords_found']}")
            print(f"  New keywords:      {result['new_keywords']}")
            print(f"  Pages crawled:     {result['pages_crawled']}")
            print(f"  Pages failed:      {result['pages_failed']}")
            print(f"Job ID:              {job_id}")
            print("=" * 70 + "\n")

            return True
        else:
            db_manager.update_crawl_job(
                job_id,
                'failed',
                pages_crawled=result['pages_crawled'],
                pages_failed=result['pages_failed'],
                error_message=result['error']
            )
            db_manager.update_company_status(
                company_id,
                'failed',
                error_message=result['error']
            )

            # Print error summary
            print("\n" + "=" * 70)
            print("COMPLETE EXTRACTION RESULTS")
            print("=" * 70)
            print(f"Domain:              {normalized_domain}")
            print(f"Status:              FAILED")
            print(f"Error:               {result['error']}")
            print(f"Job ID:              {job_id}")
            print("=" * 70 + "\n")

            return False

    except Exception as e:
        logger.error(f"Error during service extraction: {e}", exc_info=True)
        db_manager.update_company_status(
            company_id,
            'failed',
            error_message=str(e)
        )
        return False


def main():
    """Main application entry point."""
    # Parse command line arguments
    args = parse_arguments()

    # Setup logging
    if args.verbose:
        Config.LOG_LEVEL = 'DEBUG'

    logger = setup_logging()
    logger.info("=" * 80)
    if args.domain:
        logger.info(f"Web Crawler - On-Demand Mode (Domain: {args.domain})")
    else:
        logger.info("Web Crawler - Batch Mode")
    logger.info("=" * 80)

    # Validate configuration
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Initialize database manager
    db_manager = None
    crawler = None

    try:
        logger.info("Initializing database connection...")
        db_manager = DatabaseManager()

        # Health check
        if not db_manager.health_check():
            logger.error("Database health check failed")
            sys.exit(1)

        logger.info("Database connection established successfully")

        # Get initial statistics
        stats = db_manager.get_statistics()
        logger.info(
            f"Initial Stats - Total: {stats['total']}, "
            f"Pending: {stats['pending']}, "
            f"Completed: {stats['completed']}, "
            f"Failed: {stats['failed']}, "
            f"Keywords: {stats['total_keywords']}"
        )

        # Initialize crawler
        logger.info("Initializing web crawler...")
        crawler = WebCrawler(db_manager)

        # Register signal handlers for graceful shutdown
        signal_handler.crawler = crawler
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run crawler in appropriate mode
        if args.domain:
            # On-demand mode: crawl specific domain
            if args.extract_services:
                logger.info(f"Starting service extraction for: {args.domain}")
                success = crawl_services_on_demand(crawler, db_manager, args.domain)
            else:
                logger.info(f"Starting on-demand crawl for: {args.domain}")
                success = crawler.crawl_single_domain(args.domain)

            if success:
                logger.info(f"Successfully crawled {args.domain}")
            else:
                logger.error(f"Failed to crawl {args.domain}")
                sys.exit(1)
        else:
            # Batch mode: crawl all pending domains
            logger.info("Starting batch crawl process...")
            crawler.run()
            logger.info("Batch crawl process completed successfully")

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        # Cleanup
        logger.info("Cleaning up resources...")

        if crawler:
            crawler.close()

        if db_manager:
            db_manager.close_pool()

        logger.info("=" * 80)
        logger.info("Web Crawler Application Shutdown Complete")
        logger.info("=" * 80)


if __name__ == '__main__':
    main()
