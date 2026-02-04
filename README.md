# Rommelmarkt Zoeker

Een Python web scraper voor rommelmarkten.be die rommelmarkt-informatie verzamelt uit Vlaamse provincies en opslaat in een SQLite database.

## Features

- Scrapet rommelmarkt listings van alle Vlaamse provincies
- Respectvolle scraping met rate limiting (2.5 seconden tussen requests)
- Incrementele updates (slaat bestaande events over)
- SQLite database opslag
- JSON export functionaliteit
- Configureerbaar via YAML bestand
- Cloudflare email-bescherming decoder

## Installatie

### Vereisten

- Python 3.8 of hoger
- pip (Python package manager)

### Stappen

1. Clone of download dit project

2. Maak een virtual environment aan (aanbevolen):
   ```bash
   python -m venv venv

   # Windows:
   venv\Scripts\activate

   # Linux/Mac:
   source venv/bin/activate
   ```

3. Installeer dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Gebruik

### Basis gebruik

```bash
# Standaard: scrape huidige maand + volgende 3 maanden (incrementeel)
python main.py

# Forceer volledige refresh (alle events opnieuw scrapen)
python main.py --full-refresh

# Exporteer naar JSON na het scrapen
python main.py --export-json

# Gebruik een ander configuratiebestand
python main.py --config my_config.yaml

# Dry run: toon wat er gescrapet zou worden zonder daadwerkelijk te scrapen
python main.py --dry-run
```

### Command-line opties

| Optie | Kort | Beschrijving |
|-------|------|--------------|
| `--config` | `-c` | Pad naar configuratiebestand (standaard: config.yaml) |
| `--full-refresh` | `-f` | Forceer volledige refresh, alle events opnieuw scrapen |
| `--export-json` | `-e` | Exporteer database naar JSON na het scrapen |
| `--dry-run` | `-n` | Toon wat er zou gebeuren zonder daadwerkelijk te scrapen |

## Configuratie

Pas `config.yaml` aan om het gedrag van de scraper te wijzigen:

```yaml
scraping:
  delay_seconds: 2.5          # Vertraging tussen requests
  max_retries: 3              # Aantal retry pogingen bij fouten
  user_agent: "RommelmarktZoeker/1.0"

target:
  base_url: "https://www.rommelmarkten.be"
  provinces:                   # Provincies om te scrapen
    - antwerpen
    - limburg
    - oost-vlaanderen
    - vlaams-brabant
    - west-vlaanderen
  month_selection: "next_3"    # "current", "next_3", "next_6", "all"

storage:
  database_path: "data/rommelmarkten.db"
  json_export_path: "data/exports"

logging:
  level: "INFO"                # DEBUG, INFO, WARNING, ERROR
  file: "logs/scraper.log"
```

### Maand selectie opties

| Optie | Beschrijving |
|-------|--------------|
| `current` | Alleen de huidige maand |
| `next_3` | Huidige maand + volgende 3 maanden |
| `next_6` | Huidige maand + volgende 6 maanden |
| `all` | Alle 12 maanden |

Of specificeer een expliciete lijst:
```yaml
target:
  months:
    - januari
    - februari
    - maart
```

## Database Schema

De scraper slaat data op in SQLite met de volgende structuur:

| Veld | Type | Beschrijving |
|------|------|--------------|
| `id` | INTEGER | Unieke event ID (van rommelmarkten.be) |
| `naam` | TEXT | Naam van het evenement |
| `gemeente` | TEXT | Gemeente naam |
| `postcode` | TEXT | Postcode |
| `adres` | TEXT | Straat en huisnummer |
| `locatie_naam` | TEXT | Naam van de locatie/zaal |
| `datum` | DATE | Datum van het evenement |
| `start_tijd` | TEXT | Starttijd (HH:MM) |
| `eind_tijd` | TEXT | Eindtijd (HH:MM) |
| `types` | TEXT | JSON array met event types |
| `inkom_prijs` | REAL | Toegangsprijs in EUR |
| `standplaats_prijs` | REAL | Prijs per standplaats in EUR |
| `organisator` | TEXT | Naam van de organisator |
| `telefoon` | TEXT | Telefoonnummer |
| `email` | TEXT | E-mailadres |
| `website` | TEXT | Website URL |
| `beschrijving` | TEXT | Volledige beschrijving |
| `afbeelding_url` | TEXT | URL naar affiche/foto |
| `source_url` | TEXT | Originele URL op rommelmarkten.be |
| `first_scraped_at` | TIMESTAMP | Wanneer eerst toegevoegd |
| `last_updated_at` | TIMESTAMP | Laatste update |

### Database queries voorbeelden

```bash
# Open de database
sqlite3 data/rommelmarkten.db

# Bekijk alle events
SELECT id, naam, gemeente, datum FROM events ORDER BY datum;

# Events in een specifieke gemeente
SELECT * FROM events WHERE gemeente LIKE '%Gent%';

# Events van deze maand
SELECT * FROM events WHERE datum >= date('now', 'start of month');

# Tel events per provincie
SELECT gemeente, COUNT(*) FROM events GROUP BY gemeente;
```

## Project Structuur

```
rommelmarkt-zoeker/
├── main.py                     # CLI entry point
├── config.yaml                 # Configuratie
├── schema.sql                  # Database schema
├── requirements.txt            # Python dependencies
├── README.md                   # Deze documentatie
├── src/
│   ├── __init__.py
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── base.py             # Base scraper met rate limiting
│   │   ├── listing_scraper.py  # Scraper voor lijstpagina's
│   │   ├── detail_scraper.py   # Scraper voor detailpagina's
│   │   └── email_decoder.py    # Cloudflare email decoder
│   ├── models/
│   │   ├── __init__.py
│   │   └── event.py            # Pydantic Event model
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py         # SQLite operaties
│   │   └── json_export.py      # JSON export
│   └── utils/
│       ├── __init__.py
│       ├── config.py           # Config loader
│       └── logging_setup.py    # Logging configuratie
├── data/
│   ├── rommelmarkten.db        # SQLite database (gegenereerd)
│   └── exports/                # JSON exports
└── logs/
    └── scraper.log             # Log bestanden
```

## Juridisch / Ethisch

Deze scraper is ontworpen om respectvol om te gaan met de bron website:

- **robots.txt**: De scraper respecteert de robots.txt van rommelmarkten.be
- **Rate limiting**: Minimaal 2.5 seconden tussen requests
- **User-Agent**: Identificeert zichzelf duidelijk
- **Geen geblokkeerde paden**: Scrapet alleen publiek toegankelijke content

### robots.txt van rommelmarkten.be

De site blokkeert alleen:
- `/admin/` - Administratie
- `/account/` - Gebruikersaccounts
- `/info/*` - Info pagina's
- `/a/` - Advertenties

Alle publieke rommelmarkt listings zijn toegestaan.

## Troubleshooting

### Veelvoorkomende problemen

**Fout: "Configuration file not found"**
- Zorg dat `config.yaml` bestaat in de project root

**Fout: "Connection refused" of timeout**
- Check je internetverbinding
- De website kan tijdelijk onbereikbaar zijn
- Verhoog `timeout_seconds` in config

**Lege database na scrapen**
- Check de logs in `logs/scraper.log`
- Probeer met `--full-refresh` optie
- Verifieer dat de website structuur niet gewijzigd is

**Email adressen worden niet geëxtraheerd**
- Emails zijn versleuteld met Cloudflare bescherming
- De decoder probeert dit automatisch te ontcijferen

### Debug mode

Zet logging level op DEBUG voor meer informatie:

```yaml
logging:
  level: "DEBUG"
```

## Licentie

Dit project is bedoeld voor educatieve doeleinden. Gebruik op eigen verantwoordelijkheid en respecteer de terms of service van rommelmarkten.be.
