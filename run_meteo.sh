#!/bin/bash
cd "$(dirname "$0")"

echo "=== Esecuzione Meteo Cusago ==="
python3 ilmeteo_scraper.py cusago
