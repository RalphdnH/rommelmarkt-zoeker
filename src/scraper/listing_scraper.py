"""Scraper for rommelmarkten.be listing pages."""

import re
from dataclasses import dataclass
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from .base import BaseScraper


@dataclass
class EventLink:
    """Represents a link to an event detail page."""
    id: int
    slug: str
    url: str


class ListingScraper(BaseScraper):
    """Scraper for province/month listing pages."""

    # Pattern to match event detail URLs
    EVENT_LINK_PATTERN = re.compile(r'/rommelmarkt/(\d+)/(.+)')

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the listing scraper.

        Args:
            config: Scraping configuration dictionary.
        """
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://www.rommelmarkten.be')

    def scrape_listing_page(self, province: str, month: str) -> List[EventLink]:
        """
        Scrape a listing page and extract all event links.

        Args:
            province: Province name in Dutch (e.g., 'oost-vlaanderen').
            month: Month name in Dutch (e.g., 'februari').

        Returns:
            List of EventLink objects with event IDs, slugs, and URLs.
        """
        url = f"{self.base_url}/rommelmarkten-tijdens-{month}-in-{province}"
        html = self.fetch(url)

        if not html:
            self.logger.warning(f"Failed to fetch listing page: {url}")
            return []

        soup = BeautifulSoup(html, 'lxml')
        event_links = []

        # Find all links matching the event detail pattern
        for link in soup.find_all('a', href=self.EVENT_LINK_PATTERN):
            href = link.get('href')
            match = self.EVENT_LINK_PATTERN.match(href)

            if match:
                event_id = int(match.group(1))
                slug = match.group(2)

                # Build full URL if href is relative
                if href.startswith('/'):
                    full_url = f"{self.base_url}{href}"
                else:
                    full_url = href

                event_links.append(EventLink(
                    id=event_id,
                    slug=slug,
                    url=full_url
                ))

        # Deduplicate (same event may appear multiple times on the page)
        seen_ids = set()
        unique_links = []
        for link in event_links:
            if link.id not in seen_ids:
                seen_ids.add(link.id)
                unique_links.append(link)

        self.logger.info(
            f"Found {len(unique_links)} unique events for {month} in {province}"
        )
        return unique_links
