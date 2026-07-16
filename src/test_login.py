"""
Test Login Script

A standalone script to test Instagram login functionality.
Use this to debug login issues without running the full scraper.
"""

import os
import logging
from dotenv import load_dotenv
from utils import setup_driver, instagram_login

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Test Instagram login."""
    # Get credentials
    username = os.getenv('INSTAGRAM_USERNAME')
    password = os.getenv('INSTAGRAM_PASSWORD')
    
    if not username or not password:
        logger.error("INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD must be set in .env file")
        logger.info("Please create a .env file with:")
        logger.info("INSTAGRAM_USERNAME=your_username")
        logger.info("INSTAGRAM_PASSWORD=your_password")
        return
    
    logger.info("=" * 60)
    logger.info("Instagram Login Test")
    logger.info("=" * 60)
    logger.info(f"Username: {username}")
    logger.info(f"Password: {'*' * len(password)}")
    logger.info("=" * 60)
    
    # Setup driver (non-headless so you can see what's happening)
    logger.info("Setting up Chrome driver...")
    driver = setup_driver(headless=False, slow_mode=0)
    
    try:
        # Test login
        logger.info("Attempting to log in...")
        success = instagram_login(driver, username, password, slow_mode=2)
        
        if success:
            logger.info("=" * 60)
            logger.info("✓ LOGIN SUCCESSFUL!")
            logger.info("=" * 60)
            logger.info("You can now close the browser manually or wait 30 seconds...")
            import time
            time.sleep(30)
        else:
            logger.error("=" * 60)
            logger.error("✗ LOGIN FAILED")
            logger.error("=" * 60)
            logger.error("Check the screenshots and logs for details:")
            logger.error("- login_error_*.png (screenshots)")
            logger.error("- login_page_source.html (page HTML)")
            logger.error("- Check the browser window for error messages")
            logger.error("=" * 60)
            logger.info("Keeping browser open for 60 seconds so you can inspect...")
            import time
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        driver.quit()
        logger.info("Browser closed")


if __name__ == "__main__":
    main()

