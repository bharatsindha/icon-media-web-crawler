"""
Utility functions for the web crawler.
"""

import re
import time
import random
import logging
from typing import Optional, Set
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)


def normalize_keyword(keyword: str) -> str:
    """
    Normalize a keyword by converting to lowercase, removing special characters,
    and trimming whitespace.

    Args:
        keyword: The keyword to normalize

    Returns:
        Normalized keyword string
    """
    if not keyword:
        return ""

    # Convert to lowercase
    normalized = keyword.lower()

    # Remove special characters but keep spaces, hyphens, and underscores
    normalized = re.sub(r'[^\w\s\-]', '', normalized)

    # Replace multiple spaces with single space
    normalized = re.sub(r'\s+', ' ', normalized)

    # Trim whitespace
    normalized = normalized.strip()

    return normalized


def normalize_domain(url: str) -> str:
    """
    Extract and normalize domain from URL.

    Args:
        url: Full URL or domain

    Returns:
        Normalized domain (e.g., 'example.com')
    """
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    # Remove www. prefix
    if domain.startswith('www.'):
        domain = domain[4:]

    return domain


def build_full_url(domain: str, path: str = '') -> str:
    """
    Build a full URL from domain and optional path.

    Args:
        domain: Domain name
        path: Optional path

    Returns:
        Full URL with https protocol
    """
    if not domain.startswith(('http://', 'https://')):
        domain = 'https://' + domain

    if path:
        return urljoin(domain, path)

    return domain


def rate_limit_delay(min_delay: float = 1.0, max_delay: float = 2.0) -> None:
    """
    Add a random delay for rate limiting.

    Args:
        min_delay: Minimum delay in seconds
        max_delay: Maximum delay in seconds
    """
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)


def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid.

    Args:
        url: URL to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def check_robots_txt(url: str, user_agent: str) -> bool:
    """
    Check if crawling is allowed by robots.txt.

    Args:
        url: URL to check
        user_agent: User agent string

    Returns:
        True if allowed, False if disallowed
    """
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()

        return rp.can_fetch(user_agent, url)
    except Exception as e:
        logger.warning(f"Error checking robots.txt for {url}: {e}")
        # If we can't read robots.txt, allow crawling
        return True


def extract_keywords_from_text(text: str, min_length: int = 2) -> Set[str]:
    """
    Extract individual keywords from text.

    Args:
        text: Text to extract keywords from
        min_length: Minimum keyword length

    Returns:
        Set of normalized keywords
    """
    if not text:
        return set()

    keywords = set()

    # Split by common separators
    parts = re.split(r'[,|/\n\t]', text)

    for part in parts:
        normalized = normalize_keyword(part)
        if len(normalized) >= min_length:
            keywords.add(normalized)

    return keywords


def sanitize_text(text: str) -> str:
    """
    Sanitize text by removing extra whitespace and special characters.

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def get_domain_from_url(url: str) -> Optional[str]:
    """
    Extract domain from a full URL.

    Args:
        url: Full URL

    Returns:
        Domain or None if invalid
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc

        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]

        return domain.lower()
    except Exception:
        return None


class RateLimiter:
    """Simple rate limiter to control request frequency."""

    def __init__(self, min_delay: float = 1.0, max_delay: float = 2.0):
        """
        Initialize rate limiter.

        Args:
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0

    def wait(self) -> None:
        """Wait for rate limit before next request."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time

        delay = random.uniform(self.min_delay, self.max_delay)

        if elapsed < delay:
            time.sleep(delay - elapsed)

        self.last_request_time = time.time()


class ProgressTracker:
    """Track crawler progress."""

    def __init__(self, total: int = 0):
        """
        Initialize progress tracker.

        Args:
            total: Total number of items to process
        """
        self.total = total
        self.processed = 0
        self.successful = 0
        self.failed = 0
        self.start_time = time.time()

    def update(self, success: bool = True) -> None:
        """
        Update progress counters.

        Args:
            success: Whether the operation was successful
        """
        self.processed += 1
        if success:
            self.successful += 1
        else:
            self.failed += 1

    def get_stats(self) -> dict:
        """
        Get current statistics.

        Returns:
            Dictionary with progress statistics
        """
        elapsed = time.time() - self.start_time
        rate = self.processed / elapsed if elapsed > 0 else 0

        return {
            'total': self.total,
            'processed': self.processed,
            'successful': self.successful,
            'failed': self.failed,
            'progress_pct': (self.processed / self.total * 100) if self.total > 0 else 0,
            'elapsed_time': elapsed,
            'rate_per_second': rate,
            'estimated_remaining': (self.total - self.processed) / rate if rate > 0 else 0
        }

    def __str__(self) -> str:
        """String representation of progress."""
        stats = self.get_stats()
        return (
            f"Progress: {self.processed}/{self.total} "
            f"({stats['progress_pct']:.1f}%) - "
            f"Success: {self.successful}, Failed: {self.failed} - "
            f"Rate: {stats['rate_per_second']:.2f}/s"
        )
