"""Scraper for rommelmarkten.be event detail pages."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup, Tag

from ..models.event import Event
from .base import BaseScraper
from .email_decoder import decode_cloudflare_email


# Dutch month name mapping
DUTCH_MONTHS = {
    'januari': 1, 'jan': 1,
    'februari': 2, 'feb': 2,
    'maart': 3, 'mrt': 3, 'mar': 3,
    'april': 4, 'apr': 4,
    'mei': 5,
    'juni': 6, 'jun': 6,
    'juli': 7, 'jul': 7,
    'augustus': 8, 'aug': 8,
    'september': 9, 'sep': 9, 'sept': 9,
    'oktober': 10, 'okt': 10, 'oct': 10,
    'november': 11, 'nov': 11,
    'december': 12, 'dec': 12,
}


class DetailScraper(BaseScraper):
    """Scraper for individual event detail pages."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the detail scraper.

        Args:
            config: Scraping configuration dictionary.
        """
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://www.rommelmarkten.be')

    def scrape_detail_page(self, url: str, event_id: int) -> Optional[Event]:
        """
        Scrape an event detail page and extract all information.

        Args:
            url: Full URL to the event detail page.
            event_id: The event ID from the URL.

        Returns:
            Event object with extracted data, or None if scraping failed.
        """
        html = self.fetch(url)

        if not html:
            self.logger.warning(f"Failed to fetch detail page: {url}")
            return None

        soup = BeautifulSoup(html, 'lxml')

        try:
            # Extract location info (gemeente, postcode, adres)
            location_info = self._extract_location_info(soup)

            # Extract title, with URL slug as fallback
            naam = self._extract_title(soup)
            if naam == "Onbekend":
                # Try to extract from URL slug
                naam = self._title_from_url(url)

            event = Event(
                id=event_id,
                naam=naam,
                gemeente=location_info.get('gemeente'),
                postcode=location_info.get('postcode'),
                adres=location_info.get('adres'),
                locatie_naam=self._extract_locatie_naam(soup),
                datum=self._extract_datum(soup),
                start_tijd=self._extract_start_tijd(soup),
                eind_tijd=self._extract_eind_tijd(soup),
                types=self._extract_types(soup),
                inkom_prijs=self._extract_inkom_prijs(soup),
                standplaats_prijs=self._extract_standplaats_prijs(soup),
                organisator=self._extract_organisator(soup),
                telefoon=self._extract_telefoon(soup),
                email=self._extract_email(soup),
                website=self._extract_website(soup),
                beschrijving=self._extract_beschrijving(soup),
                afbeelding_url=self._extract_afbeelding(soup),
                source_url=url
            )

            self.logger.debug(f"Extracted event: {event.naam}")
            return event

        except Exception as e:
            self.logger.error(f"Error parsing detail page {url}: {e}")
            return None

    def _title_from_url(self, url: str) -> str:
        """Extract a title from the URL slug."""
        # URL format: /rommelmarkt/12345/event-name-city
        match = re.search(r'/rommelmarkt/\d+/(.+?)(?:\?|$)', url)
        if match:
            slug = match.group(1)
            # Convert slug to title: replace hyphens with spaces, title case
            title = slug.replace('-', ' ').strip()
            # Clean up common suffixes like city names
            title = re.sub(r'\s+\d{4}\s*$', '', title)  # Remove postcodes
            return title.title()
        return "Onbekend"

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract event title from page."""
        # First try: Look in the <title> tag which usually has the event name
        title_tag = soup.find('title')
        if title_tag:
            text = title_tag.get_text(strip=True)
            # Format is typically: "Event Name | rommelmarkten.be"
            if ' | ' in text:
                return text.split(' | ')[0].strip()

        # Second try: Look for h3 that doesn't contain section headers
        section_headers = ['thema', 'waar', 'contact', 'wanneer', 'info', 'prijs']
        for h3 in soup.find_all('h3'):
            text = h3.get_text(strip=True)
            # Skip if it looks like a section header
            if text and not any(header in text.lower() for header in section_headers):
                # Skip if it contains an image (usually location markers)
                if not h3.find('img'):
                    return text

        # Third try: Extract from URL slug if available
        # This is handled by the caller as fallback

        return "Onbekend"

    def _extract_location_info(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """
        Extract gemeente, postcode, and adres from location text.

        The page structure has a "Waar" (Where) section with location info.
        Format is typically:
        - Address line (e.g., "Kapelanielaan 27")
        - Postcode + City (e.g., "9140 TEMSE")
        """
        result = {'gemeente': None, 'postcode': None, 'adres': None}

        # Get text and normalize whitespace (replace multiple spaces/newlines with single space)
        raw_text = soup.get_text()
        text = ' '.join(raw_text.split())

        # Pattern 1: Look for Belgian postcode followed by city
        # Format: "9140 TEMSE" or "9140 Temse"
        postcode_pattern = re.compile(
            r'(\d{4})\s+([A-Z][A-Za-z\-]+(?:\s*-\s*[A-Za-z]+)?)',
        )
        match = postcode_pattern.search(text)
        if match:
            result['postcode'] = match.group(1)
            result['gemeente'] = match.group(2).strip().title()

        # Pattern 2: Look for street address with common Belgian street suffixes
        # Street name + number, e.g., "Kapelanielaan 27", "Grote Markt 1"
        street_suffixes = (
            'straat|laan|plein|weg|baan|dreef|steenweg|lei|kaai|ring|'
            'boulevard|dijk|gracht|singel|pad|hof|park|wijk|veld|markt'
        )
        address_pattern = re.compile(
            rf'\b([A-Z][a-z]+(?:[a-z]*)(?:{street_suffixes}))\s+(\d+[A-Za-z]?)\b',
            re.IGNORECASE
        )
        match = address_pattern.search(text)
        if match:
            result['adres'] = match.group(0).strip()
        else:
            # Fallback: look for multi-word street names like "Grote Markt 1"
            multiword_pattern = re.compile(
                rf'\b([A-Z][a-z]+\s+(?:[A-Z]?[a-z]+\s+)*(?:{street_suffixes}))\s+(\d+[A-Za-z]?)\b',
                re.IGNORECASE
            )
            match = multiword_pattern.search(text)
            if match:
                result['adres'] = match.group(0).strip()

        return result

    def _parse_location_text(self, text: str) -> Dict[str, Optional[str]]:
        """Parse location text into components."""
        result = {'gemeente': None, 'postcode': None, 'adres': None}

        # Pattern: GEMEENTE (POSTCODE) Adres
        match = re.match(
            r'^([A-Z][A-Za-z\s\-]+?)\s*\((\d{4})\)\s*(.+)?$',
            text.strip()
        )
        if match:
            result['gemeente'] = match.group(1).strip().title()
            result['postcode'] = match.group(2)
            if match.group(3):
                result['adres'] = match.group(3).strip()

        return result

    def _extract_locatie_naam(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract venue/location name (h4 element)."""
        # Venue name is often in h4 before the main title
        h4_elements = soup.find_all('h4')
        for h4 in h4_elements:
            text = h4.get_text(strip=True)
            # Skip date headers (contain day names)
            if not any(day in text.lower() for day in
                      ['maandag', 'dinsdag', 'woensdag', 'donderdag',
                       'vrijdag', 'zaterdag', 'zondag']):
                return text
        return None

    def _extract_datum(self, soup: BeautifulSoup) -> Optional[date]:
        """Extract event date from page."""
        # Look for date patterns in the page text
        text = soup.get_text()

        # Pattern: "za 7 feb 2026" or "zaterdag 7 februari 2026"
        date_pattern = re.compile(
            r'(?:ma|di|wo|do|vr|za|zo|maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\s+'
            r'(\d{1,2})\s+'
            r'(jan(?:uari)?|feb(?:ruari)?|mrt|mar(?:t)?|apr(?:il)?|mei|jun(?:i)?|jul(?:i)?|'
            r'aug(?:ustus)?|sep(?:t(?:ember)?)?|okt(?:ober)?|oct|nov(?:ember)?|dec(?:ember)?)\s+'
            r'(\d{4})',
            re.IGNORECASE
        )

        match = date_pattern.search(text)
        if match:
            day = int(match.group(1))
            month_str = match.group(2).lower()
            year = int(match.group(3))

            month = DUTCH_MONTHS.get(month_str)
            if month:
                try:
                    return date(year, month, day)
                except ValueError:
                    pass

        return None

    def _extract_start_tijd(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract start time from page."""
        times = self._extract_times(soup)
        return times[0] if times else None

    def _extract_eind_tijd(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract end time from page."""
        times = self._extract_times(soup)
        return times[1] if len(times) > 1 else None

    def _extract_times(self, soup: BeautifulSoup) -> List[str]:
        """Extract start and end times from page."""
        text = soup.get_text()

        # Pattern: "9:00 - 17:30" or "09:00 tot 17:30"
        time_pattern = re.compile(
            r'(\d{1,2}[:.]\d{2})\s*[-–tot]+\s*(\d{1,2}[:.]\d{2})'
        )

        match = time_pattern.search(text)
        if match:
            start = match.group(1).replace('.', ':')
            end = match.group(2).replace('.', ':')
            return [start, end]

        return []

    def _extract_types(self, soup: BeautifulSoup) -> List[str]:
        """Extract event types (badges/tags)."""
        types = []

        # Known event type keywords
        known_types = [
            'rommelmarkt', 'binnenrommelmarkt', 'buitenrommelmarkt',
            'antiekbeurs', 'brocante beurs', 'brocantebeurs',
            'kinderrommelmarkt', 'tweedehandsmarkt', 'vlooienmarkt',
            'verzamelbeurs', 'curiosamarkt', 'garageverkoop'
        ]

        # Look for badge-style elements
        for element in soup.find_all(['span', 'a', 'div'], class_=re.compile(
            r'badge|btn|theme|tag|label|category', re.I
        )):
            text = element.get_text(strip=True).lower()
            if text in known_types or any(kt in text for kt in known_types):
                types.append(text.title())

        # Deduplicate while preserving order
        seen = set()
        unique_types = []
        for t in types:
            if t.lower() not in seen:
                seen.add(t.lower())
                unique_types.append(t)

        return unique_types

    def _extract_inkom_prijs(self, soup: BeautifulSoup) -> Optional[Decimal]:
        """Extract entrance price."""
        return self._extract_price(soup, ['inkom', 'toegang', 'entree', 'entrance'])

    def _extract_standplaats_prijs(self, soup: BeautifulSoup) -> Optional[Decimal]:
        """Extract booth/stand price."""
        return self._extract_price(soup, ['standplaats', 'stand', 'tafel', 'kraam'])

    def _extract_price(self, soup: BeautifulSoup, keywords: List[str]) -> Optional[Decimal]:
        """
        Extract a price value based on nearby keywords.

        Args:
            soup: BeautifulSoup object.
            keywords: List of keywords that indicate this price type.

        Returns:
            Price as Decimal, or None if not found.
        """
        text = soup.get_text()

        for keyword in keywords:
            # Pattern: "Inkom 4,50 €" or "Standplaats: 9 EUR" etc.
            pattern = re.compile(
                rf'{keyword}[:\s]*\**(\d+(?:[,\.]\d+)?)\s*(?:€|EUR|euro)?\**',
                re.IGNORECASE
            )
            match = pattern.search(text)
            if match:
                price_str = match.group(1).replace(',', '.')
                try:
                    return Decimal(price_str)
                except InvalidOperation:
                    continue

        return None

    def _extract_organisator(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract organizer name."""
        # Look for text after "Organisator:" or in strong/bold tags
        text = soup.get_text()

        patterns = [
            r'(?:organisator|georganiseerd door)[:\s]*([^\n,]+)',
            r'(?:org\.?)[:\s]*([^\n,]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                org = match.group(1).strip()
                # Clean up common suffixes
                org = re.sub(r'\s*(tel|email|www|http).*$', '', org, flags=re.I)
                if org and len(org) > 2:
                    return org

        return None

    def _extract_telefoon(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract phone number."""
        text = soup.get_text()

        # Belgian phone patterns
        patterns = [
            r'(?:tel(?:efoon)?|gsm|phone)[.:\s]*(\+?32[\s./\-]?(?:\d[\s./\-]?){8,})',
            r'(?:tel(?:efoon)?|gsm|phone)[.:\s]*(0\d[\s./\-]?(?:\d[\s./\-]?){7,})',
            r'(\+32[\s./\-]?\d[\s./\-]?(?:\d[\s./\-]?){7,})',
            r'(0\d{1,3}[\s./\-]?\d{2}[\s./\-]?\d{2}[\s./\-]?\d{2})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                phone = match.group(1).strip()
                # Normalize
                phone = re.sub(r'[\s./\-]+', ' ', phone)
                return phone

        return None

    def _extract_email(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract and decode email address."""
        # Look for Cloudflare-protected email
        cf_link = soup.find('a', href=re.compile(r'/cdn-cgi/l/email-protection'))
        if cf_link:
            href = cf_link.get('href', '')
            match = re.search(r'#([a-f0-9]+)$', href, re.I)
            if match:
                decoded = decode_cloudflare_email(match.group(1))
                if decoded and '@' in decoded:
                    return decoded

        # Look for data-cfemail attribute
        cf_span = soup.find(attrs={'data-cfemail': True})
        if cf_span:
            encoded = cf_span.get('data-cfemail', '')
            decoded = decode_cloudflare_email(encoded)
            if decoded and '@' in decoded:
                return decoded

        # Look for regular email pattern
        text = soup.get_text()
        email_pattern = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
        match = email_pattern.search(text)
        if match:
            return match.group(0)

        return None

    def _extract_website(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract website URL."""
        # Look for external links
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            # Skip internal links and email links
            if href.startswith('http') and 'rommelmarkten.be' not in href:
                if not href.startswith('mailto:'):
                    return href

        # Look for URL in text
        text = soup.get_text()
        url_pattern = re.compile(
            r'(?:website|www|http)[:\s]*(https?://[^\s<>"]+|www\.[^\s<>"]+)',
            re.IGNORECASE
        )
        match = url_pattern.search(text)
        if match:
            url = match.group(1)
            if not url.startswith('http'):
                url = 'http://' + url
            return url

        return None

    def _extract_beschrijving(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract event description."""
        # Look for description in paragraph tags
        paragraphs = soup.find_all('p')

        descriptions = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            # Skip very short or irrelevant text
            if len(text) > 50 and not any(skip in text.lower() for skip in
                ['cookie', 'privacy', 'copyright', 'advertentie']):
                descriptions.append(text)

        if descriptions:
            return '\n\n'.join(descriptions[:3])  # Limit to first 3 paragraphs

        return None

    def _extract_afbeelding(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract event poster/image URL."""
        # Look for images in content area
        for img in soup.find_all('img', src=True):
            src = img.get('src', '')
            # Look for poster/affiche images
            if any(indicator in src.lower() for indicator in
                   ['affiche', 'poster', 'flyer', 'banner']):
                if src.startswith('/'):
                    return f"{self.base_url}{src}"
                return src

        # Look for content images
        for img in soup.find_all('img', src=re.compile(r'/content/', re.I)):
            src = img.get('src', '')
            if src.startswith('/'):
                return f"{self.base_url}{src}"
            return src

        return None
