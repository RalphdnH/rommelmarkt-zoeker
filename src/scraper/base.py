"""Base scraper class with rate limiting and retry logic."""

import logging
import time
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class BaseScraper:
    """Base scraper with rate limiting, retry logic, and session management."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the base scraper.

        Args:
            config: Scraping configuration dictionary.
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = self._create_session()
        self.last_request_time: float = 0

    def _create_session(self) -> requests.Session:
        """Create and configure a requests session with retry logic."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.get('max_retries', 3),
            backoff_factor=self.config.get('retry_delay_seconds', 5),
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Set headers
        session.headers.update({
            'User-Agent': self.config.get('user_agent', 'RommelmarktZoeker/1.0'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'nl-BE,nl;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })

        return session

    def _respect_rate_limit(self) -> None:
        """Ensure minimum delay between requests."""
        delay = self.config.get('delay_seconds', 2.5)
        elapsed = time.time() - self.last_request_time

        if elapsed < delay:
            sleep_time = delay - elapsed
            self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

    def fetch(self, url: str) -> Optional[str]:
        """
        Fetch URL with rate limiting and error handling.

        Args:
            url: The URL to fetch.

        Returns:
            HTML content as string, or None if request failed.
        """
        self._respect_rate_limit()

        try:
            self.logger.info(f"Fetching: {url}")
            timeout = self.config.get('timeout_seconds', 30)
            response = self.session.get(url, timeout=timeout)
            self.last_request_time = time.time()

            response.raise_for_status()
            return response.text

        except requests.Timeout:
            self.logger.error(f"Timeout fetching {url}")
            return None
        except requests.HTTPError as e:
            self.logger.error(f"HTTP error fetching {url}: {e.response.status_code}")
            return None
        except requests.RequestException as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None

    def close(self) -> None:
        """Close the session."""
        self.session.close()
