import csv
import os
import logging
from typing import Dict

try:
    from .. import config
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import config

logger = logging.getLogger(__name__)

class CSVHandler:
    def __init__(self, filename: str = config.OUTPUT_CSV):
        self.filename = filename
        self.initialize_csv()
        
    def initialize_csv(self):
        """Create CSV file with headers if it doesn't exist."""
        if not os.path.exists(self.filename):
            try:
                with open(self.filename, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    # Header: Blog URL, Blog Title, Email
                    writer.writerow(["블로그 URL", "블로그 제목", "이메일"])
                logger.info(f"Created new CSV file: {self.filename}")
            except Exception as e:
                logger.error(f"Failed to create CSV file: {e}")

    def append_data(self, data: Dict[str, str]):
        """Append a single row of data to the CSV."""
        try:
            with open(self.filename, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow([
                    data.get("blog_url", ""),
                    data.get("title", ""),
                    data.get("email", "")
                ])
            logger.info(f"Appended to CSV: {data.get('blog_url')}")
        except Exception as e:
            logger.error(f"Failed to write to CSV: {e}")
