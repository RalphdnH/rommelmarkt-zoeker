"""SQLite database operations for rommelmarkt data."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from ..models.event import Event


class Database:
    """SQLite database handler for rommelmarkt events."""

    def __init__(self, db_path: str, schema_path: str = "schema.sql"):
        """
        Initialize database connection and schema.

        Args:
            db_path: Path to the SQLite database file.
            schema_path: Path to the SQL schema file.
        """
        self.db_path = Path(db_path)
        self.schema_path = Path(schema_path)
        self.logger = logging.getLogger(self.__class__.__name__)

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema
        self._init_schema()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Initialize database schema from SQL file."""
        if self.schema_path.exists():
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
        else:
            # Inline schema as fallback
            schema_sql = """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY,
                    naam TEXT NOT NULL,
                    gemeente TEXT,
                    postcode TEXT,
                    adres TEXT,
                    locatie_naam TEXT,
                    datum DATE,
                    start_tijd TEXT,
                    eind_tijd TEXT,
                    types TEXT,
                    inkom_prijs REAL,
                    standplaats_prijs REAL,
                    organisator TEXT,
                    telefoon TEXT,
                    email TEXT,
                    website TEXT,
                    beschrijving TEXT,
                    afbeelding_url TEXT,
                    source_url TEXT,
                    first_scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_events_datum ON events(datum);
                CREATE INDEX IF NOT EXISTS idx_events_gemeente ON events(gemeente);
                CREATE INDEX IF NOT EXISTS idx_events_postcode ON events(postcode);
            """

        with self._get_connection() as conn:
            conn.executescript(schema_sql)
            conn.commit()
            self.logger.debug("Database schema initialized")

    def event_exists(self, event_id: int) -> bool:
        """
        Check if event already exists in database.

        Args:
            event_id: The event ID to check.

        Returns:
            True if event exists, False otherwise.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM events WHERE id = ?",
                (event_id,)
            )
            return cursor.fetchone() is not None

    def get_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single event by ID.

        Args:
            event_id: The event ID to retrieve.

        Returns:
            Event as dictionary, or None if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM events WHERE id = ?",
                (event_id,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_dict(row)
            return None

    def upsert_event(self, event: Event) -> None:
        """
        Insert or update an event.

        Args:
            event: Event object to save.
        """
        with self._get_connection() as conn:
            # Check if exists for proper timestamp handling
            exists = self.event_exists(event.id)

            if exists:
                # Update existing record
                conn.execute("""
                    UPDATE events SET
                        naam = ?,
                        gemeente = ?,
                        postcode = ?,
                        adres = ?,
                        locatie_naam = ?,
                        datum = ?,
                        start_tijd = ?,
                        eind_tijd = ?,
                        types = ?,
                        inkom_prijs = ?,
                        standplaats_prijs = ?,
                        organisator = ?,
                        telefoon = ?,
                        email = ?,
                        website = ?,
                        beschrijving = ?,
                        afbeelding_url = ?,
                        source_url = ?,
                        last_updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    event.naam,
                    event.gemeente,
                    event.postcode,
                    event.adres,
                    event.locatie_naam,
                    event.datum.isoformat() if event.datum else None,
                    event.start_tijd,
                    event.eind_tijd,
                    json.dumps(event.types) if event.types else '[]',
                    float(event.inkom_prijs) if event.inkom_prijs is not None else None,
                    float(event.standplaats_prijs) if event.standplaats_prijs is not None else None,
                    event.organisator,
                    event.telefoon,
                    event.email,
                    event.website,
                    event.beschrijving,
                    event.afbeelding_url,
                    event.source_url,
                    event.id
                ))
                self.logger.debug(f"Updated event {event.id}: {event.naam}")
            else:
                # Insert new record
                conn.execute("""
                    INSERT INTO events (
                        id, naam, gemeente, postcode, adres, locatie_naam,
                        datum, start_tijd, eind_tijd, types,
                        inkom_prijs, standplaats_prijs,
                        organisator, telefoon, email, website,
                        beschrijving, afbeelding_url, source_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, event.to_db_tuple())
                self.logger.debug(f"Inserted event {event.id}: {event.naam}")

            conn.commit()

    def get_all_events(self) -> List[Dict[str, Any]]:
        """
        Retrieve all events as dictionaries.

        Returns:
            List of events as dictionaries.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM events ORDER BY datum"
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_events_by_gemeente(self, gemeente: str) -> List[Dict[str, Any]]:
        """
        Get events filtered by municipality.

        Args:
            gemeente: Municipality name to filter by.

        Returns:
            List of matching events.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM events WHERE gemeente LIKE ? ORDER BY datum",
                (f"%{gemeente}%",)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_events_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Get events within a date range.

        Args:
            start_date: Start date in ISO format (YYYY-MM-DD).
            end_date: End date in ISO format (YYYY-MM-DD).

        Returns:
            List of matching events.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM events WHERE datum BETWEEN ? AND ? ORDER BY datum",
                (start_date, end_date)
            )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_event_count(self) -> int:
        """Get total number of events in database."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM events")
            return cursor.fetchone()[0]

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite Row to dictionary with JSON parsing."""
        d = dict(row)
        # Parse JSON fields
        if d.get('types'):
            try:
                d['types'] = json.loads(d['types'])
            except json.JSONDecodeError:
                d['types'] = []
        return d
