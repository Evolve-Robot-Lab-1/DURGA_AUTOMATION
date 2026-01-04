#!/usr/bin/env python3
"""
Browser-Use Login Test for DURGA Dashboard
Uses AI-powered browser automation for reliable form interaction
"""
import asyncio
import os
from browser_use import Agent
from langchain_anthropic import ChatAnthropic

# Credentials (from SESSION_SUMMARY_2025-12-25.md)
EMAIL = "evolverobotlab@gmail.com"
PASSWORD = "katacity"
DASHBOARD_URL = "http://localhost:8080"

async def login_to_dashboard():
    """Use browser-use Agent to login to DURGA Dashboard"""

    # Use Claude as the LLM (API key from environment)
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    agent = Agent(
        task=f"""
        Go to {DASHBOARD_URL} and login with these credentials:
        - Email: {EMAIL}
        - Password: {PASSWORD}

        Steps:
        1. Click the LOGIN button in the navigation
        2. Click "Already have an account? Log In" to switch to login form
        3. Enter the email and password
        4. Submit the login form
        5. Wait for dashboard to load
        6. Take a screenshot of the logged-in dashboard
        """,
        llm=llm,
    )

    result = await agent.run()
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    asyncio.run(login_to_dashboard())
