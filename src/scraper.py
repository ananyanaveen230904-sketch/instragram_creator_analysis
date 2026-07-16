"""
Instagram Engagement Scraper - Phase 2

Main script that:
1. Searches Instagram for a keyword
2. Collects post URLs from search results
3. For each post that passes Phase-1 criteria:
   - Opens creator's profile
   - Fetches their latest N posts
   - Analyzes each post (comment extraction + classification + EQS)
4. Generates creator-level summaries
5. Saves results to posts.csv and creators.csv
"""

import os
import sys
import time
import random
import logging
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException
)
from dotenv import load_dotenv

# Import from local modules
from utils import (
    load_config,
    setup_driver,
    instagram_login,
    scroll_and_collect_comments,
    extract_creator_handle,
    save_posts_csv,
    save_creators_csv,
    save_raw_comments
)
from post_analyzer import analyze_post
from creator_analyzer import fetch_creator_posts, aggregate_creator_stats
from comment_classifier import classify_comment

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('instagram_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def search_instagram(driver, keyword, num_posts, slow_mode=0):
    """
    Improved Instagram search:
    - Loads hashtag page
    - Scrolls reliably
    - Collects unique post URLs
    """

    post_urls = set()
    scroll_pause = random.uniform(2, 3) + slow_mode
    max_scrolls = 50  # Increased scroll attempts
    scroll_count = 0

    try:
        hashtag_url = f"https://www.instagram.com/explore/tags/{keyword}/"
        logger.info(f"Opening hashtag page: {hashtag_url}")
        driver.get(hashtag_url)

        time.sleep(5 + slow_mode)

        # Ensure page loads fully
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
        except:
            logger.warning("Article not found, still continuing...")

        logger.info(f"Collecting up to {num_posts} post URLs...")

        while len(post_urls) < num_posts and scroll_count < max_scrolls:

            # Try multiple selectors
            xpaths = [
                "//a[contains(@href, '/p/')]",
                "//a[contains(@href, '/reel/')]",
                "//article//a",
                "//div[@role='presentation']//a[contains(@href, '/')]"
            ]

            links = []
            for xp in xpaths:
                try:
                    elements = driver.find_elements(By.XPATH, xp)
                    links.extend(elements)
                except:
                    continue

            # Extract valid URLs
            for link in links:
                try:
                    url = link.get_attribute("href")
                    if not url:
                        continue

                    url = url.split('?')[0]  # Clean URL
                    if "/p/" in url or "/reel/" in url:
                        post_urls.add(url)

                    if len(post_urls) >= num_posts:
                        break

                except:
                    continue

            # Log progress
            logger.info(f"Collected: {len(post_urls)} URLs (scrolls: {scroll_count})")

            # Scroll down
            driver.execute_script("window.scrollBy(0, 1500);")
            time.sleep(scroll_pause)

            scroll_count += 1

        logger.info(f"Final unique URLs collected: {len(post_urls)}")
        return list(post_urls)[:num_posts]

    except Exception as e:
        logger.error(f"Error in search_instagram: {e}", exc_info=True)
        return list(post_urls)


def process_post_phase1(driver, post_url, min_comments, min_text_percentage, slow_mode=0):
    """
    Process a single Instagram post for Phase-1 criteria check.
    Returns basic metrics to determine if we should analyze the creator.
    
    Args:
        driver: Selenium WebDriver instance
        post_url (str): URL of the post to process
        min_comments (int): Minimum required comments for qualification
        min_text_percentage (float): Minimum text-based percentage required
        slow_mode (int): Additional delay in seconds
        
    Returns:
        dict: Result dictionary with post metrics and creator handle
    """
    result = {
        'creator_handle': '',
        'post_url': post_url,
        'total_comments': 0,
        'text_percentage': 0.0,
        'emoji_percentage': 0.0,
        'mixed_percentage': 0.0,
        'passes_phase1': False
    }
    
    try:
        logger.info(f"Processing post for Phase-1 check: {post_url}")
        
        # Navigate to post
        driver.get(post_url)
        time.sleep(3 + slow_mode)
        
        # Extract creator handle
        result['creator_handle'] = extract_creator_handle(driver)
        
        if not result['creator_handle']:
            logger.warning(f"Could not extract creator handle from post: {post_url}")
            return result
        
        # Click on comments to open comments section (if needed)
        try:
            comment_selectors = [
                "//span[contains(text(), 'comment') and not(contains(text(), 'comments'))]/ancestor::button",
                "//a[contains(@href, '/p/')]//span[contains(text(), 'comment')]",
                "//button[contains(@aria-label, 'comment')]",
                "//span[contains(text(), 'comment')]/ancestor::a",
                "//article//span[contains(text(), 'comment')]",
            ]
            
            comment_opened = False
            for selector in comment_selectors:
                try:
                    comment_element = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if comment_element.is_displayed():
                        driver.execute_script("arguments[0].click();", comment_element)
                        time.sleep(2 + slow_mode)
                        comment_opened = True
                        logger.info("Opened comments section")
                        break
                except:
                    continue
            
            if not comment_opened:
                logger.info("Comments section may already be visible or will be extracted from page")
        except Exception as e:
            logger.warning(f"Could not open comments section explicitly: {e}. Will try to extract from page.")
        
        # Collect comments
        comments = scroll_and_collect_comments(driver, max_scroll_attempts=10, slow_mode=slow_mode)
        result['total_comments'] = len(comments)

        # Persist raw comments for later offline analysis (e.g. sentiment classification)
        save_raw_comments(result['creator_handle'], post_url, comments)
        
        if result['total_comments'] == 0:
            logger.warning(f"No comments found for post: {post_url}")
            return result
        
        # Quick classification for Phase-1 check
        text_count = 0
        emoji_count = 0
        mixed_count = 0
        
        for comment in comments:
            classification = classify_comment(comment)
            if classification == "text":
                text_count += 1
            elif classification == "emoji":
                emoji_count += 1
            elif classification == "mixed":
                mixed_count += 1
        
        # Calculate percentages
        total = len(comments)
        result['text_percentage'] = round((text_count / total) * 100, 2)
        result['emoji_percentage'] = round((emoji_count / total) * 100, 2)
        result['mixed_percentage'] = round((mixed_count / total) * 100, 2)

        
        # >>> ADD THIS
        logger.info(
            f"[Phase-1] Text %: {result['text_percentage']}% | "
            f"Emoji %: {result['emoji_percentage']}% | "
            f"Mixed %: {result['mixed_percentage']}%"
        )


        
        # Check Phase-1 criteria
        text_based_count = text_count + mixed_count
        text_based_percentage = (text_based_count / total) * 100
        
        if result['total_comments'] >= min_comments and text_based_percentage >= min_text_percentage:
            result['passes_phase1'] = True
            logger.info(
                f"Post PASSES Phase-1: {result['total_comments']} comments, "
                f"{text_based_percentage:.2f}% text-based, Creator: {result['creator_handle']}"
            )
        else:
            logger.info(
                f"Post FAILS Phase-1: {result['total_comments']} comments, "
                f"{text_based_percentage:.2f}% text-based"
            )
        
        return result
        
    except TimeoutException:
        logger.error(f"Timeout while processing post: {post_url}")
        return result
    except Exception as e:
        logger.error(f"Error processing post {post_url}: {e}")
        return result


def process_post_full_analysis(driver, post_url, creator_handle, min_comments, min_text_percentage, slow_mode=0):
    """
    Process a single Instagram post with full analysis (EQS calculation).
    
    Args:
        driver: Selenium WebDriver instance
        post_url (str): URL of the post to process
        creator_handle (str): Creator's handle
        min_comments (int): Minimum required comments
        min_text_percentage (float): Minimum text-based percentage required
        slow_mode (int): Additional delay in seconds
        
    Returns:
        dict: Complete post analysis results
    """
    result = {
        'creator_handle': creator_handle,
        'post_url': post_url,
        'total_comments': 0,
        'text_percentage': 0.0,
        'emoji_percentage': 0.0,
        'mixed_percentage': 0.0,
        'unique_commenters_ratio': 0.0,
        'EQS': 0.0,
        'pass': 'Fail'
    }
    
    try:
        logger.info(f"Full analysis of post: {post_url} (Creator: {creator_handle})")
        
        # Navigate to post
        driver.get(post_url)
        time.sleep(3 + slow_mode)
        
        # Click on comments to open comments section (if needed)
        try:
            comment_selectors = [
                "//span[contains(text(), 'comment') and not(contains(text(), 'comments'))]/ancestor::button",
                "//a[contains(@href, '/p/')]//span[contains(text(), 'comment')]",
                "//button[contains(@aria-label, 'comment')]",
                "//span[contains(text(), 'comment')]/ancestor::a",
                "//article//span[contains(text(), 'comment')]",
            ]
            
            comment_opened = False
            for selector in comment_selectors:
                try:
                    comment_element = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    if comment_element.is_displayed():
                        driver.execute_script("arguments[0].click();", comment_element)
                        time.sleep(2 + slow_mode)
                        comment_opened = True
                        break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Could not open comments section explicitly: {e}")
        
        # Collect comments
        # Collect comments
        comments = scroll_and_collect_comments(driver, max_scroll_attempts=15, slow_mode=slow_mode)

        # Persist raw comments for later offline analysis (e.g. sentiment classification)
        save_raw_comments(creator_handle, post_url, comments)
        
        if not comments:
            logger.warning(f"No comments found for post: {post_url}")
            return result
        
        # Full analysis using post_analyzer
        analysis = analyze_post(comments, min_comments, min_text_percentage)
        
        # Merge results
        result.update(analysis)
        result['creator_handle'] = creator_handle
        result['post_url'] = post_url
        
        
        logger.info(
            f"[Phase-2] Text %: {result['text_percentage']}% | "
            f"Emoji %: {result['emoji_percentage']}% | "
            f"Mixed %: {result['mixed_percentage']}%"
        )
        logger.info(f"[Phase-2] EQS: {result['EQS']} | Pass: {result['pass']}")

        return result
        
    except Exception as e:
        logger.error(f"Error in full analysis of post {post_url}: {e}", exc_info=True)
        return result


def process_creator(driver, creator_handle, posts_per_creator, scroll_delay_range,
                    min_comments, min_text_percentage, slow_mode=0):
    """
    Process a creator: fetch their posts and analyze each one.
    
    Args:
        driver: Selenium WebDriver instance
        creator_handle (str): Creator's Instagram handle
        posts_per_creator (int): Number of posts to analyze per creator
        scroll_delay_range (list): [min, max] delay range for scrolling
        min_comments (int): Minimum required comments
        min_text_percentage (float): Minimum text-based percentage required
        slow_mode (int): Additional delay in seconds
        
    Returns:
        list: List of post analysis results
    """
    post_results = []
    
    try:
        logger.info(f"Processing creator: {creator_handle}")
        
        # Fetch creator's posts
        creator_post_urls = fetch_creator_posts(
            driver, creator_handle, posts_per_creator, scroll_delay_range, slow_mode
        )
        
        if not creator_post_urls:
            logger.warning(f"No posts found for creator: {creator_handle}")
            return post_results
        
        logger.info(f"Found {len(creator_post_urls)} posts for creator: {creator_handle}")
        
        # Analyze each post
        for post_url in creator_post_urls:
            result = process_post_full_analysis(
                driver, post_url, creator_handle, min_comments, min_text_percentage, slow_mode
            )
            post_results.append(result)
            
            # Random delay between posts
            time.sleep(random.uniform(3, 5) + slow_mode)
        
        logger.info(f"Completed analysis of {len(post_results)} posts for creator: {creator_handle}")
        
    except Exception as e:
        logger.error(f"Error processing creator {creator_handle}: {e}", exc_info=True)
    
    return post_results


def main():
    """Main execution function."""
    try:
        # Load configuration
        # Path relative to project root (when running from src/)
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'config.yaml')
        config = load_config(config_path)
        
        keyword = config.get('keyword', 'lifestyle')
        num_initial_posts = config.get('number_of_initial_posts_to_scan', 20)
        posts_per_creator = config.get('posts_per_creator', 5)
        min_comments = config.get('minimum_comments_required', 50)
        min_text_percentage = config.get('minimum_text_percentage_required', 50)
        scroll_delay_range = config.get('scroll_delay_range', [2, 4])
        browser_config = config.get('browser', {})
        headless = browser_config.get('headless', False)
        slow_mode = browser_config.get('slow_mode', 2)
        output_config = config.get('output', {})
        # Make output paths relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        posts_csv = output_config.get('posts_csv', 'output/posts.csv')
        creators_csv = output_config.get('creators_csv', 'output/creators.csv')
        # Convert to absolute paths if relative
        if not os.path.isabs(posts_csv):
            posts_csv = os.path.join(project_root, posts_csv)
        if not os.path.isabs(creators_csv):
            creators_csv = os.path.join(project_root, creators_csv)
        
        # Get credentials from config or environment
        login_config = config.get('login', {})
        username = login_config.get('username') or os.getenv('INSTAGRAM_USERNAME')
        password = login_config.get('password') or os.getenv('INSTAGRAM_PASSWORD')
        
        if not username or not password:
            logger.error("INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD must be set in config.yaml or .env file")
            return
        
        # Setup driver
        driver = setup_driver(headless=headless, slow_mode=slow_mode)
        
        try:
            # Login to Instagram
            logger.info("Attempting to log into Instagram...")
            if not instagram_login(driver, username, password, slow_mode=slow_mode):
                logger.error("=" * 60)
                logger.error("LOGIN FAILED - Please check the following:")
                logger.error("=" * 60)
                logger.error("1. Verify your credentials in config.yaml or .env file")
                logger.error("2. Check for screenshots: login_error_*.png")
                logger.error("3. Check page source: login_page_source.html")
                logger.error("=" * 60)
                if not headless:
                    logger.info("Browser will stay open for 30 seconds for inspection...")
                    time.sleep(30)
                return
            
            # Phase 1: Search and collect initial post URLs
            logger.info("=" * 60)
            logger.info("PHASE 1: Searching for posts that pass initial criteria")
            logger.info("=" * 60)
            post_urls = search_instagram(driver, keyword, num_initial_posts, slow_mode=slow_mode)
            
            if not post_urls:
                logger.error("No posts found. Exiting.")
                return
            
            # Phase 1: Check each post for Phase-1 criteria
            logger.info("=" * 60)
            logger.info("PHASE 1: Checking posts for Phase-1 criteria")
            logger.info("=" * 60)
            
            creators_to_analyze = {}  # {creator_handle: initial_post_url}
            
            with tqdm(total=len(post_urls), desc="Phase-1: Checking posts") as pbar:
                for post_url in post_urls:
                    phase1_result = process_post_phase1(
                        driver, post_url, min_comments, min_text_percentage, slow_mode
                    )
                    
                    if phase1_result['passes_phase1']:
                        creator_handle = phase1_result['creator_handle']
                        if creator_handle and creator_handle not in creators_to_analyze:
                            creators_to_analyze[creator_handle] = post_url
                            logger.info(f"Creator added for Phase-2 analysis: {creator_handle}")
                    
                    pbar.update(1)
                    time.sleep(random.uniform(2, 4) + slow_mode)
            
            if not creators_to_analyze:
                logger.warning("No creators found that pass Phase-1 criteria. Exiting.")
                return
            
            logger.info(f"Found {len(creators_to_analyze)} creators to analyze in Phase-2")
            
            # Phase 2: Analyze each creator's posts
            logger.info("=" * 60)
            logger.info("PHASE 2: Analyzing creators and their posts")
            logger.info("=" * 60)
            
            all_posts_data = []
            creators_data = []
            
            with tqdm(total=len(creators_to_analyze), desc="Phase-2: Analyzing creators") as pbar:
                for creator_handle, initial_post_url in creators_to_analyze.items():
                    # Process creator's posts
                    post_results = process_creator(
                        driver, creator_handle, posts_per_creator, scroll_delay_range,
                        min_comments, min_text_percentage, slow_mode
                    )
                    
                    if post_results:
                        # Add to all posts data
                        all_posts_data.extend(post_results)
                        
                        # Aggregate creator stats
                        creator_stats = aggregate_creator_stats(post_results)
                        creator_stats['creator_handle'] = creator_handle
                        creators_data.append(creator_stats)
                        
                        logger.info(
                            f"Creator {creator_handle}: {creator_stats['posts_analyzed']} posts analyzed, "
                            f"{creator_stats['posts_passed']} passed, avg EQS: {creator_stats['avg_EQS']:.2f}"
                        )
                    
                    pbar.update(1)
                    time.sleep(random.uniform(5, 8) + slow_mode)  # Delay between creators
            
            # Save results to CSV
            if all_posts_data:
                save_posts_csv(all_posts_data, posts_csv)
                logger.info(f"Posts data saved to: {posts_csv}")
            
            if creators_data:
                save_creators_csv(creators_data, creators_csv)
                logger.info(f"Creators data saved to: {creators_csv}")
            
            # Print summary
            logger.info("=" * 60)
            logger.info("SCRAPING COMPLETED!")
            logger.info("=" * 60)
            logger.info(f"Total creators analyzed: {len(creators_data)}")
            logger.info(f"Total posts analyzed: {len(all_posts_data)}")
            total_passed = sum(1 for p in all_posts_data if p.get('pass') == 'Pass')
            logger.info(f"Total posts that passed: {total_passed}")
            logger.info(f"Posts CSV: {posts_csv}")
            logger.info(f"Creators CSV: {creators_csv}")
            logger.info("=" * 60)
            
        finally:
            # Close driver
            driver.quit()
            logger.info("Browser closed")
            
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    main()

