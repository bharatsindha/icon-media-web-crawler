"""
Utility functions for the web crawler.
"""

import re
import time
import random
import logging
import yaml
from pathlib import Path
from typing import Optional, Set, List, Dict
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from fnmatch import fnmatch

logger = logging.getLogger(__name__)


# Special character replacements for normalization
SPECIAL_CHAR_REPLACEMENTS = {
    '&': ' and ',
    '/': ' or ',
    '+': ' plus ',
    '@': ' at ',
    '#': ' number ',
    '%': ' percent ',
}


def normalize_keyword(keyword: str) -> str:
    """
    Normalize a keyword by converting to lowercase, replacing special characters
    with text equivalents, and trimming whitespace.

    The original keyword is preserved separately. This normalized version is used
    for deduplication and search.

    Special character replacements:
    - & → and
    - / → or
    - + → plus
    - @ → at
    - # → number
    - % → percent

    Args:
        keyword: The keyword to normalize

    Returns:
        Normalized keyword string
    """
    if not keyword:
        return ""

    # Convert to lowercase
    normalized = keyword.lower()

    # Replace special characters with text equivalents
    for char, replacement in SPECIAL_CHAR_REPLACEMENTS.items():
        normalized = normalized.replace(char, replacement)

    # Remove remaining special characters but keep spaces, hyphens, and underscores
    normalized = re.sub(r'[^\w\s\-]', '', normalized)

    # Replace multiple spaces with single space
    normalized = re.sub(r'\s+', ' ', normalized)

    # Replace multiple hyphens with single hyphen
    normalized = re.sub(r'-+', '-', normalized)

    # Trim whitespace and hyphens
    normalized = normalized.strip().strip('-')

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
    Extract individual keywords from text, preserving original text.

    This function extracts keywords while preserving special characters
    and original capitalization. Normalization happens later in the
    database layer to separate original from normalized keywords.

    Args:
        text: Text to extract keywords from
        min_length: Minimum keyword length

    Returns:
        Set of original keywords (not normalized)
    """
    if not text:
        return set()

    keywords = set()

    # Split by common separators
    parts = re.split(r'[,|\n\t]', text)

    for part in parts:
        # Only do minimal cleanup - preserve original text and special chars
        cleaned = part.strip()

        # Remove leading/trailing punctuation but keep internal special chars
        cleaned = cleaned.strip('.,;:!?\'"`()[]{}')

        if len(cleaned) >= min_length and cleaned:
            keywords.add(cleaned)

    return keywords


def sanitize_text(text: str) -> str:
    """
    Sanitize text by removing extra whitespace and special characters.
    Enhanced to handle malformed keywords from web extraction.

    Args:
        text: Text to sanitize

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # 1. Add space between camelCase words (e.g., "SurveysUsing" → "Surveys Using")
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

    # 2. Remove multiple dashes/em-dashes (formatting artifacts)
    text = re.sub(r'[-—]{2,}', ' ', text)

    # 3. Truncate at email addresses (contact info shouldn't be in keywords)
    if '@' in text:
        text = text.split('@')[0].strip()

    # 4. Truncate at phone numbers (various formats)
    # Match patterns like: 555-1234, 555.1234, (555) 1234
    phone_match = re.search(r'\d{3}[-.\s)]\d{3,4}', text)
    if phone_match:
        text = text[:phone_match.start()].strip()

    # 5. Remove excessive punctuation
    text = re.sub(r'[.]{2,}', '', text)  # Multiple periods
    text = re.sub(r'[!]{2,}', '', text)  # Multiple exclamation marks

    # 6. Clean up whitespace
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces → single space
    text = text.strip()  # Leading/trailing whitespace

    # 7. Remove leading/trailing punctuation (but preserve internal)
    text = text.strip('.,;:!?\'"`()[]{}')

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


class KeywordFilter:
    """Filter keywords based on exclusion rules."""

    def __init__(self, config_file: str = 'keyword_exclusions.yaml'):
        """
        Initialize keyword filter.

        Args:
            config_file: Path to YAML configuration file
        """
        self.config_file = config_file
        self.enabled = True
        self.case_insensitive = True
        self.log_excluded = True
        self.min_length = 2
        self.max_length = 50
        self.exclusions = set()
        self.patterns = []
        self.excluded_count = 0

        self._load_config()

    def _load_config(self) -> None:
        """Load exclusion configuration from YAML file."""
        config_path = Path(self.config_file)

        if not config_path.exists():
            logger.warning(f"Keyword exclusion config not found: {self.config_file}")
            logger.info("Keyword filtering disabled")
            self.enabled = False
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Load configuration options
            if 'config' in config:
                cfg = config['config']
                self.enabled = cfg.get('enabled', True)
                self.case_insensitive = cfg.get('case_insensitive', True)
                self.log_excluded = cfg.get('log_excluded', True)
                self.min_length = cfg.get('min_length', 2)
                self.max_length = cfg.get('max_length', 50)

            if not self.enabled:
                logger.info("Keyword filtering disabled by configuration")
                return

            # Load exclusion categories
            for category in ['navigation', 'legal', 'support', 'social',
                           'authentication', 'locale', 'actions', 'footer', 'utility']:
                if category in config and config[category]:
                    for term in config[category]:
                        if self.case_insensitive:
                            term = term.lower()
                        self.exclusions.add(term)

            # Load patterns
            if 'patterns' in config and config['patterns']:
                self.patterns = config['patterns']
                if self.case_insensitive:
                    self.patterns = [p.lower() for p in self.patterns]

            logger.info(
                f"Loaded {len(self.exclusions)} exclusion terms and "
                f"{len(self.patterns)} patterns from {self.config_file}"
            )

        except Exception as e:
            logger.error(f"Error loading keyword exclusion config: {e}")
            self.enabled = False

    def should_exclude(self, keyword: str) -> bool:
        """
        Check if a keyword should be excluded.

        Args:
            keyword: Keyword to check

        Returns:
            True if keyword should be excluded, False otherwise
        """
        if not self.enabled:
            return False

        if not keyword:
            return True

        # Check length
        if len(keyword) < self.min_length or len(keyword) > self.max_length:
            return True

        # Prepare keyword for comparison
        check_keyword = keyword.lower() if self.case_insensitive else keyword

        # Check exact matches
        if check_keyword in self.exclusions:
            if self.log_excluded:
                logger.debug(f"Excluded (exact match): '{keyword}'")
                self.excluded_count += 1
            return True

        # Check patterns
        for pattern in self.patterns:
            if fnmatch(check_keyword, pattern):
                if self.log_excluded:
                    logger.debug(f"Excluded (pattern '{pattern}'): '{keyword}'")
                    self.excluded_count += 1
                return True

        return False

    def filter_keywords(self, keywords: Set[str]) -> Set[str]:
        """
        Filter a set of keywords, removing excluded ones.

        Args:
            keywords: Set of keywords to filter

        Returns:
            Filtered set of keywords
        """
        if not self.enabled:
            return keywords

        filtered = {kw for kw in keywords if not self.should_exclude(kw)}

        excluded_count = len(keywords) - len(filtered)
        if excluded_count > 0:
            logger.info(
                f"Filtered {excluded_count} non-business keywords "
                f"({len(filtered)} remaining)"
            )

        return filtered

    def get_stats(self) -> Dict:
        """
        Get filtering statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            'enabled': self.enabled,
            'total_exclusions': len(self.exclusions),
            'total_patterns': len(self.patterns),
            'excluded_count': self.excluded_count
        }
