"""
HTML parser for extracting navigation menu items from websites.
"""

import logging
from typing import List, Set
from bs4 import BeautifulSoup, Tag
from utils import extract_keywords_from_text, sanitize_text

logger = logging.getLogger(__name__)


class MenuParser:
    """Extracts navigation menu items from HTML content."""

    # CSS selectors for navigation menus
    NAV_SELECTORS = [
        'nav',
        '.nav',
        '#nav',
        '.menu',
        '#menu',
        '.navigation',
        '#navigation',
        'header nav',
        '.navbar',
        '.nav-menu',
        '.main-menu',
        '.primary-menu',
        '.site-navigation',
        '.main-navigation',
        '.primary-navigation',
        '.header-menu',
        '.top-menu',
        '.header-nav',
        '#main-menu',
        '#primary-menu',
        '#site-navigation',
        '.menu-container',
        '.nav-container',
    ]

    # Attributes that might indicate navigation
    NAV_ATTRIBUTES = [
        {'role': 'navigation'},
        {'role': 'menubar'},
        {'aria-label': 'navigation'},
        {'aria-label': 'main navigation'},
        {'aria-label': 'primary navigation'},
    ]

    # Classes/IDs that suggest navigation (for fallback)
    NAV_KEYWORDS = [
        'menu', 'nav', 'navigation', 'navbar', 'menubar',
        'header-menu', 'main-menu', 'primary-menu'
    ]

    def __init__(self):
        """Initialize the menu parser."""
        self.soup = None

    def parse(self, html_content: str) -> List[str]:
        """
        Parse HTML content and extract menu items.

        Args:
            html_content: Raw HTML content

        Returns:
            List of menu item texts
        """
        if not html_content:
            return []

        try:
            self.soup = BeautifulSoup(html_content, 'html.parser')
            menu_items = self._extract_menu_items()
            return menu_items
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return []

    def _extract_menu_items(self) -> List[str]:
        """
        Extract menu items using multiple detection methods.

        Returns:
            List of unique menu item texts
        """
        all_items = set()

        # Method 1: CSS selectors
        all_items.update(self._find_by_css_selectors())

        # Method 2: HTML5 semantic tags
        all_items.update(self._find_by_semantic_tags())

        # Method 3: ARIA attributes
        all_items.update(self._find_by_aria_attributes())

        # Method 4: Common patterns
        all_items.update(self._find_by_common_patterns())

        # Filter and clean
        cleaned_items = self._clean_menu_items(all_items)

        logger.debug(f"Extracted {len(cleaned_items)} unique menu items")
        return list(cleaned_items)

    def _find_by_css_selectors(self) -> Set[str]:
        """
        Find menu items using CSS selectors.

        Returns:
            Set of menu item texts
        """
        items = set()

        for selector in self.NAV_SELECTORS:
            try:
                elements = self.soup.select(selector)
                for element in elements:
                    items.update(self._extract_text_from_element(element))
            except Exception as e:
                logger.debug(f"Error with selector '{selector}': {e}")

        return items

    def _find_by_semantic_tags(self) -> Set[str]:
        """
        Find menu items using HTML5 semantic tags.

        Returns:
            Set of menu item texts
        """
        items = set()

        # Find <nav> tags
        nav_tags = self.soup.find_all('nav')
        for nav in nav_tags:
            items.update(self._extract_text_from_element(nav))

        # Find <menu> tags
        menu_tags = self.soup.find_all('menu')
        for menu in menu_tags:
            items.update(self._extract_text_from_element(menu))

        return items

    def _find_by_aria_attributes(self) -> Set[str]:
        """
        Find menu items using ARIA attributes.

        Returns:
            Set of menu item texts
        """
        items = set()

        for attrs in self.NAV_ATTRIBUTES:
            try:
                elements = self.soup.find_all(attrs=attrs)
                for element in elements:
                    items.update(self._extract_text_from_element(element))
            except Exception as e:
                logger.debug(f"Error finding ARIA elements: {e}")

        return items

    def _find_by_common_patterns(self) -> Set[str]:
        """
        Find menu items using common class/id patterns.

        Returns:
            Set of menu item texts
        """
        items = set()

        # Find all divs and other containers
        containers = self.soup.find_all(['div', 'ul', 'ol', 'aside', 'section'])

        for container in containers:
            # Check class and id attributes
            class_str = ' '.join(container.get('class', [])).lower()
            id_str = (container.get('id') or '').lower()

            # Check if any navigation keyword is present
            for keyword in self.NAV_KEYWORDS:
                if keyword in class_str or keyword in id_str:
                    items.update(self._extract_text_from_element(container))
                    break

        return items

    def _extract_text_from_element(self, element: Tag) -> Set[str]:
        """
        Extract text from links and buttons within an element.

        Args:
            element: BeautifulSoup element

        Returns:
            Set of text items
        """
        items = set()

        if not element:
            return items

        # Find all links
        links = element.find_all('a')
        for link in links:
            text = self._get_element_text(link)
            if text:
                items.add(text)

        # Find all buttons
        buttons = element.find_all('button')
        for button in buttons:
            text = self._get_element_text(button)
            if text:
                items.add(text)

        # Find list items (common in navigation)
        list_items = element.find_all('li')
        for li in list_items:
            # Get direct text or text from first link
            link = li.find('a')
            if link:
                text = self._get_element_text(link)
            else:
                text = self._get_element_text(li)

            if text:
                items.add(text)

        # If no links/buttons found, try to get direct text from spans/divs
        if not items:
            spans = element.find_all('span', recursive=False)
            for span in spans:
                text = self._get_element_text(span)
                if text:
                    items.add(text)

        return items

    def _get_element_text(self, element: Tag) -> str:
        """
        Get cleaned text from an element.

        Args:
            element: BeautifulSoup element

        Returns:
            Cleaned text or empty string
        """
        if not element:
            return ""

        # Try aria-label first
        aria_label = element.get('aria-label')
        if aria_label:
            return sanitize_text(aria_label)

        # Get visible text
        text = element.get_text(strip=True)
        return sanitize_text(text)

    def _clean_menu_items(self, items: Set[str]) -> Set[str]:
        """
        Clean and filter menu items.

        Args:
            items: Set of raw menu items

        Returns:
            Set of cleaned menu items
        """
        cleaned = set()

        for item in items:
            # Skip empty items
            if not item or len(item.strip()) == 0:
                continue

            # Skip items that are too short (likely noise)
            if len(item) < 2:
                continue

            # Skip items that are too long (likely not menu items)
            if len(item) > 100:
                continue

            # Skip items that are just numbers
            if item.isdigit():
                continue

            # Skip common noise
            noise_words = ['skip to content', 'skip navigation', 'menu', 'toggle']
            if item.lower() in noise_words:
                continue

            cleaned.add(item)

        return cleaned

    def extract_keywords(self, html_content: str) -> Set[str]:
        """
        Extract and normalize keywords from menu items.

        Args:
            html_content: Raw HTML content

        Returns:
            Set of normalized keywords
        """
        menu_items = self.parse(html_content)

        all_keywords = set()
        for item in menu_items:
            # Extract keywords from each menu item
            keywords = extract_keywords_from_text(item)
            all_keywords.update(keywords)

        logger.debug(f"Extracted {len(all_keywords)} unique keywords from menu items")
        return all_keywords

    def get_menu_structure(self, html_content: str) -> dict:
        """
        Get structured information about menus found.

        Args:
            html_content: Raw HTML content

        Returns:
            Dictionary with menu structure information
        """
        if not html_content:
            return {'menus_found': 0, 'total_items': 0, 'items': []}

        try:
            self.soup = BeautifulSoup(html_content, 'html.parser')
            menu_items = self._extract_menu_items()

            return {
                'menus_found': len(self.soup.find_all('nav')) + len(self.soup.find_all('menu')),
                'total_items': len(menu_items),
                'items': menu_items[:50]  # Return first 50 items
            }
        except Exception as e:
            logger.error(f"Error getting menu structure: {e}")
            return {'menus_found': 0, 'total_items': 0, 'items': []}
