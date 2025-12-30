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

# Persistent Context Path
USER_DATA_DIR = os.path.join(os.getcwd(), "browser_session")

try:
    from crawler.db_handler import DBHandler
    db = DBHandler()
except Exception:
    db = None

async def download_session(platform):
    """Download session from Supabase and extract to USER_DATA_DIR."""
    if not db: return
    session_json = db.load_session(platform)
    if session_json:
        # Playwright persistent context actually stores files. 
        # For simplicity, we'll store specific cookies/storage state if needed, 
        # but persistent_context directory is better. 
        # However, syncing a whole directory to DB is heavy.
        # We will use 'storage_state' instead which is a JSON file.
        state_path = os.path.join(USER_DATA_DIR, f"{platform}_state.json")
        os.makedirs(USER_DATA_DIR, exist_ok=True)
        with open(state_path, 'w', encoding='utf-8') as f:
            f.write(session_json)
        return state_path
    return None

async def upload_session(page, platform):
    """Save current browser state to Supabase."""
    if not db: return
    state_path = os.path.join(USER_DATA_DIR, f"{platform}_state.json")
    await page.context.storage_state(path=state_path)
    with open(state_path, 'r', encoding='utf-8') as f:
        db.save_session(platform, f.read())

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

async def login_instagram(page, username, password):
    """Handles Instagram login."""
    logger.info("Attempting Instagram login...")
    await page.goto("https://www.instagram.com/accounts/login/")
    await human_delay(3, 5)
    
    if await page.locator("input[name='username']").count() > 0:
        await page.locator("input[name='username']").fill(username)
        await page.locator("input[name='password']").fill(password)
        await page.locator("button[type='submit']").click()
        await human_delay(10, 15) # Wait for potential OTP or dashboard
        
    if "login" in page.url or await page.locator("button[type='submit']").count() > 0:
        logger.warning("Instagram needs verification or login failed.")
        return False
    return True


async def login_naver(page, username, password):
    """Handles Naver login including potential verification."""
    logger.info("Attempting Naver login...")
    await page.goto("https://nid.naver.com/nidlogin.login")
    await human_delay(2, 4)
    
    # Use evaluate to avoid bot detection for input
    await page.evaluate(f'document.getElementById("id").value="{username}"')
    await page.evaluate(f'document.getElementById("pw").value="{password}"')
    await page.locator(".btn_login").click()
    await human_delay(5, 10)
    
    if "nidlogin.login" in page.url:
        logger.warning("Naver login verification required! Check your phone.")
        # Wait for user to confirm on phone or enter code if we had a UI
        # For now, we wait up to 60s for the URL to change
        for _ in range(12):
            await asyncio.sleep(5)
            if "nidlogin.login" not in page.url:
                return True
        return False
    return True

async def login_instagram(page, username, password):
    """Handles Instagram login."""
    logger.info("Attempting Instagram login...")
    await page.goto("https://www.instagram.com/accounts/login/")
    await human_delay(3, 5)
    
    if await page.locator("input[name='username']").count() > 0:
        await page.locator("input[name='username']").fill(username)
        await page.locator("input[name='password']").fill(password)
        await page.locator("button[type='submit']").click()
        await human_delay(10, 15) # Wait for potential OTP or dashboard
        
    if "login" in page.url or await page.locator("button[type='submit']").count() > 0:
        logger.warning("Instagram needs verification or login failed.")
        return False
    return True

async def main(target_list_json, message, method="both", naver_creds=None, insta_creds=None):
    """
    Args:
        target_list_json: JSON string of shops to message
        message: The message body
        method: 'talk', 'insta', or 'both'
        naver_creds: (user, pw)
        insta_creds: (user, pw)
    """
    targets = json.loads(target_list_json)
    is_cloud = os.path.exists("/mount/src")
    logger.info(f"Starting auto-messenger. Cloud: {is_cloud}, Targets: {len(targets)}, Method: {method}")
    
    async with async_playwright() as p:
        # Load existing sessions if available
        n_state = await download_session("naver")
        i_state = await download_session("insta")
        
        # Launch browser
        browser = await p.chromium.launch(headless=is_cloud)
        
        # Determine which state to load for the primary navigation
        # Note: Playwright contexts are per-browser. 
        # For 'both' mode, we'll use naver state as base if available.
        base_state = n_state if n_state else i_state
        
        context_args = {
            "viewport": {'width': 1280, 'height': 800},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        if base_state:
            context_args["storage_state"] = base_state

        context = await browser.new_context(**context_args)
        page = await context.new_page()

        # Step 1: Login Check/Perform
        if method in ["talk", "both"] and naver_creds:
            n_user, n_pw = naver_creds
            if await login_naver(page, n_user, n_pw):
                await upload_session(page, "naver")
        
        if method in ["insta", "both"] and insta_creds:
            i_user, i_pw = insta_creds
            if await login_instagram(page, i_user, i_pw):
                await upload_session(page, "insta")

        for idx, shop in enumerate(targets):
            logger.info(f"[{idx+1}/{len(targets)}] Targeting: {shop['상호명']}")
            success = False
            
            # --- Naver TalkTalk ---
            if method in ["talk", "both"] and shop.get('톡톡링크'):
                # Ensure we are logged in - simple check
                success = await send_talktalk_message(page, shop['톡톡링크'], message)
            
            # --- Instagram DM ---
            if method == "insta" or (method == "both" and not success):
                if shop.get('인스타'):
                    success = await send_instagram_dm(page, shop['인스타'], message)
            
            if success:
                wait_time = random.uniform(60, 120) 
                logger.info(f"Waiting {wait_time:.1f}s before next send...")
                await asyncio.sleep(wait_time)
            else:
                logger.warning(f"Failed to send to {shop['상호명']} via {method}")
                await human_delay(5, 10)
                
        await browser.close()
        logger.info("Auto-messenger task complete.")

if __name__ == "__main__":
    import json
    # Usage: python safe_messenger.py targets_json message method [naver_u:p] [insta_u:p]
    if len(sys.argv) < 3:
        print("Usage: python safe_messenger.py '<json_targets>' 'message' [method] [naver_u:p] [insta_u:p]")
        sys.exit(1)
        
    targets_json = sys.argv[1]
    msg = sys.argv[2]
    send_method = sys.argv[3] if len(sys.argv) > 3 else "both"
    
    n_creds = None
    if len(sys.argv) > 4 and ":" in sys.argv[4]:
        n_creds = tuple(sys.argv[4].split(":", 1))
        
    i_creds = None
    if len(sys.argv) > 5 and ":" in sys.argv[5]:
        i_creds = tuple(sys.argv[5].split(":", 1))
    
    asyncio.run(main(targets_json, msg, send_method, n_creds, i_creds))
