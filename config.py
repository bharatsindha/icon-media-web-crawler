"""
Configuration settings for the web crawler.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""

    # Database settings
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME', 'crawler_db')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_MIN_CONN = int(os.getenv('DB_MIN_CONN', 2))
    DB_MAX_CONN = int(os.getenv('DB_MAX_CONN', 10))

    # Crawler settings
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))
    RATE_LIMIT_MIN = float(os.getenv('RATE_LIMIT_MIN', 1.0))
    RATE_LIMIT_MAX = float(os.getenv('RATE_LIMIT_MAX', 2.0))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', 5))

    # User agent
    USER_AGENT = os.getenv(
        'USER_AGENT',
        'Mozilla/5.0 (compatible; MenuCrawler/1.0; +http://example.com/bot)'
    )

    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = os.getenv('LOG_DIR', 'logs')
    LOG_TO_CONSOLE = os.getenv('LOG_TO_CONSOLE', 'true').lower() == 'true'
    LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'

    # Crawler behavior
    RESPECT_ROBOTS_TXT = os.getenv('RESPECT_ROBOTS_TXT', 'true').lower() == 'true'
    FOLLOW_REDIRECTS = os.getenv('FOLLOW_REDIRECTS', 'true').lower() == 'true'
    VERIFY_SSL = os.getenv('VERIFY_SSL', 'true').lower() == 'true'

    # Processing settings
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', 100))
    PROCESS_SEQUENTIAL = os.getenv('PROCESS_SEQUENTIAL', 'true').lower() == 'true'

    # Keyword filtering settings
    ENABLE_KEYWORD_FILTER = os.getenv('ENABLE_KEYWORD_FILTER', 'true').lower() == 'true'
    KEYWORD_EXCLUSIONS_FILE = os.getenv('KEYWORD_EXCLUSIONS_FILE', 'keyword_exclusions.yaml')

    @classmethod
    def get_db_connection_string(cls):
        """Get PostgreSQL connection string."""
        return (
            f"host={cls.DB_HOST} port={cls.DB_PORT} "
            f"dbname={cls.DB_NAME} user={cls.DB_USER} "
            f"password={cls.DB_PASSWORD}"
        )

    @classmethod
    def validate(cls):
        """Validate configuration."""
        required = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing = []

        for var in required:
            if not getattr(cls, var):
                missing.append(var)

        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}"
            )
