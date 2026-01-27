import asyncio
import os
import sys
from step1_refined_crawler import run_crawler
from extract_competitors import run_competitor_extraction

async def main():
    print("🚀 Starting manual recovery for Jung-gu and Jungnang-gu...")
    # These were the districts being processed when it crashed
    # We can just run a 'resume' of '서울' and it will check the checkpoint
    # But let's be more specific if we want to be fast, or just use the resume logic.
    
    # Actually, the best way to verify the new logic is to use it!
    # I'll manually create a checkpoint at the district before Jung-gu if needed, 
    # but the log showed it was already in Jung-gu/Jungnang-gu.
    
    await run_crawler("서울", 99999, resume=True)
    
    print("🎯 Crawling finished. Running final competitor extraction...")
    run_competitor_extraction()
    print("✅ Recovery complete!")

if __name__ == "__main__":
    asyncio.run(main())
