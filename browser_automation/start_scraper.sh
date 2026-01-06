#!/bin/bash

cd /home/erl/AI1/DURGA_AUTOMATION/browser_automation

# Activate virtual environment
source venv/bin/activate

# Install playwright chromium if not installed
echo "Checking Playwright installation..."
playwright install chromium --quiet 2>/dev/null || echo "Playwright already installed"

# Start service
echo "Starting DURGA Company List Scraper on port 3006..."
python3 company_list_scraper.py
