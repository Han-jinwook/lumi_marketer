import schedule
import time
import logging
import subprocess
import os
from datetime import datetime

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - SCHEDULER - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_crawler():
    logger.info("Starting scheduled crawl job...")
    try:
        # Run main.py using the same python interpreter
        result = subprocess.run(["py", "main.py"], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Crawl job finished successfully.")
            logger.info(f"Output: {result.stdout[-200:]}...") # Log last 200 chars
        else:
            logger.error(f"Crawl job failed with code {result.returncode}")
            logger.error(f"Error: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Failed to run crawl job: {e}")

def main():
    logger.info("Scheduler started. The crawler will run every 6 hours.")
    
    # Run immediately on start
    run_crawler()
    
    # Schedule every 6 hours
    schedule.every(6).hours.do(run_crawler)
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60) # Check every minute

if __name__ == "__main__":
    main()
