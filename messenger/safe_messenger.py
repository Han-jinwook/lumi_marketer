import asyncio
import random
import logging
import os
import sys
from playwright.async_api import async_playwright

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Persistent Context Path (Where login sessions are stored)
USER_DATA_DIR = os.path.join(os.getcwd(), "browser_session")

async def human_delay(min_sec=2, max_sec=5):
    """Realistic human-like delay."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def slow_type(element, text):
    """Type text slowly, like a human."""
    for char in text:
        await element.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.2))

async def send_talktalk_message(page, talk_url, message):
    """Automates sending a Naver TalkTalk message."""
    logger.info(f"Opening TalkTalk: {talk_url}")
    await page.goto(talk_url, wait_until="networkidle")
    await human_delay(3, 6)
    
    # 1. Look for the message input area
    # Note: Selector might change, using common ones for TalkTalk
    input_selector = "textarea, div[contenteditable='true'], .chat_input_area"
    input_area = page.locator(input_selector).first
    
    if await input_area.count() > 0:
        await input_area.click()
        await human_delay(1, 2)
        await slow_type(input_area, message)
        await human_delay(1, 2)
        
        # 2. Look for the send button
        send_btn = page.locator("button:has-text('전송'), button.btn_send").first
        if await send_btn.count() > 0:
            await send_btn.click()
            logger.info("TalkTalk Message Sent!")
            return True
        else:
            logger.error("Could not find TalkTalk send button")
    else:
        logger.error("Could not find TalkTalk input area. Is the user logged in?")
    return False

async def send_instagram_dm(page, insta_url, message):
    """Automates sending an Instagram DM."""
    logger.info(f"Opening Instagram: {insta_url}")
    await page.goto(insta_url, wait_until="networkidle")
    await human_delay(4, 7)
    
    # 1. Click "Message" button on profile
    msg_btn = page.locator("div[role='button']:has-text('메시지 보내기'), button:has-text('Message')").first
    if await msg_btn.count() > 0:
        await msg_btn.click()
        logger.info("Clicked message button, waiting for chat to load...")
        await human_delay(5, 8)
        
        # 2. Look for the chat input
        chat_input = page.locator("div[role='textbox'][aria-label*='메시지'], textarea[placeholder*='메시지']").first
        if await chat_input.count() > 0:
            await chat_input.click()
            await human_delay(1, 2)
            await slow_type(chat_input, message)
            await human_delay(1, 2)
            
            # Press Enter to send or find send button
            await chat_input.press("Enter")
            logger.info("Instagram DM Sent!")
            return True
        else:
            logger.error("Could not find Instagram chat input.")
    else:
        logger.error("Could not find Instagram 'Message' button. Private account?")
    return False

async def main(target_list_json, message):
    """
    Args:
        target_list_json: JSON string of shops to message
        message: The message body
    """
    targets = json.loads(target_list_json)
    logger.info(f"Starting auto-messenger for {len(targets)} targets.")
    
    async with async_playwright() as p:
        # Launch with persistent context
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False, # Show browser for visibility/login first time
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        for idx, shop in enumerate(targets):
            logger.info(f"[{idx+1}/{len(targets)}] Targeting: {shop['상호명']}")
            
            success = False
            # Try TalkTalk first if available
            if shop.get('톡톡링크'):
                success = await send_talktalk_message(page, shop['톡톡링크'], message)
            
            # If TalkTalk failed or not available, try Instagram
            if not success and shop.get('인스타'):
                success = await send_instagram_dm(page, shop['인스타'], message)
            
            if success:
                # LONG delay between successful sends to avoid detection
                wait_time = random.uniform(60, 120) 
                logger.info(f"Waiting {wait_time:.1f}s before next send...")
                await asyncio.sleep(wait_time)
            else:
                logger.warning(f"Failed to send to {shop['상호명']}")
                await human_delay(5, 10)
                
        await context.close()
        logger.info("Auto-messenger task complete.")

if __name__ == "__main__":
    import json
    if len(sys.argv) < 3:
        print("Usage: python safe_messenger.py '<json_targets>' 'message'")
        sys.exit(1)
        
    targets_json = sys.argv[1]
    msg = sys.argv[2]
    
    asyncio.run(main(targets_json, msg))
