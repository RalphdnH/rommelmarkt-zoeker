"""Pydantic model for rommelmarkt event data."""

from datetime import date, time
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field


class Event(BaseModel):
    """Represents a single rommelmarkt (flea market) event."""

    id: int
    naam: str
    gemeente: Optional[str] = None
    postcode: Optional[str] = None
    adres: Optional[str] = None
    locatie_naam: Optional[str] = None
    datum: Optional[date] = None
    start_tijd: Optional[str] = None  # Stored as string "HH:MM"
    eind_tijd: Optional[str] = None   # Stored as string "HH:MM"
    types: List[str] = Field(default_factory=list)
    inkom_prijs: Optional[Decimal] = None
    standplaats_prijs: Optional[Decimal] = None
    organisator: Optional[str] = None
    telefoon: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    beschrijving: Optional[str] = None
    afbeelding_url: Optional[str] = None
    source_url: str

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            date: lambda v: v.isoformat() if v else None,
            time: lambda v: v.strftime('%H:%M') if v else None,
            Decimal: lambda v: float(v) if v else None,
        }

    def to_db_tuple(self) -> tuple:
        """Convert event to tuple for database insertion."""
        import json

        return (
            self.id,
            self.naam,
            self.gemeente,
            self.postcode,
            self.adres,
            self.locatie_naam,
            self.datum.isoformat() if self.datum else None,
            self.start_tijd,
            self.eind_tijd,
            json.dumps(self.types) if self.types else '[]',
            float(self.inkom_prijs) if self.inkom_prijs is not None else None,
            float(self.standplaats_prijs) if self.standplaats_prijs is not None else None,
            self.organisator,
            self.telefoon,
            self.email,
            self.website,
            self.beschrijving,
            self.afbeelding_url,
            self.source_url,
        )
