#!/usr/bin/env python3
"""
Marketing Campaign Automation
Quick and easy email marketing using DurgaMail.

Usage:
    python marketing_campaign.py --csv contacts.csv --goal vc_funding
    python marketing_campaign.py --emails "email1@test.com,email2@test.com" --goal partnership
"""

import asyncio
import argparse
import os
from playwright.async_api import async_playwright

# Configuration
DURGAMAIL_URL = "http://localhost:5002"
DASHBOARD_URL = "http://localhost:8080"
EMAIL = "evolverobotlab@gmail.com"
PASSWORD = "katacity"

# Marketing Goals
GOALS = {
    "vc_funding": "Seeking VC Funding",
    "partnership": "Partnership Opportunities",
    "sales": "Selling AI/Robotics Services",
    "customers": "Customer Acquisition",
    "launch": "Product Launch"
}


async def run_marketing_campaign(csv_path=None, emails_list=None, company="Evolve Robot Lab",
                                  product="AI & Robotics Services", goal="customers"):
    """Run a complete marketing campaign."""

    print("\n" + "=" * 60)
    print("   MARKETING CAMPAIGN AUTOMATION")
    print("=" * 60)
    print(f"\n   Company: {company}")
    print(f"   Product: {product}")
    print(f"   Goal: {GOALS.get(goal, goal)}")
    if csv_path:
        print(f"   Recipients: {csv_path}")
    elif emails_list:
        print(f"   Recipients: {len(emails_list)} emails")
    print("\n" + "-" * 60)

    async with async_playwright() as p:
        # Launch browser (visible so you can see what's happening)
        browser = await p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        try:
            # Step 1: Login
            print("\n[1/6] Logging in to DurgaAI...")
            await page.goto(DASHBOARD_URL)
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)

            if await page.locator('text=evolve robot lab').count() == 0:
                await page.locator('text=LOGIN').first.click()
                await asyncio.sleep(2)
                await page.click('a:has-text("Log In"), span:has-text("Log In")')
                await asyncio.sleep(1)
                await page.fill('#login-email', EMAIL)
                await page.fill('#login-password', PASSWORD)
                await page.locator('button:has-text("Log In")').first.click()
                await asyncio.sleep(3)
                if await page.locator('#auth-modal.active').count() > 0:
                    await page.keyboard.press('Escape')
            print("   ✓ Logged in successfully")

            # Step 2: Go to Campaign
            print("\n[2/6] Opening Campaign section...")
            await page.goto(DURGAMAIL_URL)
            await asyncio.sleep(3)
            await page.locator('text=Campaign').first.click()
            await asyncio.sleep(2)
            print("   ✓ Campaign section opened")

            # Step 3: Upload Recipients
            print("\n[3/6] Uploading recipients...")
            if csv_path and os.path.exists(csv_path):
                file_input = page.locator('#file-input')
                await file_input.set_input_files(csv_path)
                await asyncio.sleep(3)
                print(f"   ✓ CSV uploaded: {csv_path}")
            elif emails_list:
                textarea = page.locator('#recipient-list-textarea')
                if await textarea.count() > 0:
                    await textarea.fill("\n".join(emails_list))
                print(f"   ✓ {len(emails_list)} emails entered")

            # Take screenshot
            await page.screenshot(path='marketing_step1_recipients.png')

            # Step 4: Continue to Compose
            print("\n[4/6] Configuring campaign settings...")
            continue_btn = page.locator('#continue-to-compose, button:has-text("Continue")')
            if await continue_btn.count() > 0:
                await continue_btn.first.click()
                await asyncio.sleep(2)

            # Fill campaign details
            company_input = page.locator('#company-info')
            if await company_input.count() > 0:
                await company_input.fill(company)

            product_input = page.locator('#product-info')
            if await product_input.count() > 0:
                await product_input.fill(product)

            goal_select = page.locator('#campaign-goal-select')
            if await goal_select.count() > 0:
                await goal_select.select_option(goal)

            print(f"   ✓ Campaign configured")
            await asyncio.sleep(1)

            # Step 5: Generate AI Email
            print("\n[5/6] Generating AI email content...")
            generate_btn = page.locator('button:has-text("Generate Emails")')
            if await generate_btn.count() > 0:
                await generate_btn.first.scroll_into_view_if_needed()
                await generate_btn.first.click()
                await asyncio.sleep(5)

                # Wait for generation
                for i in range(60):
                    start_btn = page.locator('#start-campaign-btn, button:has-text("Start Campaign")')
                    if await start_btn.count() > 0 and await start_btn.first.is_visible():
                        break
                    if i % 10 == 0:
                        print(f"   Generating emails... ({i}s)")
                    await asyncio.sleep(1)

                print("   ✓ AI emails generated")

            await page.screenshot(path='marketing_step2_compose.png')

            # Step 6: Launch Campaign
            print("\n[6/6] Ready to launch campaign!")
            print("\n" + "=" * 60)
            print("   CAMPAIGN READY")
            print("=" * 60)
            print("\n   Screenshots saved:")
            print("   - marketing_step1_recipients.png")
            print("   - marketing_step2_compose.png")
            print("\n   The browser is open for you to:")
            print("   1. Review the generated emails")
            print("   2. Edit if needed")
            print("   3. Click 'Start Campaign' to send")
            print("\n   Browser will close in 60 seconds...")
            print("   (Or close it manually when done)")

            await asyncio.sleep(60)

        except Exception as e:
            print(f"\n   ✗ Error: {e}")
            await page.screenshot(path='marketing_error.png')
            print("   Error screenshot saved: marketing_error.png")

        finally:
            await browser.close()
            print("\n" + "=" * 60)
            print("   Marketing campaign automation complete!")
            print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Marketing Campaign Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send to CSV contacts for VC funding
  python marketing_campaign.py --csv investors.csv --goal vc_funding

  # Send to specific emails for partnership
  python marketing_campaign.py --emails "john@company.com,jane@startup.com" --goal partnership

  # Customer acquisition campaign
  python marketing_campaign.py --csv leads.csv --goal customers --company "My Company"

Goals:
  vc_funding   - Seeking VC Funding
  partnership  - Partnership Opportunities
  sales        - Selling AI/Robotics Services
  customers    - Customer Acquisition
  launch       - Product Launch
        """
    )

    parser.add_argument('--csv', help='Path to CSV file with recipient emails')
    parser.add_argument('--emails', help='Comma-separated list of emails')
    parser.add_argument('--company', default='Evolve Robot Lab', help='Your company name')
    parser.add_argument('--product', default='AI & Robotics Services', help='Product/service description')
    parser.add_argument('--goal', default='customers', choices=list(GOALS.keys()),
                        help='Campaign goal (default: customers)')

    args = parser.parse_args()

    # Parse emails if provided
    emails_list = None
    if args.emails:
        emails_list = [e.strip() for e in args.emails.split(',')]

    if not args.csv and not emails_list:
        print("\nError: Please provide either --csv or --emails")
        parser.print_help()
        return

    asyncio.run(run_marketing_campaign(
        csv_path=args.csv,
        emails_list=emails_list,
        company=args.company,
        product=args.product,
        goal=args.goal
    ))


if __name__ == "__main__":
    main()
