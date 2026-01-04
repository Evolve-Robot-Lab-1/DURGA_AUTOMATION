#!/usr/bin/env python3
"""
Gmail Inbox Automation v2.0 - Stateful Session
===============================================
Opens inbox, lists emails, keeps session alive for follow-up actions.

Usage:
    python3 open_gmail_inbox.py list                     # List emails (keeps browser open)
    python3 open_gmail_inbox.py view 3                   # View email #3
    python3 open_gmail_inbox.py reply 4 job_application  # Reply to email #4
    python3 open_gmail_inbox.py close                    # Close browser session

Author: Evolve Robot Lab
"""
import asyncio
import sys
import json
import os
from playwright.async_api import async_playwright

VERSION = "2.0.0"
STATE_FILE = "/tmp/durga_inbox_state.json"
USER_DATA_DIR = "/tmp/durga_browser_session"

# Credentials
EMAIL = "evolverobotlab@gmail.com"
PASSWORD = "katacity"
DASHBOARD_URL = "http://localhost:8080"
GMAIL_WORKSPACE_URL = "http://localhost:5002"

# Professional Reply Templates
REPLY_TEMPLATES = {
    "job_application": """Dear {applicant_name},

Thank you for expressing your interest in the {position} position at Evolve Robot Lab.

We appreciate you reaching out to us. To proceed with your application, please share your updated resume/CV along with any relevant projects or portfolio that demonstrates your experience with AI/ML technologies.

We will review your application and get back to you regarding the next steps in our selection process.

Best regards,
Evolve Robot Lab Team""",

    "job_acknowledgment": """Dear {applicant_name},

Thank you for your interest in the {position} at Evolve Robot Lab.

We have received your application and our team will review it shortly. If your profile matches our requirements, we will contact you for the next steps in the interview process.

We appreciate your patience during this process.

Best regards,
Evolve Robot Lab Team""",

    "interview_invite": """Dear {applicant_name},

Thank you for your application for the {position} at Evolve Robot Lab.

We are pleased to inform you that your profile has been shortlisted. We would like to invite you for an interview to discuss your background and how you can contribute to our team.

Please let us know your availability for the coming week, and we will schedule a convenient time.

Best regards,
Evolve Robot Lab Team""",

    "general_response": """Dear {sender_name},

Thank you for your email.

We have received your message and will respond to your inquiry shortly.

Best regards,
Evolve Robot Lab Team""",

    "internship_completion": """Dear {applicant_name},

Thank you for submitting your internship completion report.

We have received your final report and appreciate the effort you put into documenting your work during the internship at Evolve Robot Lab. Your contributions to our projects have been valuable.

We will review the report and provide feedback if needed. We wish you all the best in your future endeavors, and hope the experience gained here will be helpful in your career.

Please feel free to stay in touch, and we would be happy to provide a reference if required.

Best regards,
Evolve Robot Lab Team"""
}

def get_professional_reply(template_name, **kwargs):
    template = REPLY_TEMPLATES.get(template_name, REPLY_TEMPLATES["general_response"])
    return template.format(
        applicant_name=kwargs.get("applicant_name", "Applicant"),
        sender_name=kwargs.get("sender_name", "Sir/Madam"),
        position=kwargs.get("position", "the position")
    )

def save_state(emails, session_active=True):
    """Save email list and session state."""
    state = {
        "emails": emails,
        "session_active": session_active,
        "timestamp": str(asyncio.get_event_loop().time()) if asyncio.get_event_loop().is_running() else "0"
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def load_state():
    """Load saved state."""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {"emails": [], "session_active": False}

def output_for_durga(emails):
    """Format email list for Durga dashboard display."""
    result = {
        "success": True,
        "action": "inbox_list",
        "count": len(emails),
        "emails": emails,
        "message": f"Found {len(emails)} emails in inbox",
        "session": "active",
        "next_actions": [
            "view [number] - View specific email",
            "reply [number] [template] - Reply to email",
            "close - Close browser session"
        ]
    }
    print(json.dumps(result, indent=2))
    return result

async def list_inbox():
    """Open inbox and list all emails. Keep browser session alive."""
    emails = []

    async with async_playwright() as p:
        # Launch with persistent context to keep session
        browser = await p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            args=['--start-maximized', '--ozone-platform=x11'],
            no_viewport=True
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        try:
            # Navigate to dashboard
            await page.goto(DASHBOARD_URL)
            await page.wait_for_load_state('networkidle')

            # Check if logged in
            logged_in = await page.locator('text=evolve robot lab').count() > 0

            if not logged_in:
                print("Logging in...", file=sys.stderr)
                login_btn = page.locator('text=LOGIN').first
                await login_btn.click()
                await asyncio.sleep(0.5)

                await page.wait_for_selector('text=Already have an account')
                await page.click('a:has-text("Log In"), span:has-text("Log In")')
                await page.wait_for_selector('#login-email', state='visible', timeout=10000)

                await page.fill('#login-email', EMAIL)
                await page.fill('#login-password', PASSWORD)
                await page.locator('button:has-text("Log In")').first.click()
                await asyncio.sleep(1)

                modal = page.locator('#auth-modal.active')
                if await modal.count() > 0:
                    await page.keyboard.press('Escape')

            # Navigate to Gmail
            await page.goto(GMAIL_WORKSPACE_URL)
            await asyncio.sleep(1)

            # Click Inbox tab
            inbox_tab = page.locator('text=Inbox').first
            if await inbox_tab.count() > 0:
                await inbox_tab.click()
                await asyncio.sleep(0.5)

            # Check if refresh needed
            existing = await page.locator('tbody tr').count()
            if existing <= 1:
                refresh_btn = page.locator('button:has-text("Refresh Inbox")').first
                if await refresh_btn.count() > 0:
                    await refresh_btn.click()
                    print("Loading emails...", file=sys.stderr)
                    for i in range(40):
                        if await page.locator('button:has-text("Loading")').count() == 0:
                            break
                        await asyncio.sleep(0.5)

            await asyncio.sleep(0.5)

            # Extract email list
            rows = page.locator('tbody tr')
            count = await rows.count()

            for i in range(min(count, 20)):  # Max 20 emails
                try:
                    row = rows.nth(i)
                    cells = row.locator('td')
                    if await cells.count() >= 4:
                        sender = (await cells.nth(1).text_content() or "").strip()
                        subject = (await cells.nth(2).text_content() or "").strip()
                        preview = (await cells.nth(3).text_content() or "").strip()[:100]

                        emails.append({
                            "index": i + 1,
                            "from": sender,
                            "subject": subject,
                            "preview": preview
                        })
                except:
                    continue

            # Save state and output
            save_state(emails, session_active=True)
            output_for_durga(emails)

            # Take screenshot for browser control
            screenshot_path = '/tmp/durga_screenshot.png'
            await page.screenshot(path=screenshot_path)
            print(f"[Screenshot] Saved to {screenshot_path}", file=sys.stderr)

            # Keep browser open - wait for user
            print("\n[Session Active] Browser staying open. Use 'view N' or 'reply N' commands.", file=sys.stderr)
            print("Press Ctrl+C to close session.", file=sys.stderr)

            # Keep alive and update screenshot periodically
            while True:
                await asyncio.sleep(10)
                try:
                    await page.screenshot(path=screenshot_path)
                except:
                    pass

        except KeyboardInterrupt:
            print("\nClosing session...", file=sys.stderr)
            save_state(emails, session_active=False)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
        finally:
            await browser.close()

async def view_email(email_index):
    """View specific email in existing or new session."""
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            args=['--start-maximized', '--ozone-platform=x11'],
            no_viewport=True
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        try:
            # Check if already on inbox
            if "5002" not in page.url:
                await page.goto(GMAIL_WORKSPACE_URL)
                await asyncio.sleep(1)

            # Click view button
            view_buttons = page.locator('button:has-text("View")')
            count = await view_buttons.count()

            if email_index > count:
                print(json.dumps({"success": False, "error": f"Email #{email_index} not found. Only {count} emails."}))
                return

            await view_buttons.nth(email_index - 1).click()
            await asyncio.sleep(1)

            # Extract email details
            subject = await page.locator('#view-email-subject, .modal h2, .modal h3').first.text_content() or "Unknown"
            sender = await page.locator('#view-email-from').first.text_content() if await page.locator('#view-email-from').count() > 0 else "Unknown"
            body = await page.locator('#view-email-body, .modal .email-body, .modal p').first.text_content() if await page.locator('#view-email-body').count() > 0 else ""

            result = {
                "success": True,
                "action": "view_email",
                "email": {
                    "index": email_index,
                    "subject": subject.strip()[:200],
                    "from": sender.strip(),
                    "body": body.strip()[:500] if body else ""
                },
                "next_actions": ["reply [template]", "close modal", "back to list"]
            }
            print(json.dumps(result, indent=2))

            # Take screenshot
            await page.screenshot(path='/tmp/durga_screenshot.png')

            # Keep open and update screenshot
            while True:
                await asyncio.sleep(10)
                try:
                    await page.screenshot(path='/tmp/durga_screenshot.png')
                except:
                    pass

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}))
        finally:
            await browser.close()

async def reply_email(email_index, template=None):
    """Reply to specific email."""
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            args=['--start-maximized', '--ozone-platform=x11'],
            no_viewport=True
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()

        try:
            if "5002" not in page.url:
                await page.goto(GMAIL_WORKSPACE_URL)
                await asyncio.sleep(1)

            # Click view first
            view_buttons = page.locator('button:has-text("View")')
            await view_buttons.nth(email_index - 1).click()
            await asyncio.sleep(1)

            # Get sender name for template
            state = load_state()
            emails = state.get("emails", [])
            sender_name = "Applicant"
            subject = "the position"

            if email_index <= len(emails):
                email = emails[email_index - 1]
                sender_name = email.get("from", "Applicant").split("<")[0].strip()
                subject = email.get("subject", "the position")

            # Click reply
            reply_btn = page.locator('#toggle-reply-btn, button:has-text("Reply")').first
            if await reply_btn.count() > 0:
                await reply_btn.click()
                await asyncio.sleep(0.5)

                # Fill with template or use AI
                if template:
                    reply_text = get_professional_reply(template, applicant_name=sender_name, position=subject)
                    textarea = page.locator('#quick-reply-text, textarea').first
                    if await textarea.count() > 0:
                        await textarea.fill(reply_text)
                else:
                    # Use AI suggestions
                    gen_btn = page.locator('button:has-text("Generate")').first
                    if await gen_btn.count() > 0:
                        await gen_btn.click()
                        for _ in range(15):
                            sug = page.locator('#suggestions-container > div').first
                            if await sug.count() > 0:
                                await sug.click()
                                break
                            await asyncio.sleep(0.5)

                # Send
                await asyncio.sleep(0.3)
                send_btn = page.locator('#send-quick-reply-btn, button:has-text("Send")').first
                if await send_btn.count() > 0:
                    await send_btn.click()
                    await asyncio.sleep(1)
                    print(json.dumps({
                        "success": True,
                        "action": "reply_sent",
                        "to": sender_name,
                        "template": template or "ai_generated"
                    }))

            while True:
                await asyncio.sleep(60)

        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}))
        finally:
            await browser.close()

async def close_session():
    """Close browser session."""
    import shutil
    try:
        if os.path.exists(USER_DATA_DIR):
            shutil.rmtree(USER_DATA_DIR)
        if os.path.exists(STATE_FILE):
            os.remove(STATE_FILE)
        print(json.dumps({"success": True, "action": "session_closed"}))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        print(f"""
Gmail Inbox Automation v{VERSION}
================================
Usage:
    python3 open_gmail_inbox.py list                     # List emails
    python3 open_gmail_inbox.py view 3                   # View email #3
    python3 open_gmail_inbox.py reply 4 job_application  # Reply with template
    python3 open_gmail_inbox.py close                    # Close session

Templates: job_application, job_acknowledgment, interview_invite, general_response
""")
        sys.exit(0)

    action = sys.argv[1].lower()

    if action == "list":
        asyncio.run(list_inbox())
    elif action == "view":
        num = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        asyncio.run(view_email(num))
    elif action == "reply":
        num = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        tpl = sys.argv[3] if len(sys.argv) > 3 else None
        asyncio.run(reply_email(num, tpl))
    elif action == "close":
        asyncio.run(close_session())
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
