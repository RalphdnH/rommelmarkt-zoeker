"""Configuration loader for rommelmarkt scraper."""

import os
from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to the configuration file.

    Returns:
        Dictionary containing configuration values.

    Raises:
        FileNotFoundError: If config file doesn't exist.
        yaml.YAMLError: If config file is invalid YAML.
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Ensure required sections exist with defaults
    config.setdefault('scraping', {})
    config.setdefault('target', {})
    config.setdefault('storage', {})
    config.setdefault('logging', {})

    # Set scraping defaults
    scraping = config['scraping']
    scraping.setdefault('delay_seconds', 2.5)
    scraping.setdefault('max_retries', 3)
    scraping.setdefault('retry_delay_seconds', 5)
    scraping.setdefault('user_agent', 'RommelmarktZoeker/1.0')
    scraping.setdefault('timeout_seconds', 30)

    # Set target defaults
    target = config['target']
    target.setdefault('base_url', 'https://www.rommelmarkten.be')
    target.setdefault('provinces', [
        'antwerpen', 'limburg', 'oost-vlaanderen',
        'vlaams-brabant', 'west-vlaanderen'
    ])
    target.setdefault('month_selection', 'next_3')

    # Set storage defaults
    storage = config['storage']
    storage.setdefault('database_path', 'data/rommelmarkten.db')
    storage.setdefault('json_export_path', 'data/exports')

    # Set logging defaults
    logging_config = config['logging']
    logging_config.setdefault('level', 'INFO')
    logging_config.setdefault('file', 'logs/scraper.log')

    # Create directories if they don't exist
    db_dir = Path(storage['database_path']).parent
    export_dir = Path(storage['json_export_path'])
    log_dir = Path(logging_config['file']).parent if logging_config['file'] else None

    for directory in [db_dir, export_dir, log_dir]:
        if directory:
            directory.mkdir(parents=True, exist_ok=True)

    return config
