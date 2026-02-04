@echo off
REM Rommelmarkt Scraper - Scheduled Task Script
REM Run this script daily to keep the database updated

cd /d C:\Projects\rommelmarkt-zoeker

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Run the scraper with JSON export
python main.py --export-json

REM Log completion
echo [%date% %time%] Scraper completed >> logs\scheduled_runs.log
