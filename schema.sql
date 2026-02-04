-- Database schema for rommelmarkten.be scraper
-- Stores flea market event data from Flemish provinces

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
    types TEXT,              -- JSON array: ["Binnenrommelmarkt", "Brocante"]
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

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_events_datum ON events(datum);
CREATE INDEX IF NOT EXISTS idx_events_gemeente ON events(gemeente);
CREATE INDEX IF NOT EXISTS idx_events_postcode ON events(postcode);

-- Track scraping history for debugging and auditing
CREATE TABLE IF NOT EXISTS scrape_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT,  -- 'success', 'error', 'skipped'
    error_message TEXT
);
