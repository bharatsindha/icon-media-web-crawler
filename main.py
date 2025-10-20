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

    return parser.parse_args()


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
