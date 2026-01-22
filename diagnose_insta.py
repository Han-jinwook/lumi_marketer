import asyncio
import os
import sys
import logging
from playwright.async_api import async_playwright

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_diagnostic(target_url):
    async with async_playwright() as p:
        # We'll run in non-headless mode to see what's happening if possible, 
        # but since I'm an AI, I'll use screenshots.
        browser = await p.chromium.launch(headless=True)
        
        # Use a persistent context to simulate the user's session if it exists
        user_data_dir = os.path.join(os.getcwd(), "browser_session_diag")
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        logger.info(f"Navigating to {target_url}...")
        await page.goto(target_url, wait_until="networkidle")
        await asyncio.sleep(5)
        
        # Take a screenshot to see current state
        await page.screenshot(path="debug_insta_profile.png")
        logger.info("Saved profile screenshot to debug_insta_profile.png")
        
        # Check for 'Message' button
        msg_btn_selectors = [
            "div[role='button']:has-text('메시지 보내기')",
            "button:has-text('Message')",
            "div[role='button']:has-text('Message')",
            "//div[contains(text(), '메시지 보내기')]",
            "//button[contains(text(), 'Message')]"
        ]
        
        found_btn = None
        for selector in msg_btn_selectors:
            count = await page.locator(selector).count()
            if count > 0:
                logger.info(f"Found Message button with selector: {selector}")
                found_btn = page.locator(selector).first
                break
        
        if not found_btn:
            logger.error("Could not find Message button. Private account or different UI?")
            # Try to list all buttons to see what's there
            buttons = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('button, div[role="button"]')).map(b => b.innerText);
            }''')
            logger.info(f"Found buttons/roles: {buttons}")
        else:
            logger.info("Clicking Message button...")
            await found_btn.click()
            await asyncio.sleep(8)
            await page.screenshot(path="debug_insta_chat.png")
            logger.info("Saved chat screenshot to debug_insta_chat.png")
            
            # Check for chat input
            input_selectors = [
                "div[role='textbox'][aria-label*='메시지']",
                "textarea[placeholder*='메시지']",
                "div[role='textbox'][aria-label*='Message']",
                "textarea[placeholder*='Message']"
            ]
            
            found_input = None
            for selector in input_selectors:
                count = await page.locator(selector).count()
                if count > 0:
                    logger.info(f"Found Chat input with selector: {selector}")
                    found_input = page.locator(selector).first
                    break
            
            if not found_input:
                logger.error("Could not find Chat input.")
                # Try to list textboxes
                textboxes = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('div[role="textbox"], textarea')).map(b => b.getAttribute('aria-label') || b.placeholder);
                }''')
                logger.info(f"Found textboxes/placeholders: {textboxes}")
            else:
                logger.info("Found Chat input successfully.")
                
        await browser.close()

if __name__ == "__main__":
    # Test with a public profile first to check selectors
    target = "https://www.instagram.com/zuck/" 
    asyncio.run(run_diagnostic(target))
