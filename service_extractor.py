"""
Precise service extraction by following navigation links to service pages.

This module extracts service keywords ONLY from explicitly labeled service pages,
using H1 tags, page titles, meta tags, and JSON-LD structured data.
"""

import logging
import re
import json
from typing import List, Dict, Tuple, Optional, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


class NavigationLinkFollower:
    """Identifies service-related links from website navigation."""

    # Service URL patterns (must contain these in the path)
    SERVICE_PATTERNS = [
        '/services', '/solutions', '/products', '/offerings',
        '/what-we-do', '/our-services', '/capabilities', '/expertise'
    ]

    # Exclude patterns (URLs containing these are NOT service pages)
    EXCLUDE_PATTERNS = [
        '/blog', '/news', '/about', '/contact', '/careers',
        '/privacy', '/terms', '/team', '/people', 'pdf', 'download',
        '/events', '/resources', '/case-studies', '/testimonials'
    ]

    @staticmethod
    def is_service_url(url: str) -> bool:
        """
        Check if a URL is service-related.

        Args:
            url: URL to check

        Returns:
            True if URL appears to be a service page
        """
        path = urlparse(url).path.lower()

        # Check exclusions first
        for exclude in NavigationLinkFollower.EXCLUDE_PATTERNS:
            if exclude in path:
                return False

        # Check for service patterns
        for pattern in NavigationLinkFollower.SERVICE_PATTERNS:
            if pattern in path:
                return True

        return False

    @staticmethod
    def classify_service_url(url: str) -> Optional[str]:
        """
        Classify service URL as 'listing' (hub page) or 'detail' (individual service).

        Args:
            url: Service URL to classify

        Returns:
            'service_listing', 'service_detail', or None
        """
        path = urlparse(url).path.lower()

        # Listing pages (hub pages with multiple services)
        listing_indicators = [
            '/services$', '/services/$',
            '/solutions$', '/solutions/$',
            '/products$', '/products/$',
            '/what-we-do$', '/what-we-do/$'
        ]

        for indicator in listing_indicators:
            if re.search(indicator, path):
                return 'service_listing'

        # Detail pages (specific service pages)
        # Examples: /services/consulting, /solutions/cloud-migration
        if any(pattern in path for pattern in NavigationLinkFollower.SERVICE_PATTERNS):
            # Has additional path components after the service indicator
            parts = [p for p in path.split('/') if p]
            if len(parts) >= 2:
                return 'service_detail'

        return None

    @staticmethod
    def find_service_links(html_content: str, base_url: str, max_links: int = 20) -> List[Dict[str, str]]:
        """
        Find service-related links from navigation menu.

        Args:
            html_content: Homepage HTML content
            base_url: Base URL for resolving relative links
            max_links: Maximum number of service links to return

        Returns:
            List of dicts with 'url' and 'type' ('service_listing' or 'service_detail')
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        service_links = []
        seen_urls = set()

        # Find all links in navigation areas
        nav_areas = soup.find_all(['nav', 'header']) + soup.find_all(class_=re.compile('nav|menu'))

        for nav in nav_areas:
            for link in nav.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(base_url, href)

                # Only same-domain URLs
                if urlparse(absolute_url).netloc != urlparse(base_url).netloc:
                    continue

                # Remove fragments and queries for deduplication
                clean_url = absolute_url.split('#')[0].split('?')[0]

                # Skip if already seen
                if clean_url in seen_urls:
                    continue

                # Check if service URL
                if NavigationLinkFollower.is_service_url(clean_url):
                    url_type = NavigationLinkFollower.classify_service_url(clean_url)
                    if url_type:
                        service_links.append({
                            'url': clean_url,
                            'type': url_type,
                            'link_text': link.get_text(strip=True)
                        })
                        seen_urls.add(clean_url)

                        if len(service_links) >= max_links:
                            break

            if len(service_links) >= max_links:
                break

        logger.info(f"Found {len(service_links)} service links")
        return service_links


class ServicePageExtractor:
    """Extracts service keywords from individual service pages."""

    # Generic terms to exclude (not specific service names)
    GENERIC_TERMS = {
        'our services', 'services', 'solutions', 'what we do', 'what we offer',
        'learn more', 'contact us', 'get started', 'view all', 'see all',
        'home', 'back', 'next', 'previous', 'page', 'loading', 'menu'
    }

    # Business/service indicator terms
    SERVICE_INDICATORS = {
        'consulting', 'development', 'management', 'design', 'engineering',
        'assessment', 'analysis', 'integration', 'migration', 'optimization',
        'implementation', 'support', 'planning', 'architecture', 'security',
        'compliance', 'testing', 'training', 'strategy', 'audit', 'review'
    }

    @staticmethod
    def is_valid_service_keyword(text: str) -> bool:
        """
        Validate if text is a valid service keyword.

        Args:
            text: Text to validate

        Returns:
            True if valid service keyword
        """
        if not text or len(text) < 3 or len(text) > 100:
            return False

        # Word count check
        word_count = len(text.split())
        if word_count < 1 or word_count > 8:
            return False

        # Lowercase for checking
        text_lower = text.lower()

        # Exclude generic terms
        if text_lower in ServicePageExtractor.GENERIC_TERMS:
            return False

        # Must contain service indicator OR be a proper noun (capitalized)
        has_indicator = any(term in text_lower for term in ServicePageExtractor.SERVICE_INDICATORS)
        is_proper_noun = any(word[0].isupper() for word in text.split() if word)

        return has_indicator or is_proper_noun

    @staticmethod
    def clean_page_title(title: str, company_name: str = None) -> Optional[str]:
        """
        Clean page title to extract service name.

        Args:
            title: Raw page title
            company_name: Company name to remove

        Returns:
            Cleaned service name or None
        """
        if not title:
            return None

        # Remove company name if provided
        if company_name:
            title = title.replace(company_name, '')

        # Split by common separators and take first part
        separators = [' | ', ' - ', ' — ', ' :: ', ' » ', ' | ']
        for sep in separators:
            if sep in title:
                title = title.split(sep)[0]
                break

        title = title.strip()

        # Validate
        if ServicePageExtractor.is_valid_service_keyword(title):
            return title

        return None

    @staticmethod
    def extract_from_h1(soup: BeautifulSoup) -> List[Tuple[str, float]]:
        """
        Extract service keywords from H1 tags.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of (keyword, confidence_score) tuples
        """
        keywords = []
        h1_tags = soup.find_all('h1')

        for h1 in h1_tags:
            text = h1.get_text(strip=True)
            if ServicePageExtractor.is_valid_service_keyword(text):
                keywords.append((text, 0.95))  # High confidence for H1
                logger.debug(f"Extracted from H1: {text}")

        return keywords

    @staticmethod
    def extract_from_title(soup: BeautifulSoup) -> List[Tuple[str, float]]:
        """
        Extract service keywords from page title.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of (keyword, confidence_score) tuples
        """
        keywords = []
        title_tag = soup.find('title')

        if title_tag:
            title = title_tag.get_text(strip=True)
            cleaned = ServicePageExtractor.clean_page_title(title)
            if cleaned:
                keywords.append((cleaned, 0.90))  # High confidence for title
                logger.debug(f"Extracted from title: {cleaned}")

        return keywords

    @staticmethod
    def extract_from_meta(soup: BeautifulSoup) -> List[Tuple[str, float]]:
        """
        Extract service keywords from meta keywords tag.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of (keyword, confidence_score) tuples
        """
        keywords = []
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})

        if meta_keywords and meta_keywords.get('content'):
            content = meta_keywords['content']
            # Split by comma
            for keyword in content.split(','):
                keyword = keyword.strip()
                if ServicePageExtractor.is_valid_service_keyword(keyword):
                    keywords.append((keyword, 0.85))  # Good confidence for meta
                    logger.debug(f"Extracted from meta: {keyword}")

        return keywords

    @staticmethod
    def extract_from_json_ld(soup: BeautifulSoup) -> List[Tuple[str, float]]:
        """
        Extract service keywords from JSON-LD structured data.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of (keyword, confidence_score) tuples
        """
        keywords = []
        scripts = soup.find_all('script', type='application/ld+json')

        for script in scripts:
            try:
                data = json.loads(script.string)

                # Handle arrays of JSON-LD objects
                if isinstance(data, list):
                    items = data
                else:
                    items = [data]

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    # Look for Service, Product, or Offer types
                    item_type = item.get('@type', '')

                    if item_type in ['Service', 'Product', 'Offer']:
                        name = item.get('name')
                        if name and ServicePageExtractor.is_valid_service_keyword(name):
                            keywords.append((name, 1.0))  # Highest confidence for structured data
                            logger.debug(f"Extracted from JSON-LD: {name}")

            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                logger.debug(f"Error parsing JSON-LD: {e}")
                continue

        return keywords

    @staticmethod
    def extract_keywords(html_content: str, url: str) -> Dict[str, Dict]:
        """
        Extract all service keywords from a service page.

        Args:
            html_content: HTML content of service page
            url: Source URL

        Returns:
            Dict of {keyword: {'confidence': float, 'method': str, 'url': str}}
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        all_keywords = {}

        # Extract from multiple sources
        sources = [
            ('h1', ServicePageExtractor.extract_from_h1(soup)),
            ('title', ServicePageExtractor.extract_from_title(soup)),
            ('meta', ServicePageExtractor.extract_from_meta(soup)),
            ('json_ld', ServicePageExtractor.extract_from_json_ld(soup))
        ]

        for method, keywords in sources:
            for keyword, confidence in keywords:
                # Keep highest confidence if keyword already exists
                if keyword not in all_keywords or all_keywords[keyword]['confidence'] < confidence:
                    all_keywords[keyword] = {
                        'confidence': confidence,
                        'method': method,
                        'url': url
                    }

        return all_keywords


class ServiceListingExtractor:
    """Extracts service names from listing/hub pages."""

    @staticmethod
    def extract_from_service_cards(soup: BeautifulSoup) -> List[Tuple[str, float]]:
        """
        Extract services from service card headings.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of (keyword, confidence_score) tuples
        """
        keywords = []

        # Common service card patterns
        selectors = [
            '.service-card h3', '.service-card h4',
            '.services-list li a', '.services-list li h3',
            '.solution-item .title', '.solution-item h3',
            'article.service h2', 'article.service h3',
            '.offerings-grid .offering-name'
        ]

        for selector in selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if ServicePageExtractor.is_valid_service_keyword(text):
                        keywords.append((text, 0.80))
                        logger.debug(f"Extracted from service card ({selector}): {text}")
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")

        return keywords

    @staticmethod
    def extract_keywords(html_content: str, url: str) -> Dict[str, Dict]:
        """
        Extract service keywords from a listing/hub page.

        Args:
            html_content: HTML content
            url: Source URL

        Returns:
            Dict of {keyword: {'confidence': float, 'method': str, 'url': str}}
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        all_keywords = {}

        # Extract from service cards
        keywords = ServiceListingExtractor.extract_from_service_cards(soup)

        for keyword, confidence in keywords:
            if keyword not in all_keywords:
                all_keywords[keyword] = {
                    'confidence': confidence,
                    'method': 'service_card',
                    'url': url
                }

        return all_keywords
