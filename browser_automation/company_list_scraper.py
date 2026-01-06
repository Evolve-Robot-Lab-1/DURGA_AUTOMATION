#!/usr/bin/env python3
"""
Company List Scraper - Browser Automation Service
Handles pagination, clicking through lists, and extracting companies

Port: 3006
Dependencies: playwright, flask, flask-cors

Usage:
    python3 company_list_scraper.py
"""

import asyncio
import logging
import re
from urllib.parse import urlparse
from flask import Flask, request, jsonify
from flask_cors import CORS
from playwright.async_api import async_playwright, Browser, Page

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Site-specific configurations
SITE_CONFIGS = {
    'f6s.com': {
        'pagination': 'click_button',
        'next_selector': 'a.next-page, button:has-text("Next")',
        'company_card': '.startup-item, .company-card',
        'name_selector': 'h3, h2, .startup-name',
        'website_selector': 'a[href*="http"]:has-text("Website"), a.website-link'
    },
    'beststartup': {
        'pagination': 'url_pattern',
        'company_card': '.company-block, article',
        'name_selector': 'h2, h3',
        'website_selector': 'a[href*="http"]'
    },
    'tracxn.com': {
        'pagination': 'infinite_scroll',
        'company_card': '[class*="CompanyCard"], [class*="company"]',
        'name_selector': '[class*="CompanyName"], h3',
        'website_selector': 'a[class*="Website"], a[href*="http"]'
    },
    'clutch.co': {
        'pagination': 'click_button',
        'next_selector': 'a.next, button:has-text("Next")',
        'company_card': '.company-info, .provider',
        'name_selector': 'h3, h2',
        'website_selector': 'a.website_link'
    },
    'wellfound.com': {
        'pagination': 'infinite_scroll',
        'company_card': '[data-test="StartupResult"], .startup-link',
        'name_selector': 'h2, h3',
        'website_selector': 'a[href*="http"]'
    },
    # Generic fallback
    'generic': {
        'pagination': 'auto_detect',
        'company_card': 'article, .card, [class*="company"], [class*="startup"], [class*="listing"]',
        'name_selector': 'h1, h2, h3, h4',
        'website_selector': 'a[href*="http"]'
    }
}


class CompanyListScraper:
    """Browser automation for scraping company lists with pagination"""

    def __init__(self):
        self.browser = None
        self.page = None
        self.playwright = None

    async def initialize(self):
        """Launch Playwright browser"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            self.page = await context.new_page()
            logger.info("Playwright browser initialized")
            return self
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    async def close(self):
        """Close browser and playwright"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    def get_site_config(self, url):
        """Get site-specific configuration"""
        domain = urlparse(url).netloc.lower()

        for site_key, config in SITE_CONFIGS.items():
            if site_key in domain:
                logger.info(f"Using config for: {site_key}")
                return config

        logger.info("Using generic config")
        return SITE_CONFIGS['generic']

    async def handle_popups(self):
        """Handle cookie popups, modals, etc."""
        try:
            # Try to dismiss common popups
            popup_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accept Cookies")',
                'button:has-text("I Agree")',
                'button:has-text("Got it")',
                'button:has-text("Close")',
                'button[aria-label="Close"]',
                '.cookie-notice button',
                '#cookie-banner button'
            ]

            for selector in popup_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        logger.info(f"Dismissed popup: {selector}")
                        await asyncio.sleep(0.5)
                        break
                except:
                    continue
        except Exception as e:
            logger.debug(f"No popups to handle: {e}")

    async def extract_companies_from_page(self, config):
        """Extract companies from current page"""
        companies = []

        try:
            # Wait for content to load
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            await asyncio.sleep(1)

            # Find all company cards
            cards_selector = config['company_card']
            cards = await self.page.locator(cards_selector).all()

            logger.info(f"Found {len(cards)} potential company cards")

            for i, card in enumerate(cards):
                try:
                    # Try to extract name
                    name = None
                    try:
                        name_elem = card.locator(config['name_selector']).first
                        name = await name_elem.text_content(timeout=2000)
                        name = name.strip() if name else None
                    except:
                        pass

                    # Try to extract website
                    website = None
                    try:
                        website_elem = card.locator(config['website_selector']).first
                        website = await website_elem.get_attribute('href', timeout=2000)
                        # Clean up website URL
                        if website:
                            website = website.strip()
                            # Skip if it's a relative URL or not http/https
                            if not website.startswith('http'):
                                website = None
                    except:
                        pass

                    # If we got a name, add the company
                    if name and len(name) > 2:
                        company_data = {
                            'name': name,
                            'website': website or '',
                            'source': urlparse(self.page.url).netloc
                        }
                        companies.append(company_data)
                        logger.debug(f"Extracted: {name} | {website}")

                except Exception as e:
                    logger.debug(f"Error extracting from card {i}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error extracting companies from page: {e}")

        return companies

    async def detect_pagination_type(self, config):
        """Auto-detect pagination type if not specified"""
        if config['pagination'] != 'auto_detect':
            return config['pagination']

        # Check for "Next" button
        next_selectors = [
            'button:has-text("Next")',
            'a:has-text("Next")',
            'a[rel="next"]',
            'button[aria-label*="Next"]'
        ]

        for selector in next_selectors:
            if await self.page.locator(selector).count() > 0:
                logger.info("Detected: click_button pagination")
                return 'click_button'

        # Check for "Load More" button
        load_more_selectors = [
            'button:has-text("Load More")',
            'button:has-text("Show More")',
            'a:has-text("Load More")'
        ]

        for selector in load_more_selectors:
            if await self.page.locator(selector).count() > 0:
                logger.info("Detected: load_more pagination")
                return 'load_more'

        # Default to infinite scroll
        logger.info("Detected: infinite_scroll (fallback)")
        return 'infinite_scroll'

    async def get_company_profile_links(self, config):
        """
        Extract URLs to individual company profile pages from list page.
        Returns list of URLs to click into.
        """
        links = []

        try:
            await self.page.wait_for_load_state('networkidle', timeout=10000)

            # Find all company cards
            cards = await self.page.locator(config['company_card']).all()

            for card in cards:
                try:
                    # Try to find link to company profile within card
                    # Prioritize links that go to profile pages (not external websites)
                    link_selectors = [
                        'a[href*="/company/"]',
                        'a[href*="/companies/"]',
                        'a[href*="/startup/"]',
                        'a[href*="/profile/"]',
                        'a.company-link',
                        'a.startup-link',
                        'a'  # Fallback: any link
                    ]

                    profile_link = None
                    for selector in link_selectors:
                        link_elem = card.locator(selector).first
                        if await link_elem.count() > 0:
                            href = await link_elem.get_attribute('href')
                            if href:
                                # Convert relative URLs to absolute
                                if href.startswith('/'):
                                    base_url = f"{self.page.url.split('/')[0]}//{self.page.url.split('/')[2]}"
                                    href = base_url + href

                                # Skip external websites, only aggregator profiles
                                current_domain = urlparse(self.page.url).netloc
                                link_domain = urlparse(href).netloc

                                if current_domain in link_domain or link_domain == '':
                                    profile_link = href
                                    break

                    if profile_link and profile_link not in links:
                        links.append(profile_link)

                except Exception as e:
                    logger.debug(f"Error extracting link from card: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error getting company profile links: {e}")

        return links

    async def extract_company_details_from_profile(self, company_url):
        """
        Click into company profile and extract all available details.
        This extracts from the AGGREGATOR'S profile page (e.g., f6s.com/companies/xyz)
        """
        try:
            # Navigate to company profile
            await self.page.goto(company_url, wait_until='networkidle', timeout=15000)
            await asyncio.sleep(1)

            # Extract comprehensive details
            details = {
                'name': '',
                'website': '',
                'description': '',
                'emails': [],
                'phones': [],
                'address': '',
                'social_links': {},
                'source_url': company_url
            }

            # Extract name
            for selector in ['h1', 'h2.company-name', '[class*="company-name"]', '[class*="CompanyName"]', 'h2', 'h3']:
                try:
                    elem = self.page.locator(selector).first
                    if await elem.count() > 0:
                        text = await elem.text_content()
                        if text:
                            details['name'] = text.strip()
                            break
                except:
                    pass

            # Extract website
            for selector in ['a:has-text("Website")', 'a.website', 'a[class*="website"]', 'a:has-text("Visit")', 'a[href*="http"]']:
                try:
                    elem = self.page.locator(selector).first
                    if await elem.count() > 0:
                        href = await elem.get_attribute('href')
                        if href and href.startswith('http'):
                            # Skip social media links
                            if not any(sm in href for sm in ['linkedin', 'twitter', 'facebook', 'instagram']):
                                details['website'] = href
                                break
                except:
                    pass

            # Extract description
            for selector in ['.description', '[class*="description"]', 'p.about', '.bio', 'p', '.content']:
                try:
                    elem = self.page.locator(selector).first
                    if await elem.count() > 0:
                        text = await elem.text_content()
                        if text and len(text) > 50:  # At least 50 chars for description
                            details['description'] = text.strip()[:500]  # Limit to 500 chars
                            break
                except:
                    pass

            # Extract emails and phones from page content
            page_content = await self.page.content()

            # Extract emails
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = list(set(re.findall(email_pattern, page_content)))
            # Filter out common false positives
            details['emails'] = [e for e in emails if not any(x in e.lower() for x in ['example', 'test', 'dummy', '@sentry'])][:5]

            # Extract phones
            phone_pattern = r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]'
            phones = list(set(re.findall(phone_pattern, page_content)))
            details['phones'] = [p.strip() for p in phones if len(p.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')) >= 10][:3]

            # Extract social links
            social_patterns = {
                'linkedin': r'(https?://[^\"\'>\s]*linkedin\.com/company/[\w-]+)',
                'twitter': r'(https?://[^\"\'>\s]*twitter\.com/[\w-]+)',
                'facebook': r'(https?://[^\"\'>\s]*facebook\.com/[\w-]+)'
            }
            for platform, pattern in social_patterns.items():
                matches = re.findall(pattern, page_content)
                if matches:
                    details['social_links'][platform] = matches[0]

            logger.info(f"Extracted details for: {details['name']}")
            return details

        except Exception as e:
            logger.error(f"Error extracting company details from {company_url}: {e}")
            return None

    async def scrape_with_pagination(self, url, max_companies=100):
        """
        Main scraping logic with click-through extraction.
        For each company card: click → extract details → go back → next
        """
        all_companies = []
        seen_urls = set()
        pages_scraped = 0
        max_pages = 10

        try:
            logger.info(f"Navigating to: {url}")
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            await self.handle_popups()

            config = self.get_site_config(url)
            pagination_type = await self.detect_pagination_type(config)

            while len(all_companies) < max_companies and pages_scraped < max_pages:
                # Get all company card links on current page
                company_links = await self.get_company_profile_links(config)

                logger.info(f"Page {pages_scraped + 1}: Found {len(company_links)} company links")

                # Click into each company profile
                for i, company_link in enumerate(company_links):
                    if len(all_companies) >= max_companies:
                        break

                    # Skip if already processed
                    if company_link in seen_urls:
                        continue
                    seen_urls.add(company_link)

                    # Extract details from company profile
                    company_data = await self.extract_company_details_from_profile(company_link)

                    if company_data and company_data.get('name'):
                        all_companies.append(company_data)
                        logger.info(f"[{len(all_companies)}/{max_companies}] Scraped: {company_data['name']}")

                    # Go back to list page
                    await self.page.go_back()
                    await asyncio.sleep(0.5)  # Brief pause to let page stabilize

                pages_scraped += 1

                # Handle pagination to next page of list
                if len(all_companies) >= max_companies:
                    break

                has_next_page = await self.handle_pagination(pagination_type, config)
                if not has_next_page:
                    logger.info("No more pages to scrape")
                    break

                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Error during scraping: {e}")

        return {
            'companies': all_companies,
            'pages': pages_scraped,
            'total': len(all_companies)
        }

    async def handle_pagination(self, pagination_type, config):
        """Handle different pagination strategies"""
        try:
            if pagination_type == 'click_button':
                return await self.click_next_button(config)
            elif pagination_type == 'load_more':
                return await self.click_load_more(config)
            elif pagination_type == 'infinite_scroll':
                return await self.infinite_scroll()
            elif pagination_type == 'url_pattern':
                return await self.url_pagination()
            else:
                logger.warning(f"Unknown pagination type: {pagination_type}")
                return False
        except Exception as e:
            logger.error(f"Pagination error: {e}")
            return False

    async def click_next_button(self, config):
        """Click 'Next' button pagination"""
        try:
            next_selector = config.get('next_selector', 'button:has-text("Next"), a:has-text("Next"), a[rel="next"]')
            next_btn = self.page.locator(next_selector).first

            if await next_btn.count() > 0:
                # Check if button is enabled
                is_disabled = await next_btn.get_attribute('disabled')
                is_visible = await next_btn.is_visible()

                if not is_disabled and is_visible:
                    await next_btn.click()
                    await self.page.wait_for_load_state('networkidle', timeout=10000)
                    logger.info("Clicked next button")
                    return True

            logger.info("Next button not available")
            return False
        except Exception as e:
            logger.error(f"Error clicking next button: {e}")
            return False

    async def click_load_more(self, config):
        """Click 'Load More' button"""
        try:
            load_more_selectors = [
                'button:has-text("Load More")',
                'button:has-text("Show More")',
                'a:has-text("Load More")'
            ]

            for selector in load_more_selectors:
                btn = self.page.locator(selector).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(2)  # Wait for content to load
                    logger.info("Clicked load more button")
                    return True

            return False
        except Exception as e:
            logger.error(f"Error clicking load more: {e}")
            return False

    async def infinite_scroll(self):
        """Handle infinite scroll pagination"""
        try:
            # Get current height
            prev_height = await self.page.evaluate("document.body.scrollHeight")

            # Scroll to bottom
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            # Check if new content loaded
            new_height = await self.page.evaluate("document.body.scrollHeight")

            if new_height > prev_height:
                logger.info(f"Scrolled: {prev_height} -> {new_height}")
                return True
            else:
                logger.info("Reached end of infinite scroll")
                return False
        except Exception as e:
            logger.error(f"Error with infinite scroll: {e}")
            return False

    async def url_pagination(self):
        """Handle URL-based pagination"""
        try:
            current_url = self.page.url

            # Try common pagination URL patterns
            patterns = [
                (r'/page/(\d+)', lambda m: f'/page/{int(m.group(1)) + 1}'),
                (r'\?page=(\d+)', lambda m: f'?page={int(m.group(1)) + 1}'),
                (r'&page=(\d+)', lambda m: f'&page={int(m.group(1)) + 1}')
            ]

            for pattern, replacement_fn in patterns:
                match = re.search(pattern, current_url)
                if match:
                    next_url = re.sub(pattern, replacement_fn(match), current_url)
                    await self.page.goto(next_url, wait_until='networkidle', timeout=15000)
                    logger.info(f"URL pagination: {next_url}")
                    return True

            # If no pattern found, try appending /page/2
            if '/page/' not in current_url:
                next_url = current_url.rstrip('/') + '/page/2'
                await self.page.goto(next_url, wait_until='networkidle', timeout=15000)
                logger.info(f"URL pagination: {next_url}")
                return True

            return False
        except Exception as e:
            logger.error(f"Error with URL pagination: {e}")
            return False


# Flask API endpoints

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'DURGA Company List Scraper',
        'version': '1.0'
    })


@app.route('/api/scrape-list', methods=['POST'])
def scrape_list():
    """
    Scrape company list with pagination

    Request JSON:
    {
        "url": "https://example.com/company-list",
        "max_companies": 100
    }
    """
    try:
        data = request.json
        url = data.get('url')
        max_companies = data.get('max_companies', 100)

        if not url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        logger.info(f"Scraping request: {url} (max: {max_companies})")

        # Run async scraping
        scraper = asyncio.run(scrape_list_async(url, max_companies))

        return jsonify(scraper)

    except Exception as e:
        logger.error(f"Error in scrape_list endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


async def scrape_list_async(url, max_companies):
    """Async wrapper for scraping"""
    scraper = None
    try:
        scraper = await CompanyListScraper().initialize()
        result = await scraper.scrape_with_pagination(url, max_companies)

        return {
            'success': True,
            'companies': result['companies'],
            'metadata': {
                'total_found': result['total'],
                'pages_scraped': result['pages'],
                'method': 'playwright_clickthrough',  # Indicates click-through extraction
                'url': url
            }
        }
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'companies': [],
            'metadata': {}
        }
    finally:
        if scraper:
            await scraper.close()


if __name__ == '__main__':
    logger.info("Starting DURGA Company List Scraper on port 3006...")
    app.run(host='0.0.0.0', port=3006, debug=False, threaded=True)
