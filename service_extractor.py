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
from utils import sanitize_text

logger = logging.getLogger(__name__)


class NavigationLinkFollower:
    """Identifies business offering links from website navigation (industry-agnostic)."""

    # Expanded URL patterns for ALL types of business offerings
    OFFERING_PATTERNS = [
        # Core offering pages (both singular and plural - with leading slash)
        '/services', '/service',  # Many sites use singular
        '/solutions', '/solution',
        '/products', '/product',
        '/offerings', '/offering',
        '/capabilities', '/capability',
        '/expertise', '/what-we-do', '/our-work',

        # Additional common patterns (from accuracy analysis)
        '/practices', '/practice',  # Professional services, law firms
        '/areas', '/area',          # Practice areas, service areas
        '/industries', '/industry',  # Industry/sector-specific service pages
        '/specialties', '/specialty',  # Medical, professional specializations

        # Technology & platforms
        '/platforms', '/technologies', '/applications', '/tools',
        '/software', '/systems', '/integrations', '/apis',

        # Portfolio & work samples
        '/portfolio', '/projects', '/work', '/our-solutions',

        # Industry-specific patterns
        '/practice-areas',  # Legal
        '/treatments', '/procedures',  # Healthcare
        '/programs', '/courses', '/training',  # Education
        '/packages', '/plans', '/pricing',  # Service tiers
        '/brands', '/collections', '/catalog',  # Retail/Manufacturing
        '/methodologies', '/frameworks', '/approaches',  # Consulting

        # Compound URL patterns (without leading slash to catch /environmental-services, /managed-services, etc.)
        # These catch URLs like /environmental-services, /professional-solutions, /technical-products
        'services', 'service',
        'solutions', 'solution',
        'products', 'product',
        'offerings', 'offering',
        'capabilities', 'capability',
        'practices', 'practice',
        'specialties', 'specialty',
        'platforms', 'platform',
        'technologies', 'technology',
        'applications', 'application',
    ]

    # Exclude patterns (URLs containing these are NOT offering pages)
    EXCLUDE_PATTERNS = [
        '/blog', '/news', '/about', '/contact', '/careers', '/jobs',
        '/privacy', '/terms', '/team', '/people', '/leadership',
        '/events', '/webinars', '/resources', '/downloads',
        '/case-studies', '/testimonials', '/reviews', '/clients',
        '/investors', '/press', '/media', '/faq', '/support',
        'pdf', 'download', '.jpg', '.png', '.mp4', '/search'
    ]

    @staticmethod
    def is_offering_url(url: str) -> bool:
        """
        Check if a URL is offering-related (industry-agnostic).

        Args:
            url: URL to check

        Returns:
            True if URL appears to be an offering page
        """
        path = urlparse(url).path.lower()

        # Check exclusions first
        for exclude in NavigationLinkFollower.EXCLUDE_PATTERNS:
            if exclude in path:
                return False

        # Check for offering patterns
        for pattern in NavigationLinkFollower.OFFERING_PATTERNS:
            if pattern in path:
                return True

        return False

    # Backward compatibility
    @staticmethod
    def is_service_url(url: str) -> bool:
        """Backward compatibility wrapper."""
        return NavigationLinkFollower.is_offering_url(url)

    @staticmethod
    def classify_offering_url(url: str) -> Optional[str]:
        """
        Classify offering URL as 'listing' (hub page) or 'detail' (individual offering).

        Args:
            url: Offering URL to classify

        Returns:
            'service_listing', 'service_detail', or None
        """
        path = urlparse(url).path.lower()

        # Listing pages (hub pages with multiple offerings)
        # Include both singular and plural forms
        listing_indicators = [
            '/services$', '/services/$', '/service$', '/service/$',
            '/solutions$', '/solutions/$', '/solution$', '/solution/$',
            '/products$', '/products/$', '/product$', '/product/$',
            '/offerings$', '/offerings/$', '/offering$', '/offering/$',
            '/what-we-do$', '/what-we-do/$',
            '/platforms$', '/platforms/$',
            '/technologies$', '/technologies/$',
            '/portfolio$', '/portfolio/$',
            '/practice-areas$', '/practice-areas/$',
            '/practices$', '/practices/$', '/practice$', '/practice/$',
        ]

        for indicator in listing_indicators:
            if re.search(indicator, path):
                return 'service_listing'

        # Detail pages (specific offering pages)
        # Examples: /services/consulting, /products/crm-software, /platforms/analytics
        # Also matches compound URLs like /environmental-services (single segment containing service keyword)
        if any(pattern in path for pattern in NavigationLinkFollower.OFFERING_PATTERNS):
            parts = [p for p in path.split('/') if p]
            # Multi-part URLs (e.g., /services/consulting) - classic detail page
            if len(parts) >= 2:
                return 'service_detail'
            # Single-part compound URLs (e.g., /environmental-services) - also a detail/listing page
            # Treat as service_listing since it's typically the main services page
            elif len(parts) == 1:
                return 'service_listing'

        return None

    # Backward compatibility
    @staticmethod
    def classify_service_url(url: str) -> Optional[str]:
        """Backward compatibility wrapper."""
        return NavigationLinkFollower.classify_offering_url(url)

    @staticmethod
    def find_service_links(html_content: str, base_url: str, max_links: int = 50) -> List[Dict[str, str]]:
        """
        Find offering-related links from navigation menu (industry-agnostic).

        Args:
            html_content: Homepage HTML content
            base_url: Base URL for resolving relative links
            max_links: Maximum number of offering links to return (increased to 50)

        Returns:
            List of dicts with 'url' and 'type' ('service_listing' or 'service_detail')
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        offering_links = []
        seen_urls = set()

        # Find all links in navigation areas AND main content
        # Include main content to capture offering links not in nav
        nav_areas = (soup.find_all(['nav', 'header', 'main', 'article']) +
                     soup.find_all(class_=re.compile('nav|menu|content|main|services|products|solutions')))

        for area in nav_areas:
            for link in area.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(base_url, href)

                # Only same-domain URLs
                if urlparse(absolute_url).netloc != urlparse(base_url).netloc:
                    continue

                # Remove fragments and queries for deduplication
                clean_url = absolute_url.split('#')[0].split('?')[0]

                # Normalize trailing slashes for deduplication
                # Remove trailing slash unless it's the root path
                if clean_url.endswith('/') and len(urlparse(clean_url).path) > 1:
                    clean_url = clean_url.rstrip('/')

                # Skip if already seen
                if clean_url in seen_urls:
                    continue

                # Check if offering URL
                if NavigationLinkFollower.is_offering_url(clean_url):
                    url_type = NavigationLinkFollower.classify_offering_url(clean_url)
                    if url_type:
                        offering_links.append({
                            'url': clean_url,
                            'type': url_type,
                            'link_text': link.get_text(strip=True)
                        })
                        seen_urls.add(clean_url)

                        if len(offering_links) >= max_links:
                            break

            if len(offering_links) >= max_links:
                break

        logger.info(f"Found {len(offering_links)} offering links")
        return offering_links


class ServicePageExtractor:
    """Extracts offering keywords from pages (industry-agnostic)."""

    # Exclude navigation, headers, and non-service content
    GENERIC_TERMS = {
        # Pure navigation
        'home', 'back', 'next', 'previous', 'menu', 'login', 'logout',
        'sign in', 'sign up', 'register', 'subscribe',

        # UI elements
        'learn more', 'read more', 'click here', 'get started', 'contact us',
        'view all', 'see all', 'show more', 'download', 'loading', 'search',

        # Generic single words WITHOUT context
        'page', 'tab', 'button', 'link', 'close', 'open', 'submit',

        # Navigation items (exact match)
        'careers', 'our story', 'our team', 'our news', 'our services',
        'about us', 'about', 'contact', 'news', 'blog', 'events',
        'community', 'media', 'gallery', 'resources',

        # Call-to-action phrases
        "let's work together", 'get in touch', 'request a quote',

        # Generic standalone terms
        'etc', 'etc.', 'services', 'solutions', 'offerings',
        'products', 'platforms', 'capabilities',

        # Single-word generic categories (sectors/industries - only when standalone)
        'sectors', 'industries', 'markets',
        'energy', 'mining', 'industrial', 'forestry', 'agriculture',
        'transportation', 'manufacturing', 'retail', 'healthcare',
        'education', 'finance', 'technology', 'construction',

        # Single-word materials/substances (unless part of service name)
        'soil', 'water', 'air', 'sediment', 'rock'
    }

    # Patterns to exclude (headers, fragments, legal terms, descriptions)
    EXCLUDE_PATTERNS = [
        r'^.*:$',  # Ends with colon (section headers)
        r'\bact\b.*\bregulation',  # Legal/regulatory headers
        r'^\s*and\s+',  # Starts with "and "
        r'^\s*or\s+',  # Starts with "or "
        r'^\s*\d+\.\s*$',  # Just numbers (1., 2., etc.)
        r'^\s*[a-z]\)\s*$',  # Just letters (a), b), etc.)
        r'^Our\s+',  # Starts with "Our " (Our News, Our Team, etc.)
        r'\.$',  # Ends with period (likely a sentence/description)
    ]

    # Description indicators (phrases that suggest text is a description, not a service name)
    DESCRIPTION_INDICATORS = [
        'through', 'including', 'such as', 'for example', 'conducted to',
        'we provide', 'we offer', 'designed to', 'intended for',
        'allows for', 'enables', 'helps to', 'used for'
    ]

    # Expanded industry-agnostic offering indicators
    OFFERING_INDICATORS = {
        # Services
        'consulting', 'advisory', 'support', 'maintenance', 'implementation',
        'integration', 'deployment', 'installation', 'configuration', 'customization',
        'training', 'coaching', 'mentoring', 'staffing', 'recruiting',

        # Development & engineering
        'development', 'engineering', 'design', 'architecture', 'programming',
        'coding', 'testing', 'qa', 'quality assurance', 'devops',

        # Analysis & assessment
        'assessment', 'analysis', 'evaluation', 'audit', 'review',
        'inspection', 'monitoring', 'reporting', 'analytics',

        # Management & optimization
        'management', 'optimization', 'improvement', 'enhancement',
        'strategy', 'planning', 'governance', 'compliance', 'regulatory',

        # Technology & platforms
        'platform', 'software', 'application', 'system', 'tool',
        'solution', 'framework', 'infrastructure', 'cloud', 'saas',
        'api', 'integration', 'automation', 'ai', 'ml', 'analytics',

        # Products & equipment
        'product', 'device', 'equipment', 'hardware', 'machinery',
        'instrument', 'appliance', 'component', 'part', 'module',

        # Healthcare
        'treatment', 'therapy', 'procedure', 'diagnosis', 'care',
        'surgery', 'rehabilitation', 'prevention', 'screening',

        # Legal & financial
        'litigation', 'advisory', 'counseling', 'representation',
        'filing', 'investment', 'portfolio', 'fund', 'advisory',

        # Education
        'course', 'program', 'certification', 'degree', 'curriculum',
        'workshop', 'seminar', 'class', 'lesson', 'tutorial',

        # Methodologies
        'methodology', 'approach', 'process', 'practice', 'technique',
        'method', 'framework', 'model', 'standard', 'protocol',

        # Capabilities & expertise
        'expertise', 'capability', 'competency', 'specialization',
        'specialty', 'proficiency', 'skill', 'experience'
    }

    @staticmethod
    def is_navigation_or_sidebar(element: Tag) -> bool:
        """
        Check if an element is part of navigation, sidebar, header, or footer.

        Args:
            element: BeautifulSoup Tag element

        Returns:
            True if element should be excluded from extraction
        """
        # Check element's own class/id
        attrs_to_check = []
        if element.get('class'):
            attrs_to_check.extend(element.get('class'))
        if element.get('id'):
            attrs_to_check.append(element.get('id'))

        # Check parent elements' class/id
        parent = element.parent
        levels = 0
        while parent and levels < 5:  # Check up to 5 levels up
            if parent.get('class'):
                attrs_to_check.extend(parent.get('class'))
            if parent.get('id'):
                attrs_to_check.append(parent.get('id'))
            parent = parent.parent
            levels += 1

        # Convert all to lowercase strings
        attrs_str = ' '.join(str(a) for a in attrs_to_check).lower()

        # Exclude patterns
        exclude_indicators = [
            'nav', 'menu', 'sidebar', 'side-bar', 'aside',
            'footer', 'header', 'breadcrumb', 'widget',
            'related', 'recent', 'popular', 'tags',
            'social', 'share', 'follow', 'subscribe'
        ]

        return any(indicator in attrs_str for indicator in exclude_indicators)

    @staticmethod
    def get_main_content_area(soup: BeautifulSoup):
        """
        Identify and return the main content area of the page.

        Args:
            soup: BeautifulSoup object

        Returns:
            BeautifulSoup element representing main content, or full soup if not found
        """
        # Try to find main content area in order of preference
        selectors = [
            'main',
            'article',
            '[role="main"]',
            '.main-content',
            '.content',
            '#main',
            '#content',
            '.post-content',
            '.entry-content'
        ]

        for selector in selectors:
            main_area = soup.select_one(selector)
            if main_area:
                logger.debug(f"Found main content area: {selector}")
                return main_area

        # If no main area found, return body or full soup
        body = soup.find('body')
        return body if body else soup

    @staticmethod
    def is_valid_offering_keyword(text: str, extraction_method: str = None) -> bool:
        """
        Validate if text is a valid offering keyword with strict quality rules.

        Args:
            text: Text to validate
            extraction_method: Optional extraction method (e.g., 'offering_card', 'h1', 'strong')
                              Used to apply context-specific validation rules

        Returns:
            True if valid offering keyword
        """
        if not text or len(text) < 3 or len(text) > 80:
            return False

        # Strip whitespace
        text = text.strip()

        # Word count check (stricter limits for quality)
        words = text.split()
        word_count = len(words)

        # Reject if too many words (likely a sentence/description)
        if word_count > 15:
            logger.debug(f"Excluded (too many words: {word_count}): {text}")
            return False

        # Lowercase for checking
        text_lower = text.lower()

        # EXCLUSION RULES (stricter)

        # 1. Exclude generic terms (exact match)
        if text_lower in ServicePageExtractor.GENERIC_TERMS:
            return False

        # 2. Exclude patterns (headers ending with :, fragments, etc.)
        for pattern in ServicePageExtractor.EXCLUDE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.debug(f"Excluded (pattern match): {text}")
                return False

        # 3. Exclude if it's just punctuation or numbers
        if not any(c.isalpha() for c in text):
            return False

        # 4. Exclude descriptions (text that describes service vs names it)
        # Check for description indicators
        has_description_indicator = any(ind in text_lower for ind in ServicePageExtractor.DESCRIPTION_INDICATORS)
        if has_description_indicator and word_count > 6:
            logger.debug(f"Excluded (description, not service name): {text}")
            return False

        # 5. For single-word entries, require offering indicator or specific patterns
        if word_count == 1:
            # EXCEPTION: Trust single words from offering cards (high-confidence source)
            # Offering cards are curated service listings, so single words are likely legitimate
            if extraction_method == 'offering_card':
                logger.debug(f"Accepted single-word from offering card: {text}")
                return True

            # For other sources, apply stricter validation
            # Allow only if contains offering indicator OR is a compound term
            has_indicator = any(term in text_lower for term in ServicePageExtractor.OFFERING_INDICATORS)
            is_compound = '-' in text or len(text) > 10  # Like "Bioremediation"
            if not (has_indicator or is_compound):
                logger.debug(f"Excluded (single word without indicator): {text}")
                return False

        # ACCEPTANCE RULES (quality-focused)

        # 1. Strong acceptance: Contains offering indicator words
        has_indicator = any(term in text_lower for term in ServicePageExtractor.OFFERING_INDICATORS)
        if has_indicator and word_count >= 2:
            return True

        # 2. Moderate acceptance: Proper service phrase structure
        # Must have at least 2 words and look like a service name
        if word_count >= 2:
            # Check if it's a proper noun phrase (capitalized appropriately)
            is_proper_phrase = words[0][0].isupper() if words[0] else False

            # Check for version markers (products)
            has_version = any(marker in text_lower for marker in [
                'version', 'v.', 'v1', 'v2', 'edition', 'pro', 'premium',
                'enterprise', 'basic', 'standard', 'advanced', 'suite', 'plus'
            ])

            # Check for trademark symbols (products)
            has_trademark = '™' in text or '®' in text or '©' in text

            # Accept if it's a proper phrase with structure
            if is_proper_phrase and (has_version or has_trademark or word_count <= 6):
                return True

        # 3. Weak acceptance: Acronyms and technical terms (only 2-4 characters, all caps)
        if word_count == 1:
            is_acronym = text.isupper() and 2 <= len(text) <= 4 and text.isalpha()
            if is_acronym:
                return True

        # 4. Accept compound terms with offering indicators
        if word_count == 1 and has_indicator:
            return True

        # Default: reject if doesn't meet quality criteria
        logger.debug(f"Excluded (no quality criteria met): {text}")
        return False

    # Backward compatibility
    @staticmethod
    def is_valid_service_keyword(text: str) -> bool:
        """Backward compatibility wrapper."""
        return ServicePageExtractor.is_valid_offering_keyword(text)

    @staticmethod
    def clean_page_title(title: str, company_name: str = None) -> Optional[str]:
        """
        Clean page title to extract service name, removing company names and branding.

        Args:
            title: Raw page title
            company_name: Company name to remove

        Returns:
            Cleaned service name or None
        """
        if not title:
            return None

        original_title = title

        # Remove company name if provided
        if company_name:
            title = title.replace(company_name, '')

        # Split by common separators and take first part
        separators = [' | ', ' - ', ' — ', ' :: ', ' » ', ' : ', ' / ']
        for sep in separators:
            if sep in title:
                parts = title.split(sep)
                # Take the part that looks most like a service name (not company name)
                for part in parts:
                    part = part.strip()
                    # Skip parts that are likely company names or generic terms
                    part_lower = part.lower()
                    if any(term in part_lower for term in ['inc', 'ltd', 'llc', 'corp', 'engineering', 'company', 'services']):
                        continue
                    if part and len(part) > 3:
                        title = part
                        break
                break

        title = title.strip()

        # Remove common company name suffixes/patterns
        company_patterns = [
            r'\s+[:\-–—]\s+.*(?:engineering|inc|ltd|llc|corp|company).*$',
            r'\s+\|\s+.*$',  # Remove everything after pipe
            r'\s+:\s+.*(?:engineering|inc|ltd).*$'
        ]

        for pattern in company_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)

        title = title.strip()

        # If title is too short after cleaning, use original
        if len(title) < 3:
            title = original_title

        # Validate
        if ServicePageExtractor.is_valid_offering_keyword(title):
            return title

        return None

    @staticmethod
    def extract_from_h1(soup: BeautifulSoup) -> List[Tuple[str, float]]:
        """
        Extract offering keywords from H1 tags.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of (keyword, confidence_score) tuples
        """
        keywords = []
        h1_tags = soup.find_all('h1')

        for h1 in h1_tags:
            text = sanitize_text(h1.get_text(strip=True))
            if ServicePageExtractor.is_valid_offering_keyword(text):
                keywords.append((text, 0.95))  # High confidence for H1
                logger.debug(f"Extracted from H1: {text}")

        return keywords

    @staticmethod
    def extract_from_headings(soup: BeautifulSoup) -> List[Tuple[str, float]]:
        """
        Extract offering keywords from H2-H6 tags in main content (context-aware).

        Args:
            soup: BeautifulSoup object

        Returns:
            List of (keyword, confidence_score) tuples
        """
        keywords = []

        # Get main content area
        main_content = ServicePageExtractor.get_main_content_area(soup)

        # H2-H6 can contain offering names (expanded from H2-H4)
        for tag_name, confidence in [('h2', 0.88), ('h3', 0.85), ('h4', 0.82), ('h5', 0.80), ('h6', 0.78)]:
            for heading in main_content.find_all(tag_name):
                # Skip if heading is in navigation/sidebar
                if ServicePageExtractor.is_navigation_or_sidebar(heading):
                    continue

                text = sanitize_text(heading.get_text(strip=True))
                if ServicePageExtractor.is_valid_offering_keyword(text):
                    keywords.append((text, confidence))
                    logger.debug(f"Extracted from {tag_name.upper()}: {text}")

        return keywords

    @staticmethod
    def extract_from_title(soup: BeautifulSoup) -> List[Tuple[str, float]]:
        """
        Extract offering keywords from page title.

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
        Extract offering keywords from meta keywords tag.

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
                if ServicePageExtractor.is_valid_offering_keyword(keyword):
                    keywords.append((keyword, 0.85))  # Good confidence for meta
                    logger.debug(f"Extracted from meta: {keyword}")

        return keywords

    @staticmethod
    def extract_from_json_ld(soup: BeautifulSoup) -> List[Tuple[str, float]]:
        """
        Extract offering keywords from JSON-LD structured data (expanded schema types).

        Args:
            soup: BeautifulSoup object

        Returns:
            List of (keyword, confidence_score) tuples
        """
        keywords = []
        scripts = soup.find_all('script', type='application/ld+json')

        # Expanded schema types to look for
        valid_types = {
            'Service', 'Product', 'Offer', 'SoftwareApplication',
            'MedicalProcedure', 'MedicalTherapy', 'Course', 'EducationalProgram',
            'ProfessionalService', 'FinancialProduct', 'Vehicle', 'Drug',
            'ItemList',  # May contain offerings
        }

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

                    # Look for offering types
                    item_type = item.get('@type', '')

                    # Handle multiple types (can be a list)
                    if isinstance(item_type, list):
                        types_to_check = item_type
                    else:
                        types_to_check = [item_type]

                    # Check if any type matches our valid types
                    if any(t in valid_types for t in types_to_check):
                        name = item.get('name')
                        if name and ServicePageExtractor.is_valid_offering_keyword(name):
                            keywords.append((name, 1.0))  # Highest confidence for structured data
                            logger.debug(f"Extracted from JSON-LD ({item_type}): {name}")

                        # Also check for offers/hasOfferingCatalog
                        for offer_key in ['offers', 'hasOfferingCatalog', 'itemListElement']:
                            if offer_key in item:
                                offers = item[offer_key]
                                if isinstance(offers, dict):
                                    offers = [offers]
                                if isinstance(offers, list):
                                    for offer in offers:
                                        if isinstance(offer, dict):
                                            offer_name = offer.get('name')
                                            if offer_name and ServicePageExtractor.is_valid_offering_keyword(offer_name):
                                                keywords.append((offer_name, 1.0))
                                                logger.debug(f"Extracted from JSON-LD offer: {offer_name}")

            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                logger.debug(f"Error parsing JSON-LD: {e}")
                continue

        return keywords

    @staticmethod
    def extract_from_lists(soup: BeautifulSoup) -> List[Tuple[str, float]]:
        """
        Extract offering keywords from lists in main content (context-aware).

        Args:
            soup: BeautifulSoup object

        Returns:
            List of (keyword, confidence_score) tuples
        """
        keywords = []

        # Get main content area only
        main_content = ServicePageExtractor.get_main_content_area(soup)

        # Find lists in main content
        for list_tag in main_content.find_all(['ul', 'ol']):
            # Skip if list is in navigation/sidebar
            if ServicePageExtractor.is_navigation_or_sidebar(list_tag):
                continue

            # Check if list is under a service-related heading
            # Look for preceding heading (h2, h3, h4) within reasonable distance
            prev_sibling = list_tag.find_previous_sibling(['h2', 'h3', 'h4', 'strong', 'b'])
            has_service_context = False

            if prev_sibling:
                heading_text = prev_sibling.get_text(strip=True).lower()
                service_indicators = [
                    'services', 'offering', 'solution', 'product', 'capability',
                    'we provide', 'we offer', 'include', 'our services',
                    'what we do', 'expertise'
                ]
                has_service_context = any(ind in heading_text for ind in service_indicators)

            # Extract list items
            list_items = []
            for li in list_tag.find_all('li', recursive=False):
                # Skip if list item is in navigation
                if ServicePageExtractor.is_navigation_or_sidebar(li):
                    continue

                text = li.get_text(strip=True)

                # Clean up common list artifacts
                text = text.strip('•').strip('-').strip()

                if ServicePageExtractor.is_valid_offering_keyword(text):
                    list_items.append(text)

            # Quality check: If we found service-related items, add them
            # Higher confidence if under service-related heading
            if list_items:
                confidence = 0.85 if has_service_context else 0.75
                for item in list_items:
                    keywords.append((item, confidence))
                    logger.debug(f"Extracted from list (context={has_service_context}): {item}")

        return keywords

    @staticmethod
    def extract_from_strong_emphasis(soup: BeautifulSoup) -> List[Tuple[str, float]]:
        """
        Extract offering keywords from emphasized text (strong/b tags).

        Product and offering names are often bold or emphasized.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of (keyword, confidence_score) tuples
        """
        keywords = []

        for tag_name in ['strong', 'b']:
            for elem in soup.find_all(tag_name):
                text = elem.get_text(strip=True)
                if ServicePageExtractor.is_valid_offering_keyword(text):
                    keywords.append((text, 0.78))  # Reasonable confidence
                    logger.debug(f"Extracted from {tag_name}: {text}")

        return keywords

    @staticmethod
    def deduplicate_keywords(keywords_dict: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Deduplicate and clean keywords, keeping the best version of near-duplicates.

        Args:
            keywords_dict: Dictionary of {keyword: {'confidence': float, 'method': str, 'url': str}}

        Returns:
            Cleaned dictionary with duplicates removed
        """
        if not keywords_dict:
            return keywords_dict

        # Convert to list for easier processing
        items = list(keywords_dict.items())
        to_remove = set()

        for i, (key1, data1) in enumerate(items):
            if key1 in to_remove:
                continue

            key1_lower = key1.lower().strip()

            for j, (key2, data2) in enumerate(items[i+1:], start=i+1):
                if key2 in to_remove:
                    continue

                key2_lower = key2.lower().strip()

                # Exact duplicate (case-insensitive)
                if key1_lower == key2_lower:
                    # Keep the one with higher confidence
                    if data2['confidence'] > data1['confidence']:
                        to_remove.add(key1)
                        break
                    else:
                        to_remove.add(key2)
                    continue

                # Plural vs singular (keep singular)
                if key1_lower == key2_lower.rstrip('s') or key2_lower == key1_lower.rstrip('s'):
                    if key1_lower.endswith('s') and not key2_lower.endswith('s'):
                        to_remove.add(key1)  # Remove plural, keep singular
                        break
                    elif key2_lower.endswith('s') and not key1_lower.endswith('s'):
                        to_remove.add(key2)  # Remove plural, keep singular
                    continue

                # One is subset of another (keep the more complete one)
                if key1_lower in key2_lower or key2_lower in key1_lower:
                    # Keep the longer/more descriptive one
                    if len(key1) < len(key2):
                        to_remove.add(key1)
                        break
                    else:
                        to_remove.add(key2)
                    continue

        # Remove duplicates
        return {k: v for k, v in keywords_dict.items() if k not in to_remove}

    @staticmethod
    def extract_from_service_sections(soup: BeautifulSoup) -> List[Tuple[str, float]]:
        """
        Fallback extraction from divs/sections with service-related classes.
        Used when standard methods find nothing.

        Args:
            soup: BeautifulSoup object

        Returns:
            List of (keyword, confidence_score) tuples
        """
        keywords = []

        # Look for sections/divs with service-related classes or IDs
        service_indicators = [
            'service', 'solution', 'offering', 'product', 'capability',
            'expertise', 'practice', 'specialty', 'treatment', 'program'
        ]

        # Find divs/sections with service-related class names
        main_content = ServicePageExtractor.get_main_content_area(soup)

        for element in main_content.find_all(['div', 'section', 'article']):
            # Check if this element has service-related classes/IDs
            attrs = []
            if element.get('class'):
                attrs.extend(element.get('class'))
            if element.get('id'):
                attrs.append(element.get('id'))

            attrs_str = ' '.join(str(a) for a in attrs).lower()

            # Check if any service indicator is in the attributes
            if any(indicator in attrs_str for indicator in service_indicators):
                # Extract heading from this section
                for heading_tag in ['h2', 'h3', 'h4', 'h5', 'h6']:
                    headings = element.find_all(heading_tag, recursive=False)  # Direct children only
                    for heading in headings[:3]:  # Limit to first 3 headings in section
                        text = sanitize_text(heading.get_text(strip=True))
                        if ServicePageExtractor.is_valid_offering_keyword(text):
                            keywords.append((text, 0.75))  # Moderate confidence
                            logger.debug(f"Extracted from service section ({heading_tag}): {text}")

        return keywords

    @staticmethod
    def extract_from_paragraphs(soup: BeautifulSoup, url: str) -> List[Tuple[str, float]]:
        """
        Extract services from paragraphs that list offerings in prose.
        Only used on service pages when services are listed like:
        "We provide X, Y, and Z services."

        Args:
            soup: BeautifulSoup object
            url: Source URL (to check if it's a service page)

        Returns:
            List of (keyword, confidence_score) tuples
        """
        keywords = []

        # Only apply to service pages (URL must contain service indicators)
        if not NavigationLinkFollower.is_offering_url(url):
            return keywords

        # Service indicator phrases that suggest the paragraph lists services
        service_indicators = [
            'we provide', 'we offer', 'we specialize in', 'services include',
            'our services', 'our offerings', 'we deliver', 'areas of expertise',
            'capabilities include', 'solutions include'
        ]

        main_content = ServicePageExtractor.get_main_content_area(soup)

        # Find paragraphs that list services
        for paragraph in main_content.find_all('p'):
            text = paragraph.get_text(strip=True).lower()

            # Check if paragraph contains service indicators
            if not any(indicator in text for indicator in service_indicators):
                continue

            # Check if it contains commas or "and" (list pattern)
            if ',' not in text and ' and ' not in text:
                continue

            # Skip very long paragraphs (likely descriptions, not lists)
            if len(text) > 500:
                continue

            # Extract the portion after the service indicator
            for indicator in service_indicators:
                if indicator in text:
                    # Get text after indicator
                    parts = text.split(indicator, 1)
                    if len(parts) < 2:
                        continue

                    listing_text = parts[1]

                    # Split by commas and "and"
                    items = re.split(r',|\sand\s', listing_text)

                    for item in items:
                        # Clean up the item
                        item = sanitize_text(item.strip())

                        # Remove common endings (periods, etc.)
                        item = re.sub(r'\.$', '', item)

                        # Validate as service keyword
                        if ServicePageExtractor.is_valid_offering_keyword(item):
                            # Lower confidence since extracted from prose
                            keywords.append((item, 0.70))
                            logger.debug(f"Extracted from paragraph: {item}")

                    break  # Found a matching indicator, process next paragraph

        return keywords

    @staticmethod
    def extract_keywords(html_content: str, url: str) -> Dict[str, Dict]:
        """
        Extract all offering keywords from a page (industry-agnostic).

        Args:
            html_content: HTML content of service page
            url: Source URL

        Returns:
            Dict of {keyword: {'confidence': float, 'method': str, 'url': str}}
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        all_keywords = {}

        # Extract from multiple sources (expanded extraction)
        sources = [
            ('h1', ServicePageExtractor.extract_from_h1(soup)),
            ('title', ServicePageExtractor.extract_from_title(soup)),
            ('headings', ServicePageExtractor.extract_from_headings(soup)),
            ('meta', ServicePageExtractor.extract_from_meta(soup)),
            ('json_ld', ServicePageExtractor.extract_from_json_ld(soup)),
            ('lists', ServicePageExtractor.extract_from_lists(soup)),
            ('strong', ServicePageExtractor.extract_from_strong_emphasis(soup)),
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

        # FALLBACK: If we found nothing or very few, try fallback extraction
        if len(all_keywords) < 3:  # Less than 3 keywords found
            if not all_keywords:
                logger.info(f"Primary extraction found 0 keywords on {url}, trying fallback methods...")
            else:
                logger.info(f"Primary extraction found only {len(all_keywords)} keywords on {url}, trying fallback methods...")

            fallback_sources = [
                ('service_sections', ServicePageExtractor.extract_from_service_sections(soup)),
                ('paragraphs', ServicePageExtractor.extract_from_paragraphs(soup, url)),
            ]

            for method, keywords in fallback_sources:
                for keyword, confidence in keywords:
                    if keyword not in all_keywords or all_keywords[keyword]['confidence'] < confidence:
                        all_keywords[keyword] = {
                            'confidence': confidence,
                            'method': method,
                            'url': url
                        }

            if all_keywords:
                logger.info(f"Total after fallback: {len(all_keywords)} keywords on {url}")
            else:
                logger.warning(f"All extraction methods failed for {url} - no keywords found")

        # Deduplicate and clean keywords
        all_keywords = ServicePageExtractor.deduplicate_keywords(all_keywords)

        return all_keywords


class ServiceListingExtractor:
    """Extracts offering names from listing/hub pages (industry-agnostic)."""

    @staticmethod
    def extract_from_offering_cards(soup: BeautifulSoup) -> List[Tuple[str, float]]:
        """
        Extract offerings from card/tile headings (expanded patterns).

        Args:
            soup: BeautifulSoup object

        Returns:
            List of (keyword, confidence_score) tuples
        """
        keywords = []

        # Expanded offering card patterns (industry-agnostic)
        selectors = [
            # Service patterns
            '.service-card h3', '.service-card h4', '.service-card h2',
            '.services-list li a', '.services-list li h3',
            'article.service h2', 'article.service h3',

            # Solution patterns
            '.solution-item .title', '.solution-item h3', '.solution-item h2',
            '.solution-card h3', '.solution-card h4',

            # Product patterns
            '.product-card h3', '.product-card h4', '.product-card .title',
            '.product-item h3', '.product-item h2', '.product-name',
            '.product-list li a', '.product-list li h3',

            # Platform/technology patterns
            '.platform-card h3', '.platform-item h3',
            '.tech-card h3', '.technology-item h3',

            # Generic offering patterns
            '.offering-card h3', '.offering-item h3', '.offerings-grid .offering-name',
            '.card h3', '.card h4', '.card .title',
            '.item h3', '.item h4', '.item .title',
            '.tile h3', '.tile h4', '.tile .title',
            '.expertise-title', '.expertise-card h3', '.expertise-item h3',

            # Accordion/toggle patterns (for collapsed service sections)
            '.panel-title', '.panel-title h4', '.panel-heading h4',
            '.accordion .panel h4', '.accordion h4',
            '.toggle-heading', '.fusion-toggle-heading',
            '.collapse-toggle', '.accordion-title',

            # List patterns
            '.capabilities-list li', '.expertise-list li',
            '.features-list li a', '.portfolio-list li a',
        ]

        for selector in selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if ServicePageExtractor.is_valid_offering_keyword(text, extraction_method='offering_card'):
                        keywords.append((text, 0.80))
                        logger.debug(f"Extracted from offering card ({selector}): {text}")
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")

        return keywords

    # Backward compatibility
    @staticmethod
    def extract_from_service_cards(soup: BeautifulSoup) -> List[Tuple[str, float]]:
        """Backward compatibility wrapper."""
        return ServiceListingExtractor.extract_from_offering_cards(soup)

    @staticmethod
    def extract_keywords(html_content: str, url: str) -> Dict[str, Dict]:
        """
        Extract offering keywords from a listing/hub page (industry-agnostic).

        Args:
            html_content: HTML content
            url: Source URL

        Returns:
            Dict of {keyword: {'confidence': float, 'method': str, 'url': str}}
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        all_keywords = {}

        # Extract from offering cards (expanded patterns)
        keywords = ServiceListingExtractor.extract_from_offering_cards(soup)

        # Also extract from H2/H3 in main content (often category names)
        for heading_tag in ['h2', 'h3']:
            for heading in soup.find_all(heading_tag):
                text = heading.get_text(strip=True)
                # Use 'offering_card' method for listing page headings too (high confidence)
                if ServicePageExtractor.is_valid_offering_keyword(text, extraction_method='offering_card'):
                    keywords.append((text, 0.75))

        for keyword, confidence in keywords:
            # Keep highest confidence if keyword already exists
            if keyword not in all_keywords or all_keywords[keyword]['confidence'] < confidence:
                all_keywords[keyword] = {
                    'confidence': confidence,
                    'method': 'offering_card',
                    'url': url
                }

        return all_keywords
