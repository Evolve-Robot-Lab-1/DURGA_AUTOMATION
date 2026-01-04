#!/usr/bin/env python3
"""
Durga Controller - Browser Automation Backend
Provides REST API for Ask Durga with clickable actions.

Usage:
    python durga_controller.py

API Endpoints:
    GET  /health              - Health check
    GET  /api/inbox           - Get inbox emails
    GET  /api/inbox/<id>      - Get specific email
    POST /api/inbox/reply     - Reply to email
    POST /api/inbox/refresh   - Refresh inbox
    GET  /api/campaign/status - Campaign status
    POST /api/campaign/create - Create campaign
    POST /api/campaign/pause  - Pause campaign
    POST /api/campaign/resume - Resume campaign
    GET  /api/analytics       - Get analytics
    POST /api/ask             - Ask Durga (natural language)
"""

import asyncio
import json
import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from playwright.async_api import async_playwright, Browser, Page
from functools import wraps
import threading
import queue

app = Flask(__name__)
CORS(app)

# Configuration
DURGAMAIL_URL = "http://localhost:5002"
DASHBOARD_URL = "http://localhost:8080"
EMAIL = "evolverobotlab@gmail.com"
PASSWORD = "katacity"

# Global browser instance
browser_instance = None
page_instance = None
browser_lock = threading.Lock()
action_queue = queue.Queue()


class DurgaController:
    """Browser automation controller for DurgaMail."""

    def __init__(self):
        self.browser = None
        self.page = None
        self.logged_in = False
        self.current_section = None

    async def initialize(self):
        """Initialize browser and login."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,  # Run headless for API
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await context.new_page()
        await self._login()
        return self

    async def _login(self):
        """Login to DurgaAI dashboard."""
        await self.page.goto(DASHBOARD_URL)
        await self.page.wait_for_load_state('networkidle')
        await asyncio.sleep(2)

        # Check if already logged in
        logged_in = await self.page.locator('text=evolve robot lab').count() > 0

        if not logged_in:
            login_btn = self.page.locator('text=LOGIN').first
            if await login_btn.count() > 0:
                await login_btn.click()
                await asyncio.sleep(2)

                await self.page.wait_for_selector('text=Already have an account')
                await self.page.click('a:has-text("Log In"), span:has-text("Log In")')
                await asyncio.sleep(1)

                await self.page.wait_for_selector('#login-email', state='visible', timeout=10000)
                await self.page.fill('#login-email', EMAIL)
                await self.page.fill('#login-password', PASSWORD)

                submit_btn = self.page.locator('button:has-text("Log In")').first
                await submit_btn.click()
                await asyncio.sleep(3)

                modal = self.page.locator('#auth-modal.active')
                if await modal.count() > 0:
                    await self.page.keyboard.press('Escape')
                    await asyncio.sleep(1)

        self.logged_in = True

    async def navigate_to_durgamail(self):
        """Navigate to DurgaMail."""
        await self.page.goto(DURGAMAIL_URL)
        await asyncio.sleep(3)

    async def go_to_inbox(self):
        """Navigate to Inbox section."""
        await self.navigate_to_durgamail()
        inbox_tab = self.page.locator('text=Inbox').first
        if await inbox_tab.count() > 0:
            await inbox_tab.click()
            await asyncio.sleep(2)
        self.current_section = 'inbox'

    async def go_to_campaign(self):
        """Navigate to Campaign section."""
        await self.navigate_to_durgamail()
        campaign_tab = self.page.locator('text=Campaign').first
        if await campaign_tab.count() > 0:
            await campaign_tab.click()
            await asyncio.sleep(2)
        self.current_section = 'campaign'

    async def go_to_analytics(self):
        """Navigate to Analytics section."""
        await self.navigate_to_durgamail()
        analytics_tab = self.page.locator('text=Analytics').first
        if await analytics_tab.count() > 0:
            await analytics_tab.click()
            await asyncio.sleep(2)
        self.current_section = 'analytics'

    async def get_inbox_emails(self, limit=20):
        """Get list of emails from inbox."""
        if self.current_section != 'inbox':
            await self.go_to_inbox()

        # Click refresh
        refresh_btn = self.page.locator('#refresh-btn, button:has-text("Refresh")')
        if await refresh_btn.count() > 0:
            await refresh_btn.first.click()
            await asyncio.sleep(3)

        emails = []
        email_rows = self.page.locator('.email-item, .email-row, tr[data-email-id]')
        count = min(await email_rows.count(), limit)

        for i in range(count):
            try:
                row = email_rows.nth(i)

                # Extract email data
                sender = await row.locator('.email-sender, .sender, td:nth-child(1)').text_content()
                subject = await row.locator('.email-subject, .subject, td:nth-child(2)').text_content()
                snippet = await row.locator('.email-snippet, .snippet, td:nth-child(3)').text_content()
                date = await row.locator('.email-date, .date, td:nth-child(4)').text_content()

                emails.append({
                    'id': i + 1,
                    'sender': sender.strip() if sender else '',
                    'subject': subject.strip() if subject else '',
                    'snippet': snippet.strip() if snippet else '',
                    'date': date.strip() if date else '',
                    'actions': [
                        {'label': 'View', 'action': 'view', 'endpoint': f'/api/inbox/{i+1}'},
                        {'label': 'Reply', 'action': 'reply', 'endpoint': f'/api/inbox/reply', 'params': {'email_id': i+1}},
                        {'label': 'Archive', 'action': 'archive', 'endpoint': f'/api/inbox/archive', 'params': {'email_id': i+1}}
                    ]
                })
            except:
                continue

        return {
            'success': True,
            'count': len(emails),
            'emails': emails,
            'actions': [
                {'label': 'Refresh Inbox', 'action': 'refresh', 'endpoint': '/api/inbox/refresh'},
                {'label': 'Compose New', 'action': 'compose', 'endpoint': '/api/compose'}
            ]
        }

    async def get_email_detail(self, email_id):
        """Get specific email details."""
        if self.current_section != 'inbox':
            await self.go_to_inbox()

        # Click on email row
        email_rows = self.page.locator('.email-item, .email-row, tr[data-email-id]')
        if await email_rows.count() >= email_id:
            await email_rows.nth(email_id - 1).click()
            await asyncio.sleep(2)

            # Extract full email content
            sender = await self.page.locator('#email-detail-sender, .detail-sender').text_content()
            subject = await self.page.locator('#email-detail-subject, .detail-subject').text_content()
            body = await self.page.locator('#email-detail-body, .detail-body').text_content()
            date = await self.page.locator('#email-detail-date, .detail-date').text_content()

            return {
                'success': True,
                'email': {
                    'id': email_id,
                    'sender': sender.strip() if sender else '',
                    'subject': subject.strip() if subject else '',
                    'body': body.strip() if body else '',
                    'date': date.strip() if date else ''
                },
                'actions': [
                    {'label': 'Reply', 'action': 'reply', 'endpoint': '/api/inbox/reply', 'params': {'email_id': email_id}},
                    {'label': 'Reply with AI', 'action': 'reply_ai', 'endpoint': '/api/inbox/reply', 'params': {'email_id': email_id, 'use_ai': True}},
                    {'label': 'Forward', 'action': 'forward', 'endpoint': '/api/inbox/forward', 'params': {'email_id': email_id}},
                    {'label': 'Archive', 'action': 'archive', 'endpoint': '/api/inbox/archive', 'params': {'email_id': email_id}},
                    {'label': 'Back to Inbox', 'action': 'back', 'endpoint': '/api/inbox'}
                ]
            }

        return {'success': False, 'error': 'Email not found'}

    async def reply_to_email(self, email_id, message=None, use_ai=False, template=None):
        """Reply to an email."""
        if self.current_section != 'inbox':
            await self.go_to_inbox()

        # Click on email
        email_rows = self.page.locator('.email-item, .email-row, tr[data-email-id]')
        if await email_rows.count() >= email_id:
            await email_rows.nth(email_id - 1).click()
            await asyncio.sleep(2)

            # Click reply button
            reply_btn = self.page.locator('#reply-btn, button:has-text("Reply")')
            if await reply_btn.count() > 0:
                await reply_btn.first.click()
                await asyncio.sleep(2)

                if use_ai:
                    # Click AI suggestions
                    ai_btn = self.page.locator('#ai-suggestions-btn, button:has-text("AI")')
                    if await ai_btn.count() > 0:
                        await ai_btn.first.click()
                        await asyncio.sleep(3)

                        # Get AI suggestion
                        suggestion = await self.page.locator('#ai-suggestion-text, .suggestion-text').text_content()

                        return {
                            'success': True,
                            'ai_suggestion': suggestion.strip() if suggestion else '',
                            'actions': [
                                {'label': 'Use This Reply', 'action': 'send', 'endpoint': '/api/inbox/send', 'params': {'email_id': email_id, 'message': suggestion}},
                                {'label': 'Edit & Send', 'action': 'edit', 'endpoint': '/api/inbox/reply', 'params': {'email_id': email_id, 'draft': suggestion}},
                                {'label': 'Generate Another', 'action': 'regenerate', 'endpoint': '/api/inbox/reply', 'params': {'email_id': email_id, 'use_ai': True}},
                                {'label': 'Cancel', 'action': 'cancel', 'endpoint': '/api/inbox'}
                            ]
                        }

                elif message:
                    # Fill reply message
                    reply_textarea = self.page.locator('#reply-message, textarea[name="reply"]')
                    if await reply_textarea.count() > 0:
                        await reply_textarea.fill(message)

                        # Click send
                        send_btn = self.page.locator('#send-reply-btn, button:has-text("Send")')
                        if await send_btn.count() > 0:
                            await send_btn.first.click()
                            await asyncio.sleep(2)

                            return {
                                'success': True,
                                'message': 'Reply sent successfully',
                                'actions': [
                                    {'label': 'Back to Inbox', 'action': 'back', 'endpoint': '/api/inbox'}
                                ]
                            }

        return {'success': False, 'error': 'Could not send reply'}

    async def get_campaign_status(self):
        """Get current campaign status."""
        if self.current_section != 'campaign':
            await self.go_to_campaign()

        status_text = ''
        email_count = ''
        error_count = ''
        progress = 0

        status_elem = self.page.locator('#campaign-status-text')
        if await status_elem.count() > 0:
            status_text = await status_elem.text_content()

        count_elem = self.page.locator('#campaign-email-count')
        if await count_elem.count() > 0:
            email_count = await count_elem.text_content()

        error_elem = self.page.locator('#campaign-error-count')
        if await error_elem.count() > 0:
            error_count = await error_elem.text_content()

        progress_elem = self.page.locator('#campaign-progress-bar')
        if await progress_elem.count() > 0:
            style = await progress_elem.get_attribute('style')
            if style and 'width' in style:
                match = re.search(r'width:\s*(\d+)', style)
                if match:
                    progress = int(match.group(1))

        return {
            'success': True,
            'campaign': {
                'status': status_text.strip() if status_text else 'No active campaign',
                'emails_sent': email_count.strip() if email_count else '0',
                'errors': error_count.strip() if error_count else '0',
                'progress': progress
            },
            'actions': [
                {'label': 'Pause Campaign', 'action': 'pause', 'endpoint': '/api/campaign/pause'},
                {'label': 'Resume Campaign', 'action': 'resume', 'endpoint': '/api/campaign/resume'},
                {'label': 'Cancel Campaign', 'action': 'cancel', 'endpoint': '/api/campaign/cancel'},
                {'label': 'View Analytics', 'action': 'analytics', 'endpoint': '/api/analytics'},
                {'label': 'New Campaign', 'action': 'create', 'endpoint': '/api/campaign/create'}
            ]
        }

    async def create_campaign(self, recipients=None, csv_path=None, company='', product='', goal='customer_acquisition'):
        """Create a new campaign."""
        if self.current_section != 'campaign':
            await self.go_to_campaign()

        # Upload CSV if provided
        if csv_path and os.path.exists(csv_path):
            file_input = self.page.locator('#file-input')
            if await file_input.count() > 0:
                await file_input.set_input_files(csv_path)
                await asyncio.sleep(3)

        # Continue to compose
        continue_btn = self.page.locator('#continue-to-compose, button:has-text("Continue")')
        if await continue_btn.count() > 0:
            await continue_btn.first.click()
            await asyncio.sleep(2)

        # Fill company info
        if company:
            company_input = self.page.locator('#company-info')
            if await company_input.count() > 0:
                await company_input.fill(company)

        # Fill product info
        if product:
            product_input = self.page.locator('#product-info')
            if await product_input.count() > 0:
                await product_input.fill(product)

        # Select goal
        goal_select = self.page.locator('#campaign-goal-select')
        if await goal_select.count() > 0:
            await goal_select.select_option(goal)

        await asyncio.sleep(1)

        return {
            'success': True,
            'message': 'Campaign settings configured',
            'actions': [
                {'label': 'Generate AI Email', 'action': 'generate', 'endpoint': '/api/campaign/generate'},
                {'label': 'Preview Campaign', 'action': 'preview', 'endpoint': '/api/campaign/preview'},
                {'label': 'Launch Campaign', 'action': 'launch', 'endpoint': '/api/campaign/launch'},
                {'label': 'Cancel', 'action': 'cancel', 'endpoint': '/api/campaign'}
            ]
        }

    async def pause_campaign(self):
        """Pause running campaign."""
        if self.current_section != 'campaign':
            await self.go_to_campaign()

        pause_btn = self.page.locator('#pause-btn, button:has-text("Pause")')
        if await pause_btn.count() > 0:
            await pause_btn.first.click()
            await asyncio.sleep(2)
            return {
                'success': True,
                'message': 'Campaign paused',
                'actions': [
                    {'label': 'Resume Campaign', 'action': 'resume', 'endpoint': '/api/campaign/resume'},
                    {'label': 'Cancel Campaign', 'action': 'cancel', 'endpoint': '/api/campaign/cancel'}
                ]
            }
        return {'success': False, 'error': 'Pause button not found'}

    async def resume_campaign(self):
        """Resume paused campaign."""
        if self.current_section != 'campaign':
            await self.go_to_campaign()

        resume_btn = self.page.locator('#resume-btn, button:has-text("Resume")')
        if await resume_btn.count() > 0:
            await resume_btn.first.click()
            await asyncio.sleep(2)
            return {
                'success': True,
                'message': 'Campaign resumed',
                'actions': [
                    {'label': 'Pause Campaign', 'action': 'pause', 'endpoint': '/api/campaign/pause'},
                    {'label': 'View Status', 'action': 'status', 'endpoint': '/api/campaign/status'}
                ]
            }
        return {'success': False, 'error': 'Resume button not found'}

    async def get_analytics(self):
        """Get campaign analytics."""
        if self.current_section != 'analytics':
            await self.go_to_analytics()

        stats = {}

        for stat_id in ['stat-sent', 'stat-campaigns', 'stat-rate', 'stat-avg']:
            elem = self.page.locator(f'#{stat_id}')
            if await elem.count() > 0:
                value = await elem.text_content()
                key = stat_id.replace('stat-', '')
                stats[key] = value.strip() if value else '0'

        return {
            'success': True,
            'analytics': stats,
            'actions': [
                {'label': 'Export Report', 'action': 'export', 'endpoint': '/api/analytics/export'},
                {'label': 'View Campaigns', 'action': 'campaigns', 'endpoint': '/api/campaign/history'},
                {'label': 'Back to Inbox', 'action': 'inbox', 'endpoint': '/api/inbox'}
            ]
        }

    async def process_natural_query(self, query):
        """Process natural language query and return actions."""
        query_lower = query.lower()

        # Intent detection
        if any(word in query_lower for word in ['inbox', 'email', 'mail', 'message']):
            if 'reply' in query_lower:
                # Extract email number
                match = re.search(r'(\d+)', query)
                email_id = int(match.group(1)) if match else 1
                return await self.reply_to_email(email_id, use_ai=True)
            elif 'view' in query_lower or 'read' in query_lower or 'open' in query_lower:
                match = re.search(r'(\d+)', query)
                email_id = int(match.group(1)) if match else 1
                return await self.get_email_detail(email_id)
            else:
                return await self.get_inbox_emails()

        elif any(word in query_lower for word in ['campaign', 'send', 'bulk']):
            if 'status' in query_lower:
                return await self.get_campaign_status()
            elif 'pause' in query_lower:
                return await self.pause_campaign()
            elif 'resume' in query_lower:
                return await self.resume_campaign()
            elif 'create' in query_lower or 'new' in query_lower:
                return {
                    'success': True,
                    'message': 'Ready to create campaign',
                    'actions': [
                        {'label': 'Upload CSV', 'action': 'upload', 'endpoint': '/api/campaign/create', 'params': {'step': 'upload'}},
                        {'label': 'Manual Entry', 'action': 'manual', 'endpoint': '/api/campaign/create', 'params': {'step': 'manual'}}
                    ]
                }
            else:
                return await self.get_campaign_status()

        elif any(word in query_lower for word in ['analytics', 'stats', 'report', 'performance']):
            return await self.get_analytics()

        else:
            # Default: show main menu
            return {
                'success': True,
                'message': 'How can I help you?',
                'actions': [
                    {'label': 'View Inbox', 'action': 'inbox', 'endpoint': '/api/inbox'},
                    {'label': 'Campaign Status', 'action': 'campaign', 'endpoint': '/api/campaign/status'},
                    {'label': 'Create Campaign', 'action': 'create', 'endpoint': '/api/campaign/create'},
                    {'label': 'View Analytics', 'action': 'analytics', 'endpoint': '/api/analytics'}
                ]
            }

    async def close(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()


# Global controller
controller = None


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def ensure_controller(f):
    """Decorator to ensure controller is initialized."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        global controller
        if controller is None:
            controller = run_async(DurgaController().initialize())
        return f(*args, **kwargs)
    return wrapper


# API Routes
@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'durga-controller'})


@app.route('/api/inbox', methods=['GET'])
@ensure_controller
def get_inbox():
    """Get inbox emails with clickable actions."""
    limit = request.args.get('limit', 20, type=int)
    result = run_async(controller.get_inbox_emails(limit))
    return jsonify(result)


@app.route('/api/inbox/<int:email_id>', methods=['GET'])
@ensure_controller
def get_email(email_id):
    """Get specific email with actions."""
    result = run_async(controller.get_email_detail(email_id))
    return jsonify(result)


@app.route('/api/inbox/reply', methods=['POST'])
@ensure_controller
def reply_email():
    """Reply to email."""
    data = request.get_json() or {}
    email_id = data.get('email_id', 1)
    message = data.get('message')
    use_ai = data.get('use_ai', False)
    template = data.get('template')

    result = run_async(controller.reply_to_email(email_id, message, use_ai, template))
    return jsonify(result)


@app.route('/api/inbox/refresh', methods=['POST'])
@ensure_controller
def refresh_inbox():
    """Refresh inbox."""
    result = run_async(controller.get_inbox_emails())
    return jsonify(result)


@app.route('/api/campaign/status', methods=['GET'])
@ensure_controller
def campaign_status():
    """Get campaign status."""
    result = run_async(controller.get_campaign_status())
    return jsonify(result)


@app.route('/api/campaign/create', methods=['POST'])
@ensure_controller
def create_campaign():
    """Create new campaign."""
    data = request.get_json() or {}
    result = run_async(controller.create_campaign(
        csv_path=data.get('csv_path'),
        company=data.get('company', ''),
        product=data.get('product', ''),
        goal=data.get('goal', 'customer_acquisition')
    ))
    return jsonify(result)


@app.route('/api/campaign/pause', methods=['POST'])
@ensure_controller
def pause_campaign():
    """Pause campaign."""
    result = run_async(controller.pause_campaign())
    return jsonify(result)


@app.route('/api/campaign/resume', methods=['POST'])
@ensure_controller
def resume_campaign():
    """Resume campaign."""
    result = run_async(controller.resume_campaign())
    return jsonify(result)


@app.route('/api/analytics', methods=['GET'])
@ensure_controller
def get_analytics():
    """Get analytics."""
    result = run_async(controller.get_analytics())
    return jsonify(result)


@app.route('/api/ask', methods=['POST'])
@ensure_controller
def ask_durga():
    """Natural language query with clickable actions."""
    data = request.get_json() or {}
    query = data.get('query', '')

    if not query:
        return jsonify({'success': False, 'error': 'Query required'})

    result = run_async(controller.process_natural_query(query))
    return jsonify(result)


if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║          Durga Controller - Browser Automation API        ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Endpoints:                                               ║
    ║    GET  /health              - Health check               ║
    ║    GET  /api/inbox           - Get inbox emails           ║
    ║    GET  /api/inbox/<id>      - Get specific email         ║
    ║    POST /api/inbox/reply     - Reply to email             ║
    ║    POST /api/inbox/refresh   - Refresh inbox              ║
    ║    GET  /api/campaign/status - Campaign status            ║
    ║    POST /api/campaign/create - Create campaign            ║
    ║    POST /api/campaign/pause  - Pause campaign             ║
    ║    POST /api/campaign/resume - Resume campaign            ║
    ║    GET  /api/analytics       - Get analytics              ║
    ║    POST /api/ask             - Natural language query     ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    app.run(host='0.0.0.0', port=3004, debug=False)
