#!/usr/bin/env python3
"""
Durga Session Manager
=====================
Manages persistent browser sessions for Email, WhatsApp, etc.
Reports status back to Durga Home.

Run: python3 session_manager.py
API: http://localhost:3005
"""
import asyncio
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from playwright.async_api import async_playwright

PORT = 3005
SESSIONS = {}  # Active sessions: {"email": {...}, "whatsapp": {...}}

# Credentials
EMAIL = "evolverobotlab@gmail.com"
PASSWORD = "katacity"

URLS = {
    "home": "http://localhost:8080",
    "email": "http://localhost:5002",
    "whatsapp": "http://localhost:3004"
}

class SessionState:
    def __init__(self, name):
        self.name = name
        self.status = "stopped"  # stopped, starting, active, busy
        self.current_view = None  # inbox, email_detail, compose, etc.
        self.data = {}  # emails list, current email, etc.
        self.browser = None
        self.page = None
        self.last_action = None

    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status,
            "current_view": self.current_view,
            "data": self.data,
            "last_action": self.last_action
        }

# ============================================
# EMAIL SESSION
# ============================================
async def start_email_session():
    """Launch email browser session."""
    session = SESSIONS.get("email") or SessionState("email")
    SESSIONS["email"] = session
    session.status = "starting"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--start-maximized'])
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        session.browser = browser
        session.page = page

        try:
            # Login to dashboard first
            await page.goto(URLS["home"])
            await page.wait_for_load_state('networkidle')

            logged_in = await page.locator('text=evolve robot lab').count() > 0
            if not logged_in:
                session.status = "logging_in"
                login_btn = page.locator('text=LOGIN').first
                await login_btn.click()
                await asyncio.sleep(0.5)
                await page.wait_for_selector('text=Already have an account')
                await page.click('a:has-text("Log In"), span:has-text("Log In")')
                await page.wait_for_selector('#login-email', state='visible')
                await page.fill('#login-email', EMAIL)
                await page.fill('#login-password', PASSWORD)
                await page.locator('button:has-text("Log In")').first.click()
                await asyncio.sleep(1)
                modal = page.locator('#auth-modal.active')
                if await modal.count() > 0:
                    await page.keyboard.press('Escape')

            # Go to email
            await page.goto(URLS["email"])
            await asyncio.sleep(1)

            # Click inbox
            inbox_tab = page.locator('text=Inbox').first
            if await inbox_tab.count() > 0:
                await inbox_tab.click()

            session.status = "active"
            session.current_view = "inbox"
            session.last_action = "opened_inbox"

            # Load emails
            await load_emails(session, page)

            # Keep alive
            while session.status != "stopped":
                await asyncio.sleep(1)

        except Exception as e:
            session.status = "error"
            session.data["error"] = str(e)
        finally:
            await browser.close()
            session.status = "stopped"

async def load_emails(session, page):
    """Load email list into session."""
    # Refresh if needed
    existing = await page.locator('tbody tr').count()
    if existing <= 1:
        refresh_btn = page.locator('button:has-text("Refresh Inbox")').first
        if await refresh_btn.count() > 0:
            await refresh_btn.click()
            session.status = "loading"
            for _ in range(40):
                if await page.locator('button:has-text("Loading")').count() == 0:
                    break
                await asyncio.sleep(0.5)

    # Extract emails
    rows = page.locator('tbody tr')
    count = await rows.count()
    emails = []

    for i in range(min(count, 20)):
        try:
            row = rows.nth(i)
            cells = row.locator('td')
            if await cells.count() >= 4:
                sender = (await cells.nth(1).text_content() or "").strip()
                subject = (await cells.nth(2).text_content() or "").strip()
                preview = (await cells.nth(3).text_content() or "").strip()[:80]
                emails.append({
                    "index": i + 1,
                    "from": sender,
                    "subject": subject,
                    "preview": preview
                })
        except:
            continue

    session.data["emails"] = emails
    session.data["count"] = len(emails)
    session.status = "active"
    session.current_view = "inbox"

async def email_action(action, params=None):
    """Execute action in email session."""
    session = SESSIONS.get("email")
    if not session or session.status != "active":
        return {"error": "Email session not active"}

    page = session.page
    params = params or {}

    if action == "view":
        email_num = params.get("num", 1)
        view_buttons = page.locator('button:has-text("View")')
        if await view_buttons.count() >= email_num:
            await view_buttons.nth(email_num - 1).click()
            session.current_view = "email_detail"
            session.data["viewing"] = email_num
            return {"success": True, "viewing": email_num}

    elif action == "back":
        close_btn = page.locator('button:has-text("Close"), .modal-close')
        if await close_btn.count() > 0:
            await close_btn.first.click()
        session.current_view = "inbox"
        return {"success": True, "view": "inbox"}

    elif action == "refresh":
        await load_emails(session, page)
        return {"success": True, "count": session.data.get("count", 0)}

    return {"error": f"Unknown action: {action}"}

# ============================================
# HTTP API
# ============================================
class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            # Return all session states
            status = {name: s.to_dict() for name, s in SESSIONS.items()}
            self.send_json({"sessions": status})

        elif self.path == "/email/status":
            session = SESSIONS.get("email")
            self.send_json(session.to_dict() if session else {"status": "stopped"})

        elif self.path == "/email/emails":
            session = SESSIONS.get("email")
            if session:
                self.send_json({"emails": session.data.get("emails", [])})
            else:
                self.send_json({"emails": []})

        else:
            self.send_json({"error": "Unknown endpoint"})

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(body) if body else {}

        if self.path == "/email/start":
            if "email" not in SESSIONS or SESSIONS["email"].status == "stopped":
                Thread(target=lambda: asyncio.run(start_email_session()), daemon=True).start()
                self.send_json({"success": True, "message": "Email session starting..."})
            else:
                self.send_json({"success": True, "message": "Email session already running"})

        elif self.path == "/email/action":
            action = data.get("action")
            params = data.get("params", {})
            result = asyncio.run(email_action(action, params))
            self.send_json(result)

        elif self.path == "/email/stop":
            session = SESSIONS.get("email")
            if session:
                session.status = "stopped"
            self.send_json({"success": True})

        else:
            self.send_json({"error": "Unknown endpoint"})

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logs

def run_server():
    server = HTTPServer(('localhost', PORT), APIHandler)
    print(f"Session Manager running at http://localhost:{PORT}")
    print("\nEndpoints:")
    print("  GET  /status         - All session states")
    print("  GET  /email/status   - Email session state")
    print("  GET  /email/emails   - Email list")
    print("  POST /email/start    - Start email session")
    print("  POST /email/action   - Execute action (view, back, refresh)")
    print("  POST /email/stop     - Stop email session")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
