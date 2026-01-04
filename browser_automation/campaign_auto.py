#!/usr/bin/env python3
"""
DurgaMail Campaign Automation
Browser automation for email campaign management with AI assistance.

Usage:
    python campaign_auto.py create --csv contacts.csv --company "Evolve Robot" --goal partnership
    python campaign_auto.py upload --csv contacts.csv
    python campaign_auto.py generate --company "Evolve Robot" --goal customer_acquisition
    python campaign_auto.py status
    python campaign_auto.py pause
    python campaign_auto.py resume
    python campaign_auto.py cancel
    python campaign_auto.py analytics
"""
import asyncio
import argparse
import os
import subprocess
from playwright.async_api import async_playwright

# Configuration
DURGAMAIL_URL = "http://localhost:5002"
DASHBOARD_URL = "http://localhost:8080"
EMAIL = "evolverobotlab@gmail.com"
PASSWORD = "katacity"

# Campaign input folder
CAMPAIGN_INPUT_DIR = "/home/evolve/AI PROJECT/browser_automation/campaign_input"
CONVERTED_DIR = "/home/evolve/AI PROJECT/browser_automation/campaign_input/converted"

# Campaign goal options
GOALS = {
    "vc_funding": "Seeking VC Funding",
    "ai_robotics_sales": "Selling AI/Robotics Services",
    "partnership": "Partnership Opportunities",
    "customer_acquisition": "Customer Acquisition",
    "product_launch": "Product Launch"
}


def convert_odt_to_docx(odt_path):
    """Convert .odt file to .docx using LibreOffice."""
    if not os.path.exists(odt_path):
        return None

    # Create converted directory
    os.makedirs(CONVERTED_DIR, exist_ok=True)

    # Get output filename
    basename = os.path.splitext(os.path.basename(odt_path))[0]
    docx_path = os.path.join(CONVERTED_DIR, f"{basename}.docx")

    # Check if already converted
    if os.path.exists(docx_path):
        print(f"Using existing converted file: {os.path.basename(docx_path)}")
        return docx_path

    print(f"Converting {os.path.basename(odt_path)} to DOCX...")
    try:
        # Use LibreOffice to convert
        result = subprocess.run([
            'libreoffice', '--headless', '--convert-to', 'docx',
            '--outdir', CONVERTED_DIR, odt_path
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and os.path.exists(docx_path):
            print(f"Converted to: {os.path.basename(docx_path)}")
            return docx_path
        else:
            print(f"Conversion failed: {result.stderr}")
            return None
    except Exception as e:
        print(f"Error converting file: {e}")
        return None


def get_campaign_files():
    """Auto-detect files in campaign_input folder."""
    files = {
        'csv': None,
        'memo_text': None,      # Readable text file (.txt, .md)
        'memo_doc': None,       # Document file for chatbot (.pdf, .docx)
        'attachments': []
    }

    if not os.path.exists(CAMPAIGN_INPUT_DIR):
        print(f"Campaign input folder not found: {CAMPAIGN_INPUT_DIR}")
        return files

    # Scan main folder for CSV and memo files
    for f in os.listdir(CAMPAIGN_INPUT_DIR):
        full_path = os.path.join(CAMPAIGN_INPUT_DIR, f)
        if os.path.isfile(full_path):
            lower_f = f.lower()
            if lower_f.endswith('.csv'):
                files['csv'] = full_path
                print(f"Found CSV: {f}")
            elif lower_f.endswith(('.txt', '.md')):
                files['memo_text'] = full_path
                print(f"Found Memo (text): {f}")
            elif lower_f.endswith(('.pdf', '.docx')):
                # PDF/DOCX - directly usable by chatbot
                files['memo_doc'] = full_path
                print(f"Found Memo (doc): {f}")
            elif lower_f.endswith('.odt'):
                # ODT needs conversion for chatbot
                print(f"Found Memo (odt): {f} - converting to DOCX...")
                converted = convert_odt_to_docx(full_path)
                if converted:
                    files['memo_doc'] = converted

    # Scan attachments subfolder - also check for readable memo files
    attach_dir = os.path.join(CAMPAIGN_INPUT_DIR, 'attachments')
    if os.path.exists(attach_dir):
        for f in os.listdir(attach_dir):
            full_path = os.path.join(attach_dir, f)
            if os.path.isfile(full_path):
                lower_f = f.lower()
                # Check for readable memo in attachments folder
                if lower_f.endswith(('.txt', '.md')) and 'memo' in lower_f:
                    if not files['memo_text']:  # Prefer root-level memo
                        files['memo_text'] = full_path
                        print(f"Found Memo (text from attachments): {f}")
                    else:
                        files['attachments'].append(full_path)
                        print(f"Found Attachment: {f}")
                else:
                    files['attachments'].append(full_path)
                    print(f"Found Attachment: {f}")

    return files


async def upload_attachments(page, attachment_paths):
    """Upload email attachments."""
    if not attachment_paths:
        return

    print(f"\n--- Uploading {len(attachment_paths)} Attachments ---")
    attachment_input = page.locator('#attachment-input')

    if await attachment_input.count() > 0:
        await attachment_input.set_input_files(attachment_paths)
        await asyncio.sleep(2)

        # Verify uploads
        attachment_list = page.locator('#attachment-list .attachment-item, #attachment-list > div')
        count = await attachment_list.count()
        print(f"Attachments uploaded: {count}")
    else:
        print("Attachment input not found!")


async def read_memo_content(memo_path):
    """Read memo file content."""
    if not memo_path or not os.path.exists(memo_path):
        return ""

    try:
        with open(memo_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"Read memo content: {len(content)} chars")
        return content
    except Exception as e:
        print(f"Error reading memo: {e}")
        return ""


# ============================================
# CHATBOT INTERACTION FUNCTIONS
# ============================================

async def open_chatbot(page):
    """Open the AI Assistant chatbot window."""
    print("\n--- Opening AI Chatbot ---")
    chatbot_toggle = page.locator('#chatbot-toggle')

    if await chatbot_toggle.count() > 0:
        await chatbot_toggle.click()
        await asyncio.sleep(0.5)

        # Verify chatbot window is open
        chatbot_window = page.locator('#chatbot-window')
        if await chatbot_window.count() > 0:
            is_visible = await chatbot_window.is_visible()
            if is_visible:
                print("Chatbot opened!")
                return True

    print("Failed to open chatbot!")
    return False


async def upload_document_to_chatbot(page, doc_path):
    """Upload a document via the chatbot's file input."""
    print(f"\n--- Uploading Document to Chatbot ---")
    print(f"File: {os.path.basename(doc_path)}")

    # Click the upload button (paperclip)
    upload_btn = page.locator('#chatbot-upload-btn')
    if await upload_btn.count() > 0:
        # Set the file directly on the hidden input
        doc_input = page.locator('#chatbot-document-input')
        await doc_input.set_input_files(doc_path)
        await asyncio.sleep(3)  # Wait for upload
        print("Document uploaded to chatbot!")
        return True

    print("Chatbot upload button not found!")
    return False


async def send_chatbot_command(page, command):
    """Send a command to the chatbot."""
    print(f"Sending command: {command}")

    chat_input = page.locator('#chatbot-input')
    send_btn = page.locator('#chatbot-send')

    if await chat_input.count() > 0 and await send_btn.count() > 0:
        await chat_input.fill(command)
        await asyncio.sleep(0.3)
        await send_btn.click()
        await asyncio.sleep(1)
        print(f"Command sent: {command}")
        return True

    print("Chatbot input not found!")
    return False


async def wait_for_chatbot_response(page, timeout=30):
    """Wait for chatbot to finish responding."""
    print("Waiting for AI response...")

    for i in range(timeout):
        # Check if typing indicator is gone
        typing = page.locator('#typing-indicator')
        if await typing.count() == 0:
            # Check for action buttons (indicates response with options)
            action_btns = page.locator('.chat-action-btn')
            if await action_btns.count() > 0:
                print(f"Response received with action buttons! ({i+1}s)")
                return True

        if i % 5 == 0 and i > 0:
            print(f"  Still waiting... ({i}s)")
        await asyncio.sleep(1)

    print("Timeout waiting for chatbot response!")
    return False


async def click_update_form_button(page):
    """Click the 'Update Form' action button in chatbot."""
    print("\n--- Clicking Update Form ---")

    # Try multiple selector patterns
    selectors = [
        '.chat-action-btn:has-text("Update Form")',
        '.chat-action-btn:has-text("✓ Update Form")',
        'button:has-text("Update Form")',
    ]

    for selector in selectors:
        btn = page.locator(selector).first
        if await btn.count() > 0:
            await btn.click()
            await asyncio.sleep(1)
            print("Update Form clicked! Form fields updated.")
            return True

    print("Update Form button not found!")
    return False


async def close_chatbot(page):
    """Close the chatbot window."""
    print("\n--- Closing Chatbot ---")

    # Try close button first
    close_btn = page.locator('#chatbot-close')
    if await close_btn.count() > 0:
        await close_btn.click()
        await asyncio.sleep(0.5)
        print("Chatbot closed!")
        return True

    # Try minimize button
    minimize_btn = page.locator('#chatbot-minimize')
    if await minimize_btn.count() > 0:
        await minimize_btn.click()
        await asyncio.sleep(0.5)
        print("Chatbot minimized!")
        return True

    # Try clicking toggle again to close
    toggle = page.locator('#chatbot-toggle')
    if await toggle.count() > 0:
        await toggle.click()
        await asyncio.sleep(0.5)
        print("Chatbot toggled closed!")
        return True

    return False


async def interact_with_chatbot(page, doc_path):
    """Full chatbot interaction: upload doc, parse, update form, close."""
    print("\n" + "=" * 40)
    print("AI CHATBOT DOCUMENT PARSING")
    print("=" * 40)

    # Step 1: Open chatbot
    if not await open_chatbot(page):
        return False

    # Step 2: Upload document
    if not await upload_document_to_chatbot(page, doc_path):
        return False

    # Step 3: Send /parse command
    await asyncio.sleep(2)  # Wait for upload confirmation message
    if not await send_chatbot_command(page, '/parse'):
        return False

    # Step 4: Wait for AI parsing response
    if not await wait_for_chatbot_response(page, timeout=45):
        return False

    # Step 5: Click Update Form button
    if not await click_update_form_button(page):
        return False

    # Step 6: Close chatbot
    await asyncio.sleep(1)
    await close_chatbot(page)

    print("\nChatbot interaction complete!")
    return True


async def login_to_dashboard(page):
    """Login to DurgaAI dashboard if needed."""
    print("Step 1: Navigating to dashboard...")
    await page.goto(DASHBOARD_URL)
    await page.wait_for_load_state('networkidle')
    await asyncio.sleep(2)

    # Check if already logged in
    logged_in = await page.locator('text=evolve robot lab').count() > 0

    if not logged_in:
        print("Step 2: Logging in...")
        login_btn = page.locator('text=LOGIN').first
        await login_btn.click()
        await asyncio.sleep(2)

        # Switch to login form
        await page.wait_for_selector('text=Already have an account')
        await page.click('a:has-text("Log In"), span:has-text("Log In")')
        await asyncio.sleep(1)

        # Fill credentials
        await page.wait_for_selector('#login-email', state='visible', timeout=10000)
        await page.fill('#login-email', EMAIL)
        await asyncio.sleep(0.5)
        await page.fill('#login-password', PASSWORD)
        await asyncio.sleep(0.5)

        # Submit
        submit_btn = page.locator('button:has-text("Log In")').first
        await submit_btn.click()
        await asyncio.sleep(3)

        # Close modal if open
        modal = page.locator('#auth-modal.active')
        if await modal.count() > 0:
            await page.keyboard.press('Escape')
            await asyncio.sleep(1)

        print("Login successful!")
    else:
        print("Already logged in!")


async def navigate_to_campaign(page):
    """Navigate to DurgaMail Campaign section."""
    print("Step 3: Navigating to DurgaMail Campaign...")
    await page.goto(DURGAMAIL_URL)
    await asyncio.sleep(3)

    # Click Campaign tab
    campaign_tab = page.locator('text=Campaign').first
    if await campaign_tab.count() > 0:
        await campaign_tab.click()
        await asyncio.sleep(2)
        print("Campaign section loaded!")
    else:
        print("Campaign tab not found!")


async def upload_recipients(page, csv_path=None, emails=None):
    """Upload recipients from CSV or enter manually."""
    print("\n--- Uploading Recipients ---")

    if csv_path and os.path.exists(csv_path):
        print(f"Uploading CSV: {csv_path}")
        # Find specific CSV file input (not attachment or chatbot inputs)
        file_input = page.locator('#file-input')
        if await file_input.count() > 0:
            await file_input.set_input_files(csv_path)
            await asyncio.sleep(3)
            print("CSV uploaded!")
        else:
            # Try clicking upload area first
            upload_area = page.locator('#csv-upload-area')
            if await upload_area.count() > 0:
                await upload_area.click()
                await asyncio.sleep(1)
                # Handle file dialog via specific file input
                await page.locator('#file-input').set_input_files(csv_path)
                await asyncio.sleep(3)

    elif emails:
        print(f"Entering {len(emails)} emails manually...")
        textarea = page.locator('#recipient-list-textarea')
        if await textarea.count() > 0:
            email_text = "\n".join(emails)
            await textarea.fill(email_text)
            await asyncio.sleep(1)
            print("Emails entered!")

    # Wait for preview
    preview = page.locator('#csv-preview')
    await asyncio.sleep(2)

    # Check recipient count
    rows = page.locator('#csv-preview tr, .recipient-row')
    count = await rows.count()
    print(f"Recipients loaded: {count}")

    # Take screenshot
    await page.screenshot(path='campaign_recipients.png')
    print("Screenshot saved: campaign_recipients.png")


async def continue_to_compose(page):
    """Click continue to move to compose step."""
    continue_btn = page.locator('#continue-to-compose, button:has-text("Continue")')
    if await continue_btn.count() > 0:
        await continue_btn.first.click()
        await asyncio.sleep(2)
        print("Moved to Compose step!")


async def compose_email(page, company="", product="", goal="customer_acquisition", generate_ai=True):
    """Fill compose form and optionally generate AI email."""
    print("\n--- Composing Email ---")

    # Fill company info
    if company:
        company_input = page.locator('#company-info')
        if await company_input.count() > 0:
            await company_input.fill(company)
            print(f"Company: {company}")

    # Fill product info
    if product:
        product_input = page.locator('#product-info')
        if await product_input.count() > 0:
            await product_input.fill(product)
            print(f"Product: {product}")

    # Select campaign goal
    goal_select = page.locator('#campaign-goal-select')
    if await goal_select.count() > 0:
        await goal_select.select_option(goal)
        print(f"Goal: {GOALS.get(goal, goal)}")

    await asyncio.sleep(1)

    # Generate AI email if requested
    if generate_ai:
        print("\nGenerating AI email...")
        generate_btn = page.locator('button:has-text("Generate"), button:has-text("AI")')
        if await generate_btn.count() > 0:
            await generate_btn.first.click()
            await asyncio.sleep(2)

            # Wait for AI generation (up to 30 seconds)
            print("Waiting for AI suggestions...")
            for i in range(30):
                subject = page.locator('#subject-template')
                if await subject.count() > 0:
                    value = await subject.input_value()
                    if value and len(value) > 5:
                        print(f"AI generation complete! ({i+1}s)")
                        break
                if i % 5 == 0:
                    print(f"  Still generating... ({i}s)")
                await asyncio.sleep(1)

    # Read generated content
    subject_elem = page.locator('#subject-template')
    message_elem = page.locator('#message-template')

    if await subject_elem.count() > 0:
        subject = await subject_elem.input_value()
        print(f"\nSubject: {subject[:80]}...")

    if await message_elem.count() > 0:
        message = await message_elem.input_value()
        print(f"Message preview: {message[:100]}...")

    # Take screenshot
    await page.screenshot(path='campaign_compose.png')
    print("Screenshot saved: campaign_compose.png")


async def send_test_email(page):
    """Send a test email."""
    print("\nSending test email...")
    test_btn = page.locator('#test-email-btn, button:has-text("Test")')
    if await test_btn.count() > 0:
        await test_btn.first.click()
        await asyncio.sleep(5)
        print("Test email sent!")


async def launch_campaign(page):
    """Generate emails and launch the campaign."""
    print("\n--- Launching Campaign ---")

    # Step 1: Click "Generate Emails" button first
    generate_emails_btn = page.locator('button:has-text("Generate Emails")')
    if await generate_emails_btn.count() > 0:
        print("Clicking 'Generate Emails' button...")
        await generate_emails_btn.first.scroll_into_view_if_needed()
        await asyncio.sleep(1)
        await generate_emails_btn.first.click()
        await asyncio.sleep(3)
        print("Generating emails for recipients...")

        # Wait for emails to be generated (up to 60 seconds)
        for i in range(60):
            # Check if Start Campaign button is now visible
            start_btn = page.locator('#start-campaign-btn, button:has-text("Start Campaign")')
            if await start_btn.count() > 0:
                try:
                    is_visible = await start_btn.first.is_visible()
                    if is_visible:
                        print(f"Emails generated! ({i+1}s)")
                        break
                except:
                    pass
            if i % 10 == 0:
                print(f"  Still generating emails... ({i}s)")
            await asyncio.sleep(1)

    # Step 2: Click "Start Campaign" button
    start_btn = page.locator('#start-campaign-btn, button:has-text("Start Campaign")')
    if await start_btn.count() > 0:
        print("Clicking 'Start Campaign' button...")
        await start_btn.first.scroll_into_view_if_needed()
        await asyncio.sleep(1)
        await start_btn.first.click()
        await asyncio.sleep(3)
        print("Campaign launched!")
    else:
        print("Start Campaign button not found")

    # Take screenshot of progress
    await page.screenshot(path='campaign_launched.png')
    print("Screenshot saved: campaign_launched.png")


async def monitor_campaign(page):
    """Monitor campaign progress."""
    print("\n--- Campaign Status ---")

    # Check progress elements
    status_text = page.locator('#campaign-status-text')
    if await status_text.count() > 0:
        status = await status_text.text_content()
        print(f"Status: {status}")

    email_count = page.locator('#campaign-email-count')
    if await email_count.count() > 0:
        count = await email_count.text_content()
        print(f"Emails: {count}")

    error_count = page.locator('#campaign-error-count')
    if await error_count.count() > 0:
        errors = await error_count.text_content()
        print(f"Errors: {errors}")

    # Take screenshot
    await page.screenshot(path='campaign_progress.png')
    print("Screenshot saved: campaign_progress.png")


async def pause_campaign(page):
    """Pause running campaign."""
    print("Pausing campaign...")
    pause_btn = page.locator('#pause-btn, button:has-text("Pause")')
    if await pause_btn.count() > 0:
        await pause_btn.first.click()
        await asyncio.sleep(2)
        print("Campaign paused!")
    else:
        print("Pause button not found")


async def resume_campaign(page):
    """Resume paused campaign."""
    print("Resuming campaign...")
    resume_btn = page.locator('#resume-btn, button:has-text("Resume")')
    if await resume_btn.count() > 0:
        await resume_btn.first.click()
        await asyncio.sleep(2)
        print("Campaign resumed!")
    else:
        print("Resume button not found")


async def cancel_campaign(page):
    """Cancel running campaign."""
    print("Cancelling campaign...")
    cancel_btn = page.locator('#cancel-btn, button:has-text("Cancel")')
    if await cancel_btn.count() > 0:
        await cancel_btn.first.click()
        await asyncio.sleep(2)
        print("Campaign cancelled!")
    else:
        print("Cancel button not found")


async def get_analytics(page):
    """Get campaign analytics."""
    print("\n--- Campaign Analytics ---")

    # Navigate to Analytics tab
    analytics_tab = page.locator('text=Analytics').first
    if await analytics_tab.count() > 0:
        await analytics_tab.click()
        await asyncio.sleep(2)

    # Read stats
    stats = {
        'sent': '#stat-sent',
        'campaigns': '#stat-campaigns',
        'rate': '#stat-rate',
        'avg': '#stat-avg'
    }

    for name, selector in stats.items():
        elem = page.locator(selector)
        if await elem.count() > 0:
            value = await elem.text_content()
            print(f"{name.capitalize()}: {value}")

    # Take screenshot
    await page.screenshot(path='campaign_analytics.png', full_page=True)
    print("\nScreenshot saved: campaign_analytics.png")


async def create_campaign(csv_path=None, company="Evolve Robot Lab", product="", goal="customer_acquisition", use_folder=True, use_chatbot=True):
    """Full campaign creation flow with AI chatbot document parsing."""
    print("\n" + "=" * 50)
    print("DurgaMail Campaign Automation v3.0 (Chatbot Flow)")
    print("=" * 50)

    # Auto-detect files from campaign_input folder
    files = None
    memo_doc_path = None

    if use_folder:
        print("\nScanning campaign_input folder...")
        files = get_campaign_files()

        if files['csv']:
            csv_path = files['csv']

        # Get memo document for chatbot parsing
        if files['memo_doc']:
            memo_doc_path = files['memo_doc']

        # Fallback: read text memo if no document
        if not memo_doc_path and files['memo_text'] and not product:
            product = await read_memo_content(files['memo_text'])

        print(f"\nFiles detected:")
        print(f"  CSV: {os.path.basename(files['csv']) if files['csv'] else 'None'}")
        print(f"  Memo (doc): {os.path.basename(memo_doc_path) if memo_doc_path else 'None'}")
        print(f"  Memo (text): {os.path.basename(files['memo_text']) if files['memo_text'] else 'None'}")
        print(f"  Attachments: {len(files['attachments'])}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        try:
            # Login and navigate
            await login_to_dashboard(page)
            await navigate_to_campaign(page)

            # Step 1: Upload recipients CSV
            if csv_path:
                await upload_recipients(page, csv_path=csv_path)
            else:
                print("No CSV file found! Please add a .csv file to campaign_input folder.")
                return

            # Step 2: Continue to compose
            await continue_to_compose(page)

            # Step 3: Use chatbot to parse document and fill form
            if use_chatbot and memo_doc_path:
                chatbot_success = await interact_with_chatbot(page, memo_doc_path)
                if chatbot_success:
                    print("Form auto-filled by AI chatbot!")
                else:
                    print("Chatbot interaction failed, using fallback...")
                    # Fallback: fill form manually
                    await compose_email(page, company=company, product=product, goal=goal, generate_ai=False)
            else:
                # No document - fill form manually
                await compose_email(page, company=company, product=product, goal=goal, generate_ai=True)

            # Step 4: Upload attachments
            if files and files['attachments']:
                await upload_attachments(page, files['attachments'])

            # Step 5: Set campaign goal
            goal_select = page.locator('#campaign-goal-select')
            if await goal_select.count() > 0:
                await goal_select.select_option(goal)
                print(f"Campaign goal set: {GOALS.get(goal, goal)}")

            # Step 6: Generate emails
            await launch_campaign(page)

            # Monitor progress
            await asyncio.sleep(5)
            await monitor_campaign(page)

            print("\n" + "=" * 50)
            print("Campaign automation complete!")
            print("=" * 50)

            # Keep browser open
            print("\nBrowser will stay open for 30 seconds...")
            await asyncio.sleep(30)

        except Exception as e:
            print(f"\nError: {e}")
            await page.screenshot(path='campaign_error.png')
            print("Error screenshot saved: campaign_error.png")

        finally:
            await browser.close()


async def run_action(action, **kwargs):
    """Run a specific campaign action."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        try:
            await login_to_dashboard(page)
            await navigate_to_campaign(page)

            if action == "upload":
                await upload_recipients(page, csv_path=kwargs.get('csv'))

            elif action == "generate":
                await continue_to_compose(page)
                await compose_email(
                    page,
                    company=kwargs.get('company', ''),
                    product=kwargs.get('product', ''),
                    goal=kwargs.get('goal', 'customer_acquisition')
                )

            elif action == "status":
                await monitor_campaign(page)

            elif action == "pause":
                await pause_campaign(page)

            elif action == "resume":
                await resume_campaign(page)

            elif action == "cancel":
                await cancel_campaign(page)

            elif action == "analytics":
                await get_analytics(page)

            print("\nAction complete! Browser stays open for 20 seconds...")
            await asyncio.sleep(20)

        except Exception as e:
            print(f"\nError: {e}")
            await page.screenshot(path='campaign_error.png')

        finally:
            await browser.close()


def main():
    parser = argparse.ArgumentParser(description="DurgaMail Campaign Automation v2.0")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Create command (folder-based)
    create_parser = subparsers.add_parser('create', help='Create campaign from folder')
    create_parser.add_argument('--csv', help='Path to CSV file (optional - auto-detected from folder)')
    create_parser.add_argument('--company', default='Evolve Robot Lab', help='Company name')
    create_parser.add_argument('--product', default='', help='Product description (reads from memo if empty)')
    create_parser.add_argument('--goal', default='customer_acquisition',
                               choices=list(GOALS.keys()), help='Campaign goal')
    create_parser.add_argument('--no-folder', action='store_true', help='Disable folder auto-detection')

    # Scan command - just show what's in the folder
    subparsers.add_parser('scan', help='Scan campaign_input folder and show files')

    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload recipients only')
    upload_parser.add_argument('--csv', help='Path to CSV file (auto-detected if not provided)')

    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate AI email')
    gen_parser.add_argument('--company', default='Evolve Robot Lab', help='Company name')
    gen_parser.add_argument('--product', default='', help='Product description')
    gen_parser.add_argument('--goal', default='customer_acquisition',
                            choices=list(GOALS.keys()), help='Campaign goal')

    # Control commands
    subparsers.add_parser('status', help='Get campaign status')
    subparsers.add_parser('pause', help='Pause campaign')
    subparsers.add_parser('resume', help='Resume campaign')
    subparsers.add_parser('cancel', help='Cancel campaign')
    subparsers.add_parser('analytics', help='View analytics')

    args = parser.parse_args()

    if args.command == 'create':
        asyncio.run(create_campaign(
            csv_path=args.csv,
            company=args.company,
            product=args.product,
            goal=args.goal,
            use_folder=not args.no_folder
        ))

    elif args.command == 'scan':
        print("\n=== Scanning campaign_input folder ===")
        files = get_campaign_files()
        print(f"\nReady to launch campaign with:")
        print(f"  Recipients: {os.path.basename(files['csv']) if files['csv'] else 'NOT FOUND'}")
        print(f"  Memo (text): {os.path.basename(files['memo_text']) if files['memo_text'] else 'None'}")
        print(f"  Memo (doc): {os.path.basename(files['memo_doc']) if files['memo_doc'] else 'None'}")
        print(f"  Attachments: {len(files['attachments'])} files")
        if files['attachments']:
            for a in files['attachments']:
                print(f"    - {os.path.basename(a)}")

    elif args.command == 'upload':
        csv_path = args.csv
        if not csv_path:
            files = get_campaign_files()
            csv_path = files['csv']
        asyncio.run(run_action('upload', csv=csv_path))

    elif args.command == 'generate':
        asyncio.run(run_action('generate',
                               company=args.company,
                               product=args.product,
                               goal=args.goal))

    elif args.command in ['status', 'pause', 'resume', 'cancel', 'analytics']:
        asyncio.run(run_action(args.command))

    else:
        parser.print_help()
        print("\n" + "=" * 50)
        print("FOLDER-BASED USAGE (Recommended):")
        print("=" * 50)
        print(f"\n1. Put files in: {CAMPAIGN_INPUT_DIR}/")
        print("   - contacts.csv (or any .csv file)")
        print("   - memo.txt or pitch.md (optional)")
        print("   - attachments/ folder with PDF, images, etc.")
        print("\n2. Run: python campaign_auto.py create --goal partnership")
        print("\nOther examples:")
        print("  python campaign_auto.py scan                    # Check folder contents")
        print("  python campaign_auto.py create                  # Create with defaults")
        print("  python campaign_auto.py status                  # Check running campaign")


if __name__ == "__main__":
    main()
