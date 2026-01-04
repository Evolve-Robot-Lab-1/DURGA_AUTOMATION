#!/usr/bin/env python3
"""
Ask Durga - Marketing Assistant
Natural language control of DurgaMail's 3 applications:
  1. Inbox - View & reply to emails
  2. Campaign - Create & send marketing campaigns
  3. Analytics - View statistics

Usage:
    python ask_durga_marketing.py

Then type commands like:
  - "show inbox"
  - "reply to email 1"
  - "create campaign for investors"
  - "show analytics"
  - "send marketing email to john@company.com"
"""

import asyncio
import re
import os
from playwright.async_api import async_playwright

# Configuration
DURGAMAIL_URL = "http://localhost:5002"
DASHBOARD_URL = "http://localhost:8080"
EMAIL = "evolverobotlab@gmail.com"
PASSWORD = "katacity"


class AskDurgaMarketing:
    """AI Marketing Assistant - Controls 3 DurgaMail Apps."""

    def __init__(self):
        self.browser = None
        self.page = None
        self.current_app = None  # inbox, campaign, analytics

    async def start(self):
        """Start browser and login."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        context = await self.browser.new_context(no_viewport=True)
        self.page = await context.new_page()

        # Login
        print("Logging in to DurgaAI...")
        await self.page.goto(DASHBOARD_URL)
        await self.page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)

        if await self.page.locator('text=evolve robot lab').count() == 0:
            await self.page.locator('text=LOGIN').first.click()
            await asyncio.sleep(2)
            await self.page.click('a:has-text("Log In"), span:has-text("Log In")')
            await asyncio.sleep(1)
            await self.page.fill('#login-email', EMAIL)
            await self.page.fill('#login-password', PASSWORD)
            await self.page.locator('button:has-text("Log In")').first.click()
            await asyncio.sleep(3)
            if await self.page.locator('#auth-modal.active').count() > 0:
                await self.page.keyboard.press('Escape')

        await self.page.goto(DURGAMAIL_URL)
        await asyncio.sleep(3)
        print("Ready!\n")
        return self

    # ==================== APP 1: INBOX ====================
    async def open_inbox(self):
        """Open Inbox app."""
        await self.page.locator('text=Inbox').first.click()
        await asyncio.sleep(2)
        self.current_app = 'inbox'

        # Refresh to load emails
        refresh_btn = self.page.locator('#refresh-btn, button:has-text("Refresh")')
        if await refresh_btn.count() > 0:
            await refresh_btn.first.click()
            await asyncio.sleep(3)

        return "Inbox opened. You can see your emails."

    async def list_emails(self, count=5):
        """List recent emails."""
        if self.current_app != 'inbox':
            await self.open_inbox()

        emails = []
        rows = self.page.locator('.email-item, .email-row, tr[data-email-id]')
        total = min(await rows.count(), count)

        for i in range(total):
            try:
                row = rows.nth(i)
                sender = await row.locator('.email-sender, .sender, td:nth-child(1)').text_content()
                subject = await row.locator('.email-subject, .subject, td:nth-child(2)').text_content()
                emails.append(f"{i+1}. {sender.strip()[:20]} - {subject.strip()[:40]}")
            except:
                continue

        if emails:
            return "Recent emails:\n" + "\n".join(emails)
        return "No emails found. Click Refresh to load."

    async def view_email(self, email_num=1):
        """View specific email."""
        if self.current_app != 'inbox':
            await self.open_inbox()

        rows = self.page.locator('.email-item, .email-row, tr[data-email-id]')
        if await rows.count() >= email_num:
            await rows.nth(email_num - 1).click()
            await asyncio.sleep(2)

            sender = await self.page.locator('#email-detail-sender, .detail-sender').text_content()
            subject = await self.page.locator('#email-detail-subject, .detail-subject').text_content()

            return f"Email #{email_num}:\nFrom: {sender.strip() if sender else 'Unknown'}\nSubject: {subject.strip() if subject else 'No subject'}"
        return f"Email #{email_num} not found."

    async def reply_email(self, email_num=1, use_ai=True):
        """Reply to email with AI."""
        await self.view_email(email_num)

        reply_btn = self.page.locator('#reply-btn, button:has-text("Reply")')
        if await reply_btn.count() > 0:
            await reply_btn.first.click()
            await asyncio.sleep(2)

            if use_ai:
                ai_btn = self.page.locator('#ai-suggestions-btn, button:has-text("AI")')
                if await ai_btn.count() > 0:
                    await ai_btn.first.click()
                    await asyncio.sleep(3)
                    return f"AI reply generated for email #{email_num}. Review and send when ready."

        return f"Reply panel opened for email #{email_num}."

    # ==================== APP 2: CAMPAIGN ====================
    async def open_campaign(self):
        """Open Campaign app."""
        await self.page.locator('text=Campaign').first.click()
        await asyncio.sleep(2)
        self.current_app = 'campaign'
        return "Campaign section opened. Ready to create marketing campaigns."

    async def create_campaign(self, csv_path=None, emails=None, goal='customers',
                               company='Evolve Robot Lab', product='AI & Robotics'):
        """Create marketing campaign."""
        if self.current_app != 'campaign':
            await self.open_campaign()

        # Upload recipients
        if csv_path and os.path.exists(csv_path):
            file_input = self.page.locator('#file-input')
            await file_input.set_input_files(csv_path)
            await asyncio.sleep(3)
        elif emails:
            textarea = self.page.locator('#recipient-list-textarea')
            if await textarea.count() > 0:
                await textarea.fill("\n".join(emails))

        # Continue to compose
        continue_btn = self.page.locator('#continue-to-compose, button:has-text("Continue")')
        if await continue_btn.count() > 0:
            await continue_btn.first.click()
            await asyncio.sleep(2)

        # Fill details
        company_input = self.page.locator('#company-info')
        if await company_input.count() > 0:
            await company_input.fill(company)

        product_input = self.page.locator('#product-info')
        if await product_input.count() > 0:
            await product_input.fill(product)

        goal_select = self.page.locator('#campaign-goal-select')
        if await goal_select.count() > 0:
            await goal_select.select_option(goal)

        return f"Campaign configured for: {goal}. Click 'Generate Emails' to create AI content."

    async def generate_campaign_emails(self):
        """Generate AI emails for campaign."""
        generate_btn = self.page.locator('button:has-text("Generate Emails")')
        if await generate_btn.count() > 0:
            await generate_btn.first.scroll_into_view_if_needed()
            await generate_btn.first.click()
            await asyncio.sleep(5)

            # Wait for generation
            for _ in range(30):
                start_btn = self.page.locator('#start-campaign-btn')
                if await start_btn.count() > 0 and await start_btn.first.is_visible():
                    return "AI emails generated! Click 'Start Campaign' to send."
                await asyncio.sleep(1)

        return "Emails being generated..."

    async def start_campaign(self):
        """Start the campaign."""
        start_btn = self.page.locator('#start-campaign-btn, button:has-text("Start Campaign")')
        if await start_btn.count() > 0:
            await start_btn.first.click()
            await asyncio.sleep(3)
            return "Campaign started! Emails are being sent."
        return "Start button not found. Generate emails first."

    async def pause_campaign(self):
        """Pause campaign."""
        btn = self.page.locator('#pause-btn, button:has-text("Pause")')
        if await btn.count() > 0:
            await btn.first.click()
            return "Campaign paused."
        return "No active campaign to pause."

    async def resume_campaign(self):
        """Resume campaign."""
        btn = self.page.locator('#resume-btn, button:has-text("Resume")')
        if await btn.count() > 0:
            await btn.first.click()
            return "Campaign resumed."
        return "No paused campaign to resume."

    # ==================== APP 3: ANALYTICS ====================
    async def open_analytics(self):
        """Open Analytics app."""
        await self.page.locator('text=Analytics').first.click()
        await asyncio.sleep(2)
        self.current_app = 'analytics'
        return "Analytics section opened."

    async def get_stats(self):
        """Get campaign statistics."""
        if self.current_app != 'analytics':
            await self.open_analytics()

        stats = []
        for stat_id, label in [('stat-sent', 'Emails Sent'), ('stat-campaigns', 'Campaigns'),
                                ('stat-rate', 'Success Rate'), ('stat-avg', 'Avg per Campaign')]:
            elem = self.page.locator(f'#{stat_id}')
            if await elem.count() > 0:
                value = await elem.text_content()
                stats.append(f"{label}: {value.strip()}")

        if stats:
            return "Campaign Statistics:\n" + "\n".join(stats)
        return "No statistics available yet."

    # ==================== NATURAL LANGUAGE PROCESSING ====================
    async def process_command(self, command):
        """Process natural language command."""
        cmd = command.lower().strip()

        # INBOX commands
        if any(w in cmd for w in ['inbox', 'email', 'mail']):
            if 'reply' in cmd:
                num = self._extract_number(cmd) or 1
                return await self.reply_email(num)
            elif 'view' in cmd or 'read' in cmd or 'open' in cmd:
                num = self._extract_number(cmd) or 1
                return await self.view_email(num)
            elif 'list' in cmd or 'show' in cmd:
                return await self.list_emails()
            else:
                return await self.open_inbox()

        # CAMPAIGN commands
        elif any(w in cmd for w in ['campaign', 'marketing', 'send']):
            if 'create' in cmd or 'new' in cmd:
                goal = 'customers'
                if 'investor' in cmd or 'vc' in cmd or 'funding' in cmd:
                    goal = 'vc_funding'
                elif 'partner' in cmd:
                    goal = 'partnership'
                elif 'sale' in cmd:
                    goal = 'ai_robotics_sales'
                return await self.create_campaign(goal=goal)
            elif 'generate' in cmd:
                return await self.generate_campaign_emails()
            elif 'start' in cmd or 'launch' in cmd:
                return await self.start_campaign()
            elif 'pause' in cmd:
                return await self.pause_campaign()
            elif 'resume' in cmd:
                return await self.resume_campaign()
            elif 'status' in cmd:
                return await self.open_campaign()
            else:
                return await self.open_campaign()

        # ANALYTICS commands
        elif any(w in cmd for w in ['analytics', 'stats', 'statistics', 'report']):
            return await self.get_stats()

        # HELP
        elif 'help' in cmd:
            return """Available commands:

INBOX:
  "show inbox" - Open inbox
  "list emails" - Show recent emails
  "view email 1" - Read email #1
  "reply to email 2" - Reply to email #2

CAMPAIGN:
  "create campaign" - Start new campaign
  "create investor campaign" - Campaign for VCs
  "generate emails" - Generate AI content
  "start campaign" - Send emails
  "pause/resume campaign" - Control campaign

ANALYTICS:
  "show analytics" - View statistics
  "show stats" - Campaign performance
"""
        else:
            return "I didn't understand. Type 'help' for available commands."

    def _extract_number(self, text):
        """Extract number from text."""
        match = re.search(r'\d+', text)
        return int(match.group()) if match else None

    async def close(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()


async def main():
    """Interactive Ask Durga Marketing Assistant."""
    print("""
╔════════════════════════════════════════════════════════════╗
║           ASK DURGA - MARKETING ASSISTANT                 ║
╠════════════════════════════════════════════════════════════╣
║  3 Apps Available:                                        ║
║    1. INBOX    - View & reply to emails                   ║
║    2. CAMPAIGN - Create marketing campaigns               ║
║    3. ANALYTICS - View statistics                         ║
╠════════════════════════════════════════════════════════════╣
║  Type 'help' for commands, 'quit' to exit                 ║
╚════════════════════════════════════════════════════════════╝
""")

    assistant = await AskDurgaMarketing().start()

    try:
        while True:
            try:
                command = input("\n🤖 Ask Durga > ").strip()
            except EOFError:
                break

            if not command:
                continue

            if command.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break

            response = await assistant.process_command(command)
            print(f"\n{response}")

    finally:
        await assistant.close()


if __name__ == "__main__":
    asyncio.run(main())
