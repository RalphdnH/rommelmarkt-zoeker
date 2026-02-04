"""JSON export functionality for rommelmarkt data."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .database import Database


def export_to_json(
    db: Database,
    export_path: str,
    filename: Optional[str] = None
) -> str:
    """
    Export all events from database to JSON file.

    Args:
        db: Database instance to export from.
        export_path: Directory path for exports.
        filename: Optional custom filename. If not provided,
                  generates timestamped filename.

    Returns:
        Full path to the exported JSON file.
    """
    logger = logging.getLogger('json_export')

    # Ensure export directory exists
    export_dir = Path(export_path)
    export_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename if not provided
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"rommelmarkten_{timestamp}.json"

    filepath = export_dir / filename

    # Get all events
    events = db.get_all_events()

    # Create export structure
    export_data = {
        'metadata': {
            'exported_at': datetime.now().isoformat(),
            'total_events': len(events),
            'source': 'rommelmarkten.be'
        },
        'events': events
    }

    # Write to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

    logger.info(f"Exported {len(events)} events to {filepath}")
    return str(filepath)


def export_filtered_to_json(
    db: Database,
    export_path: str,
    gemeente: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    filename: Optional[str] = None
) -> str:
    """
    Export filtered events from database to JSON file.

    Args:
        db: Database instance to export from.
        export_path: Directory path for exports.
        gemeente: Optional municipality filter.
        start_date: Optional start date filter (YYYY-MM-DD).
        end_date: Optional end date filter (YYYY-MM-DD).
        filename: Optional custom filename.

    Returns:
        Full path to the exported JSON file.
    """
    logger = logging.getLogger('json_export')

    # Ensure export directory exists
    export_dir = Path(export_path)
    export_dir.mkdir(parents=True, exist_ok=True)

    # Get filtered events
    if gemeente:
        events = db.get_events_by_gemeente(gemeente)
    elif start_date and end_date:
        events = db.get_events_by_date_range(start_date, end_date)
    else:
        events = db.get_all_events()

    # Generate filename if not provided
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        suffix = ""
        if gemeente:
            suffix = f"_{gemeente.lower().replace(' ', '_')}"
        filename = f"rommelmarkten{suffix}_{timestamp}.json"

    filepath = export_dir / filename

    # Create export structure
    filters_applied = {}
    if gemeente:
        filters_applied['gemeente'] = gemeente
    if start_date:
        filters_applied['start_date'] = start_date
    if end_date:
        filters_applied['end_date'] = end_date

    export_data = {
        'metadata': {
            'exported_at': datetime.now().isoformat(),
            'total_events': len(events),
            'source': 'rommelmarkten.be',
            'filters': filters_applied
        },
        'events': events
    }

    # Write to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

    logger.info(f"Exported {len(events)} filtered events to {filepath}")
    return str(filepath)
