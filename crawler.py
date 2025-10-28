"""
Main web crawler implementation.
"""

import logging
import requests
import time
from typing import Optional, Dict, Set
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import Config
from database import DatabaseManager
from parser import MenuParser
from service_extractor import (
    NavigationLinkFollower,
    ServicePageExtractor,
    ServiceListingExtractor
)
from utils import (
    RateLimiter,
    ProgressTracker,
    build_full_url,
    is_valid_url,
    check_robots_txt
)

logger = logging.getLogger(__name__)


class WebCrawler:
    """Main web crawler for extracting navigation menus."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the web crawler.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.parser = MenuParser()
        self.rate_limiter = RateLimiter(
            Config.RATE_LIMIT_MIN,
            Config.RATE_LIMIT_MAX
        )
        self.session = self._create_session()
        self.should_stop = False

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry logic.

        Returns:
            Configured requests session
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=Config.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers to mimic real browser (helps avoid bot detection)
        session.headers.update({
            'User-Agent': Config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })

        return session

    def crawl_domain(self, domain: str, company_id: int) -> Dict:
        """
        Crawl a single domain and extract menu items.

        Args:
            domain: Domain to crawl
            company_id: Company ID

        Returns:
            Dictionary with crawl results
        """
        result = {
            'success': False,
            'domain': domain,
            'keywords_found': 0,
            'new_keywords': 0,
            'error': None,
            'pages_crawled': 0,
            'pages_failed': 0
        }

        try:
            logger.info(f"Starting crawl for domain: {domain}")

            # Build full URL
            url = build_full_url(domain)

            # Validate URL
            if not is_valid_url(url):
                raise ValueError(f"Invalid URL: {url}")

            # Check robots.txt if enabled
            if Config.RESPECT_ROBOTS_TXT:
                if not check_robots_txt(url, Config.USER_AGENT):
                    raise ValueError(f"Crawling disallowed by robots.txt: {url}")

            # Apply rate limiting
            self.rate_limiter.wait()

            # Fetch the page
            html_content = self._fetch_page(url)

            if html_content:
                # Extract keywords from menu
                keywords = self.parser.extract_keywords(html_content)

                if keywords:
                    # Get section type ID for 'menu'
                    section_type_id = self.db.get_section_type_id('menu')

                    if section_type_id:
                        # Store keywords in database
                        total, new = self.db.store_keywords_batch(
                            company_id,
                            list(keywords),
                            section_type_id
                        )

                        result['keywords_found'] = total
                        result['new_keywords'] = new
                        result['pages_crawled'] = 1
                        result['success'] = True

                        logger.info(
                            f"Successfully crawled {domain}: "
                            f"{total} keywords ({new} new)"
                        )
                    else:
                        raise ValueError("Section type 'menu' not found in database")
                else:
                    logger.warning(f"No menu keywords found for {domain}")
                    result['success'] = True  # Still count as success
                    result['pages_crawled'] = 1
            else:
                result['pages_failed'] = 1
                raise ValueError("Failed to fetch page content")

        except requests.exceptions.Timeout:
            error = f"Request timeout for {domain}"
            logger.error(error)
            result['error'] = error
            result['pages_failed'] = 1

        except requests.exceptions.SSLError as e:
            error = f"SSL error for {domain}: {str(e)}"
            logger.error(error)
            result['error'] = error
            result['pages_failed'] = 1

        except requests.exceptions.ConnectionError as e:
            error = f"Connection error for {domain}: {str(e)}"
            logger.error(error)
            result['error'] = error
            result['pages_failed'] = 1

        except requests.exceptions.RequestException as e:
            error = f"Request error for {domain}: {str(e)}"
            logger.error(error)
            result['error'] = error
            result['pages_failed'] = 1

        except ValueError as e:
            error = str(e)
            logger.error(error)
            result['error'] = error
            result['pages_failed'] = 1

        except Exception as e:
            error = f"Unexpected error for {domain}: {str(e)}"
            logger.error(error, exc_info=True)
            result['error'] = error
            result['pages_failed'] = 1

        return result

    def crawl_services(self, domain: str, company_id: int) -> Dict:
        """
        Crawl service pages by following navigation links.

        Args:
            domain: Domain to crawl
            company_id: Company ID

        Returns:
            Dictionary with crawl results
        """
        result = {
            'success': False,
            'domain': domain,
            'keywords_found': 0,
            'new_keywords': 0,
            'error': None,
            'pages_crawled': 0,
            'pages_failed': 0,
            'service_links_found': 0
        }

        try:
            logger.info(f"Starting service extraction for domain: {domain}")

            # Build full URL
            url = build_full_url(domain)

            # Validate URL
            if not is_valid_url(url):
                raise ValueError(f"Invalid URL: {url}")

            # Check robots.txt if enabled
            if Config.RESPECT_ROBOTS_TXT:
                if not check_robots_txt(url, Config.USER_AGENT):
                    raise ValueError(f"Crawling disallowed by robots.txt: {url}")

            # Apply rate limiting
            self.rate_limiter.wait()

            # Fetch homepage with final URL (handles redirects like example.com -> www.example.com)
            logger.info(f"Fetching homepage: {url}")
            fetch_result = self._fetch_page_with_url(url)

            if not fetch_result:
                raise ValueError("Failed to fetch homepage content")

            html_content, final_url = fetch_result

            # Log if redirect occurred
            if final_url != url:
                logger.info(f"Redirect detected: {url} -> {final_url}")

            # Find service links from navigation using final URL (ensures same-domain check works after redirects)
            service_links = NavigationLinkFollower.find_service_links(html_content, final_url, max_links=20)
            result['service_links_found'] = len(service_links)

            if not service_links:
                logger.warning(f"No service links found for {domain}")
                result['success'] = True  # Not an error, just no services found
                return result

            logger.info(f"Found {len(service_links)} service links to crawl")

            total_keywords = 0
            total_new = 0

            # Process each service link
            for idx, link_info in enumerate(service_links, 1):
                service_url = link_info['url']
                service_type = link_info['type']  # 'service_detail' or 'service_listing'

                try:
                    logger.info(f"Crawling service page {idx}/{len(service_links)}: {service_url}")

                    # Apply rate limiting between pages
                    if idx > 1:
                        self.rate_limiter.wait()

                    # Fetch service page
                    service_html = self._fetch_page(service_url)

                    if not service_html:
                        logger.warning(f"Failed to fetch service page: {service_url}")
                        result['pages_failed'] += 1
                        continue

                    result['pages_crawled'] += 1

                    # Extract keywords based on page type
                    if service_type == 'service_detail':
                        keywords_data = ServicePageExtractor.extract_keywords(service_html, service_url)
                    else:  # service_listing
                        keywords_data = ServiceListingExtractor.extract_keywords(service_html, service_url)

                    if keywords_data:
                        # Get section type ID
                        section_type_id = self.db.get_section_type_id(service_type)

                        if not section_type_id:
                            logger.error(f"Section type '{service_type}' not found in database")
                            continue

                        # Store keywords with source tracking
                        total, new = self.db.store_keywords_with_source(
                            company_id,
                            keywords_data,
                            section_type_id
                        )

                        total_keywords += total
                        total_new += new

                        logger.info(
                            f"Extracted {total} keywords ({new} new) from {service_url}"
                        )
                    else:
                        logger.debug(f"No keywords extracted from {service_url}")

                except Exception as e:
                    logger.error(f"Error processing service page {service_url}: {e}")
                    result['pages_failed'] += 1
                    continue

            # Update final results
            result['keywords_found'] = total_keywords
            result['new_keywords'] = total_new
            result['success'] = True

            logger.info(
                f"Successfully crawled services for {domain}: "
                f"{total_keywords} keywords ({total_new} new) from {result['pages_crawled']} pages"
            )

        except requests.exceptions.Timeout:
            error = f"Request timeout for {domain}"
            logger.error(error)
            result['error'] = error
            result['pages_failed'] += 1

        except requests.exceptions.SSLError as e:
            error = f"SSL error for {domain}: {str(e)}"
            logger.error(error)
            result['error'] = error
            result['pages_failed'] += 1

        except requests.exceptions.ConnectionError as e:
            error = f"Connection error for {domain}: {str(e)}"
            logger.error(error)
            result['error'] = error
            result['pages_failed'] += 1

        except requests.exceptions.RequestException as e:
            error = f"Request error for {domain}: {str(e)}"
            logger.error(error)
            result['error'] = error
            result['pages_failed'] += 1

        except ValueError as e:
            error = str(e)
            logger.error(error)
            result['error'] = error

        except Exception as e:
            error = f"Unexpected error for {domain}: {str(e)}"
            logger.error(error, exc_info=True)
            result['error'] = error

        return result

    def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from URL.

        Args:
            url: URL to fetch

        Returns:
            HTML content or None on failure
        """
        result = self._fetch_page_with_url(url)
        return result[0] if result else None

    def _fetch_page_with_url(self, url: str) -> Optional[tuple[str, str]]:
        """
        Fetch HTML content and final URL from URL (after redirects).

        Args:
            url: URL to fetch

        Returns:
            Tuple of (HTML content, final URL after redirects) or None on failure
        """
        try:
            logger.debug(f"Fetching {url}")

            response = self.session.get(
                url,
                timeout=Config.REQUEST_TIMEOUT,
                allow_redirects=Config.FOLLOW_REDIRECTS,
                verify=Config.VERIFY_SSL
            )

            # Check status code
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type.lower():
                logger.warning(f"Non-HTML content type: {content_type}")
                return None

            # Ensure proper encoding detection and decompression
            # Access content first to trigger decompression
            _ = response.content

            # Set encoding if not detected
            if not response.encoding or response.encoding == 'ISO-8859-1':
                response.encoding = response.apparent_encoding or 'utf-8'

            # Return both HTML content and final URL (after any redirects)
            return (response.text, response.url)

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            return None

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def run(self) -> None:
        """Run the crawler to process pending domains."""
        logger.info("Starting web crawler")

        # Reset any stuck jobs from previous runs
        self.db.reset_stuck_jobs()

        # Get total pending count
        total_pending = self.db.get_pending_count()
        logger.info(f"Found {total_pending} pending domains to crawl")

        if total_pending == 0:
            logger.info("No pending domains to crawl")
            return

        # Initialize progress tracker
        progress = ProgressTracker(total_pending)

        # Process domains sequentially
        processed = 0
        while not self.should_stop:
            # Get next pending domain
            company = self.db.get_next_pending_domain()

            if not company:
                logger.info("No more pending domains")
                break

            company_id = company['id']
            domain = company['domain']

            try:
                # Update status to in_progress
                self.db.update_company_status(company_id, 'in_progress')

                # Create crawl job
                job_id = self.db.create_crawl_job(company_id)

                # Step 1: Crawl navigation menu
                logger.info(f"[{domain}] Extracting navigation menu keywords...")
                menu_result = self.crawl_domain(domain, company_id)

                # Step 2: Crawl service pages
                logger.info(f"[{domain}] Extracting service keywords...")
                service_result = self.crawl_services(domain, company_id)

                # Combine results
                result = {
                    'success': menu_result['success'] and service_result['success'],
                    'pages_crawled': menu_result['pages_crawled'] + service_result['pages_crawled'],
                    'pages_failed': menu_result['pages_failed'] + service_result['pages_failed'],
                    'new_keywords': menu_result['new_keywords'] + service_result['new_keywords'],
                    'error': menu_result.get('error') or service_result.get('error'),
                    'menu_keywords': menu_result['keywords_found'],
                    'service_keywords': service_result['keywords_found'],
                    'service_links': service_result.get('service_links_found', 0)
                }

                logger.info(
                    f"[{domain}] Complete - Menu: {result['menu_keywords']} kw, "
                    f"Services: {result['service_keywords']} kw ({result['service_links']} pages), "
                    f"Total new: {result['new_keywords']}"
                )

                # Update job status
                if result['success']:
                    self.db.update_crawl_job(
                        job_id,
                        'completed',
                        pages_crawled=result['pages_crawled'],
                        pages_failed=result['pages_failed'],
                        new_keywords_found=result['new_keywords']
                    )
                    self.db.update_company_status(company_id, 'completed')
                    progress.update(success=True)
                else:
                    self.db.update_crawl_job(
                        job_id,
                        'failed',
                        pages_crawled=result['pages_crawled'],
                        pages_failed=result['pages_failed'],
                        error_message=result['error']
                    )
                    self.db.update_company_status(
                        company_id,
                        'failed',
                        error_message=result['error']
                    )
                    progress.update(success=False)

            except Exception as e:
                logger.error(f"Error processing company {company_id}: {e}", exc_info=True)
                self.db.update_company_status(
                    company_id,
                    'failed',
                    error_message=str(e)
                )
                progress.update(success=False)

            # Log progress
            processed += 1
            if processed % 10 == 0:
                logger.info(str(progress))
                stats = self.db.get_statistics()
                logger.info(
                    f"Stats - Pending: {stats['pending']}, "
                    f"Completed: {stats['completed']}, "
                    f"Failed: {stats['failed']}, "
                    f"Total Keywords: {stats['total_keywords']}"
                )

        # Final progress report
        logger.info("Crawler finished")
        logger.info(str(progress))

        final_stats = self.db.get_statistics()
        logger.info(
            f"Final Stats - Pending: {final_stats['pending']}, "
            f"Completed: {final_stats['completed']}, "
            f"Failed: {final_stats['failed']}, "
            f"Total Keywords: {final_stats['total_keywords']}"
        )

    def crawl_single_domain(self, domain: str) -> bool:
        """
        Crawl a specific domain on-demand, bypassing status checks.

        Args:
            domain: Domain to crawl

        Returns:
            True if successful, False otherwise
        """
        from utils import normalize_domain

        logger.info(f"On-demand crawl requested for: {domain}")

        # Normalize the domain
        normalized_domain = normalize_domain(domain)
        logger.info(f"Normalized domain: {normalized_domain}")

        # Check if domain exists in database
        company = self.db.get_company_by_domain(normalized_domain)

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
        logger.info("Forcing crawl (bypassing status check)")

        try:
            # Update status to in_progress
            self.db.update_company_status(company_id, 'in_progress')

            # Create crawl job
            job_id = self.db.create_crawl_job(company_id)
            logger.info(f"Created crawl job: {job_id}")

            # Step 1: Crawl navigation menu (section_type_id=1)
            logger.info("Step 1: Extracting navigation menu keywords...")
            menu_result = self.crawl_domain(normalized_domain, company_id)

            # Step 2: Crawl service pages (section_type_id=5,6)
            logger.info("Step 2: Extracting service keywords from dedicated pages...")
            service_result = self.crawl_services(normalized_domain, company_id)

            # Combine results from all section types
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
                self.db.update_crawl_job(
                    job_id,
                    'completed',
                    pages_crawled=result['pages_crawled'],
                    pages_failed=result['pages_failed'],
                    new_keywords_found=result['new_keywords']
                )
                self.db.update_company_status(company_id, 'completed')

                # Print comprehensive summary
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
                self.db.update_crawl_job(
                    job_id,
                    'failed',
                    pages_crawled=result['pages_crawled'],
                    pages_failed=result['pages_failed'],
                    error_message=result['error']
                )
                self.db.update_company_status(
                    company_id,
                    'failed',
                    error_message=result['error']
                )

                # Print error summary
                print("\n" + "=" * 70)
                print("COMPLETE EXTRACTION RESULTS")
                print("=" * 70)
                print(f"Domain:          {normalized_domain}")
                print(f"Status:          FAILED")
                print(f"Error:           {result['error']}")
                print(f"Job ID:          {job_id}")
                print("=" * 70 + "\n")

                return False

        except Exception as e:
            logger.error(f"Error during on-demand crawl: {e}", exc_info=True)
            self.db.update_company_status(
                company_id,
                'failed',
                error_message=str(e)
            )
            return False

    def stop(self) -> None:
        """Signal the crawler to stop gracefully."""
        logger.info("Stopping crawler...")
        self.should_stop = True

    def close(self) -> None:
        """Clean up resources."""
        if self.session:
            self.session.close()
        logger.info("Crawler resources cleaned up")
