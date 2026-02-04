#!/usr/bin/env python3
"""
Rommelmarkt Zoeker - Web scraper for rommelmarkten.be

A respectful web scraper that collects flea market (rommelmarkt) listings
from Flemish provinces in Belgium and stores them in a SQLite database.

Usage:
    python main.py                    # Default incremental scrape
    python main.py --full-refresh     # Force full refresh
    python main.py --export-json      # Export to JSON after scraping
    python main.py --config my.yaml   # Use custom config file
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import load_config
from src.utils.logging_setup import setup_logging
from src.scraper.listing_scraper import ListingScraper
from src.scraper.detail_scraper import DetailScraper
from src.storage.database import Database
from src.storage.json_export import export_to_json


# Dutch month names for URL construction
DUTCH_MONTHS = [
    'januari', 'februari', 'maart', 'april', 'mei', 'juni',
    'juli', 'augustus', 'september', 'oktober', 'november', 'december'
]


def get_months_to_scrape(config: dict) -> list:
    """
    Determine which months to scrape based on configuration.

    Args:
        config: Target configuration dictionary.

    Returns:
        List of Dutch month names to scrape.
    """
    selection = config.get('month_selection', 'next_3')

    # Check for explicit month list first
    if 'months' in config and isinstance(config['months'], list):
        return config['months']

    current_month_idx = datetime.now().month - 1  # 0-indexed

    if selection == 'all':
        return DUTCH_MONTHS

    elif selection == 'current':
        return [DUTCH_MONTHS[current_month_idx]]

    elif selection.startswith('next_'):
        try:
            count = int(selection.split('_')[1])
            return [
                DUTCH_MONTHS[(current_month_idx + i) % 12]
                for i in range(count + 1)  # +1 to include current month
            ]
        except (ValueError, IndexError):
            pass

    # Default to current + next 3 months
    return [
        DUTCH_MONTHS[(current_month_idx + i) % 12]
        for i in range(4)
    ]


def main():
    """Main entry point for the scraper."""
    parser = argparse.ArgumentParser(
        description='Rommelmarkten.be Web Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    Scrape current + next 3 months (incremental)
  python main.py --full-refresh     Re-scrape all events
  python main.py --export-json      Export database to JSON after scraping
  python main.py --config test.yaml Use alternate config file
        """
    )

    parser.add_argument(
        '--config', '-c',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )

    parser.add_argument(
        '--full-refresh', '-f',
        action='store_true',
        help='Force full refresh, re-scraping all events'
    )

    parser.add_argument(
        '--export-json', '-e',
        action='store_true',
        help='Export database to JSON after scraping'
    )

    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Dry run: show what would be scraped without fetching'
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup logging
    setup_logging(config.get('logging', {}))
    logger = logging.getLogger('main')

    logger.info("=" * 60)
    logger.info("Rommelmarkt Zoeker - Starting scraper")
    logger.info("=" * 60)

    # Determine what to scrape
    provinces = config['target']['provinces']
    months = get_months_to_scrape(config['target'])

    logger.info(f"Provinces: {', '.join(provinces)}")
    logger.info(f"Months: {', '.join(months)}")
    logger.info(f"Mode: {'full refresh' if args.full_refresh else 'incremental'}")

    if args.dry_run:
        logger.info("DRY RUN - No actual scraping will be performed")
        total_urls = len(provinces) * len(months)
        logger.info(f"Would scrape {total_urls} listing pages")
        return

    # Initialize components
    db = Database(
        db_path=config['storage']['database_path'],
        schema_path='schema.sql'
    )

    # Merge base_url into scraping config for scrapers
    scraping_config = config['scraping'].copy()
    scraping_config['base_url'] = config['target']['base_url']

    listing_scraper = ListingScraper(scraping_config)
    detail_scraper = DetailScraper(scraping_config)

    # Statistics
    total_events = 0
    new_events = 0
    updated_events = 0
    skipped_events = 0
    failed_events = 0

    try:
        for province in provinces:
            for month in months:
                logger.info("-" * 40)
                logger.info(f"Scraping: {month} in {province}")

                # Get list of events from listing page
                event_links = listing_scraper.scrape_listing_page(province, month)

                if not event_links:
                    logger.warning(f"No events found for {month} in {province}")
                    continue

                for link in event_links:
                    total_events += 1

                    # Check if event already exists (unless full refresh)
                    if not args.full_refresh and db.event_exists(link.id):
                        logger.debug(f"Skipping existing event {link.id}")
                        skipped_events += 1
                        continue

                    # Scrape detail page
                    event = detail_scraper.scrape_detail_page(link.url, link.id)

                    if event:
                        was_existing = db.event_exists(link.id)
                        db.upsert_event(event)

                        if was_existing:
                            updated_events += 1
                            logger.info(f"Updated: {event.naam} ({event.gemeente})")
                        else:
                            new_events += 1
                            logger.info(f"Added: {event.naam} ({event.gemeente})")
                    else:
                        failed_events += 1
                        logger.warning(f"Failed to scrape event {link.id}")

    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user")

    finally:
        # Close scrapers
        listing_scraper.close()
        detail_scraper.close()

    # Print summary
    logger.info("=" * 60)
    logger.info("Scraping complete!")
    logger.info(f"  Total events found: {total_events}")
    logger.info(f"  New events added: {new_events}")
    logger.info(f"  Events updated: {updated_events}")
    logger.info(f"  Events skipped (existing): {skipped_events}")
    logger.info(f"  Events failed: {failed_events}")
    logger.info(f"  Database total: {db.get_event_count()} events")
    logger.info("=" * 60)

    # Export to JSON if requested
    if args.export_json:
        export_path = config['storage']['json_export_path']
        filepath = export_to_json(db, export_path)
        logger.info(f"Exported to: {filepath}")


if __name__ == '__main__':
    main()
