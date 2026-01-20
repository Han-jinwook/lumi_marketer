import asyncio
import logging
from step1_refined_crawler import run_crawler

# Setup Logging to console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    print("🚀 Starting diagnosis for Gangnam-gu...")
    # Run crawler for a small count (e.g., 3) to see what happens
    # refine_crawler.run_crawler accepts (target_area, count)
    try:
        await run_crawler("강남구", 3)
    except Exception as e:
        print(f"❌ Error during diagnosis: {e}")

if __name__ == "__main__":
    asyncio.run(main())
