#!/bin/bash
# Browser-Use Setup for DURGA Platform Testing

echo "Setting up browser-use environment..."

# Create virtual environment with Python 3.11
python3.11 -m venv /home/evolve/AI\ PROJECT/browser_automation/venv

# Activate and install
source /home/evolve/AI\ PROJECT/browser_automation/venv/bin/activate

# Install browser-use and dependencies
pip install browser-use playwright langchain-anthropic

# Install Playwright browsers
playwright install chromium

echo "Setup complete!"
echo "Activate with: source '/home/evolve/AI PROJECT/browser_automation/venv/bin/activate'"
