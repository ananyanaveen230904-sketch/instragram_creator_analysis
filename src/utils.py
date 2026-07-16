"""
Utility Functions Module

Contains helper functions for:
- Configuration loading
- Selenium driver setup
- Instagram login
- Comment extraction and scrolling
- CSV saving
"""

import os
import sys
import time
import random
import logging
import csv
from datetime import datetime
import shutil
import yaml
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path=None):
    """
    Load configuration from YAML file.
    
    Args:
        config_path (str): Path to the config YAML file (default: config/config.yaml relative to project root)
        
    Returns:
        dict: Configuration dictionary
    """
    if config_path is None:
        # Default to config/config.yaml relative to project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(project_root, 'config', 'config.yaml')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML config: {e}")
        raise


def setup_driver(headless=False, slow_mode=0):
    """
    Setup and configure Chrome WebDriver.
    
    Args:
        headless (bool): Run browser in headless mode
        slow_mode (int): Additional delay in seconds between actions
        
    Returns:
        webdriver.Chrome: Configured Chrome driver instance
    """
    options = webdriver.ChromeOptions()
    
    if headless:
        options.add_argument('--headless')
    
    # Anti-detection options
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    # User agent to appear more like a real browser
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(options=options)
        time.sleep(2)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        logger.info("Chrome driver initialized successfully")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome driver: {e}")
        raise


def instagram_login(driver, username, password, slow_mode=0):
    """
    Log into Instagram with provided credentials.
    
    Args:
        driver: Selenium WebDriver instance
        username (str): Instagram username
        password (str): Instagram password
        slow_mode (int): Additional delay in seconds
        
    Returns:
        bool: True if login successful, False otherwise
    """
    try:
        logger.info("Navigating to Instagram login page...")
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(3 + slow_mode)
        
        # Wait for login form to appear
        wait = WebDriverWait(driver, 20)
        
        # Try multiple selectors for username field
        username_field = None
        username_selectors = [
            (By.NAME, "username"),
            (By.XPATH, "//input[@name='username']"),
            (By.XPATH, "//input[@aria-label='Phone number, username, or email']"),
            (By.XPATH, "//input[@placeholder='Phone number, username, or email']"),
            (By.XPATH, "//input[@type='text']"),
        ]
        
        for selector_type, selector_value in username_selectors:
            try:
                username_field = wait.until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                logger.info(f"Found username field using {selector_type}: {selector_value}")
                break
            except TimeoutException:
                continue
        
        if not username_field:
            logger.error("Could not find username field. Saving screenshot for debugging...")
            try:
                driver.save_screenshot("login_error_username_field.png")
                logger.info("Screenshot saved as login_error_username_field.png")
            except:
                pass
            return False
        
        # Fill username with human-like typing
        username_field.clear()
        time.sleep(0.5)
        for char in username:
            username_field.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        time.sleep(random.uniform(1, 2) + slow_mode)
        logger.info("Username entered")
        
        # Try multiple selectors for password field
        password_field = None
        password_selectors = [
            (By.NAME, "password"),
            (By.XPATH, "//input[@name='password']"),
            (By.XPATH, "//input[@aria-label='Password']"),
            (By.XPATH, "//input[@type='password']"),
        ]
        
        for selector_type, selector_value in password_selectors:
            try:
                password_field = driver.find_element(selector_type, selector_value)
                logger.info(f"Found password field using {selector_type}: {selector_value}")
                break
            except NoSuchElementException:
                continue
        
        if not password_field:
            logger.error("Could not find password field. Saving screenshot for debugging...")
            try:
                driver.save_screenshot("login_error_password_field.png")
                logger.info("Screenshot saved as login_error_password_field.png")
            except:
                pass
            return False
        
        # Fill password
        password_field.clear()
        time.sleep(0.5)
        for char in password:
            password_field.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        time.sleep(random.uniform(1, 2) + slow_mode)
        logger.info("Password entered")
        
        # Find and click login button with multiple selectors
        # Find and click login button with multiple selectors
        login_button = None
        login_selectors = [
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Log in')]"),
            (By.XPATH, "//button[contains(text(), 'Log In')]"),
            (By.XPATH, "//div[contains(text(), 'Log in')]/ancestor::button"),
            (By.XPATH, "//button[contains(@class, 'submit')]"),
        ]
        
        for selector_type, selector_value in login_selectors:
            try:
                candidate = driver.find_element(selector_type, selector_value)
                if candidate.is_displayed() and candidate.is_enabled():
                    login_button = candidate
                    logger.info(f"Found login button using {selector_type}: {selector_value}")
                    break
            except NoSuchElementException:
                continue

        # Fallback: scan every <button> on the page and match by visible text,
        # since Instagram often wraps the label in nested <div>/<span> tags
        # that plain XPath text() matching can miss.
        if not login_button:
            try:
                all_buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in all_buttons:
                    try:
                        btn_text = btn.text.strip().lower()
                        if "log in" in btn_text:
                            if btn.is_displayed() and btn.is_enabled():
                                login_button = btn
                                logger.info(f"Found login button by scanning button text: '{btn.text}'")
                                break
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Error scanning buttons for login text: {e}")

        # Last resort: submit the form directly via the password field
        if not login_button:
            try:
                password_field.send_keys(Keys.RETURN)
                logger.info("Login button not found; submitted form via Enter key on password field")
                time.sleep(5 + slow_mode)
                login_button = True  # sentinel so we skip the click step below
            except Exception as e:
                logger.warning(f"Enter-key submission fallback failed: {e}")
        
        if not login_button:
            logger.error("Could not find login button. Saving screenshot for debugging...")
            try:
                driver.save_screenshot("login_error_button.png")
                logger.info("Screenshot saved as login_error_button.png")
            except:
                pass
            return False
        
        # Click login button
        # Click login button (skip if we already submitted via Enter key above)
        if login_button is not True:
            try:
                driver.execute_script("arguments[0].click();", login_button)
            except:
                login_button.click()
            logger.info("Login button clicked")
        
        # Check for various error messages
        error_messages = [
            "Sorry, your password was incorrect",
            "The password you entered is incorrect",
            "incorrect",
            "Please wait a few minutes",
            "Try again later",
            "suspicious activity",
            "challenge_required",
            "checkpoint_required",
        ]
        
        page_text = driver.page_source.lower()
        for error_msg in error_messages:
            if error_msg.lower() in page_text:
                logger.error(f"Login failed: Detected error message containing '{error_msg}'")
                try:
                    driver.save_screenshot("login_error_detected.png")
                    logger.info("Screenshot saved as login_error_detected.png")
                except:
                    pass
                return False
        
        # Check for security challenge / 2FA
        challenge_indicators = [
            "verify your identity",
            "enter confirmation code",
            "two-factor",
            "security code",
            "confirmation code",
        ]
        
        for indicator in challenge_indicators:
            if indicator.lower() in page_text:
                logger.warning(f"Security challenge detected: {indicator}")
                logger.warning("Instagram may require manual verification. Please check the browser.")
                try:
                    driver.save_screenshot("login_security_challenge.png")
                    logger.info("Screenshot saved as login_security_challenge.png")
                except:
                    pass
                # Wait a bit longer for user to complete challenge
                time.sleep(10)
        
        # Handle "Save Login Info" or "Not Now" prompts
        prompt_selectors = [
            "//button[contains(text(), 'Not Now')]",
            "//button[contains(text(), 'Save Info')]",
            "//button[contains(text(), 'Not now')]",
            "//button[contains(@aria-label, 'Not Now')]",
        ]
        
        for selector in prompt_selectors:
            try:
                prompt_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                driver.execute_script("arguments[0].click();", prompt_button)
                logger.info("Dismissed save login info prompt")
                time.sleep(2 + slow_mode)
                break
            except TimeoutException:
                continue
        
        # Check if we're logged in by looking for Instagram home page elements
        login_success_indicators = [
            (By.XPATH, "//a[contains(@href, '/direct/inbox/')]"),
            (By.XPATH, "//a[contains(@href, '/explore/')]"),
            (By.XPATH, "//svg[@aria-label='Home']"),
            (By.XPATH, "//a[contains(@href, '/') and contains(@aria-label, 'Home')]"),
            (By.XPATH, "//nav[contains(@role, 'navigation')]"),
        ]
        
        for selector_type, selector_value in login_success_indicators:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                logger.info("Login successful! Detected Instagram home page elements.")
                return True
            except TimeoutException:
                continue
        
        # Final check: look at current URL
        current_url = driver.current_url
        logger.info(f"Current URL after login attempt: {current_url}")
        
        if "accounts/login" not in current_url and "challenge" not in current_url:
            logger.info("Login appears successful (not on login page)")
            return True
        
        # If we get here, login likely failed
        logger.error("Login failed: Could not verify successful login")
        logger.error("Current page URL: " + current_url)
        try:
            driver.save_screenshot("login_final_error.png")
            logger.info("Screenshot saved as login_final_error.png")
            # Also save page source for debugging
            with open("login_page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            logger.info("Page source saved as login_page_source.html")
        except Exception as e:
            logger.warning(f"Could not save debug files: {e}")
        
        return False
            
    except TimeoutException as e:
        logger.error(f"Timeout during login: {e}")
        try:
            driver.save_screenshot("login_timeout_error.png")
            logger.info("Screenshot saved as login_timeout_error.png")
        except:
            pass
        return False
    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        try:
            driver.save_screenshot("login_exception_error.png")
            logger.info("Screenshot saved as login_exception_error.png")
        except:
            pass
        return False


def scroll_and_collect_comments(driver, max_scroll_attempts=15, slow_mode=0):
    """
    Scroll through a post's comments and collect all visible comments.
    
    Args:
        driver: Selenium WebDriver instance
        max_scroll_attempts (int): Maximum number of scroll attempts
        slow_mode (int): Additional delay in seconds
        
    Returns:
        list: List of comment text strings
    """
    comments = []
    scroll_attempts = 0
    last_comment_count = 0
    stable_count = 0
    
    try:
        # Wait for page to load
        wait = WebDriverWait(driver, 15)
        
        # Try multiple selectors to find comments container
        comments_container = None
        container_selectors = [
            "//div[@role='dialog']",
            "//div[contains(@class, 'x1n2onr6')]//ul",
            "//ul[contains(@class, 'x78zum5')]",
            "//div[contains(@aria-label, 'Comments')]",
            "//section[contains(@aria-label, 'Comments')]",
        ]
        
        for selector in container_selectors:
            try:
                comments_container = wait.until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                logger.info(f"Found comments container using: {selector}")
                break
            except TimeoutException:
                continue
        
        if not comments_container:
            logger.warning("Comments section not found, trying alternative method...")
            # Try to find comments directly on the page (not in dialog)
            comments_container = driver
        
        while scroll_attempts < max_scroll_attempts:
            # Try multiple selectors to find comment text elements
            comment_selectors = [
                "//div[@role='dialog']//span[@dir='auto']",
                "//ul//span[@dir='auto']",
                "//div[contains(@class, 'x1lliihq')]//span[@dir='auto']",
                "//article//span[@dir='auto']",
                "//div[contains(@aria-label, 'Comment')]//span",
                "//span[contains(@class, 'x193iq5w')]",
            ]
            
            comment_elements = []
            for selector in comment_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    comment_elements.extend(elements)
                except:
                    continue
            
            # Extract unique comments
            current_comments = []
            for elem in comment_elements:
                try:
                    text = elem.text.strip()
                    # Filter out empty text, usernames (usually short), and navigation text
                    if (text and 
                        len(text) > 2 and 
                        text not in current_comments and
                        not text.startswith('@') and
                        'View' not in text and
                        'Load' not in text and
                        'more' not in text.lower()):
                        current_comments.append(text)
                except:
                    continue
            
            # Update comments list (avoid duplicates)
            for comment in current_comments:
                # Check for duplicates (case-insensitive, ignore extra spaces)
                comment_normalized = ' '.join(comment.lower().split())
                is_duplicate = any(' '.join(c.lower().split()) == comment_normalized for c in comments)
                if not is_duplicate:
                    comments.append(comment)
            
            # Check if we've loaded all comments
            if len(comments) == last_comment_count:
                stable_count += 1
                if stable_count >= 3:
                    # Check for "Load more comments" button
                    load_more_selectors = [
                        "//button[contains(text(), 'Load more')]",
                        "//button[contains(text(), 'View more')]",
                        "//a[contains(text(), 'View') and contains(text(), 'more')]",
                        "//button[contains(@aria-label, 'more')]",
                    ]
                    
                    load_more_found = False
                    for selector in load_more_selectors:
                        try:
                            load_more = driver.find_element(By.XPATH, selector)
                            if load_more.is_displayed() and load_more.is_enabled():
                                try:
                                    driver.execute_script("arguments[0].click();", load_more)
                                    time.sleep(2 + slow_mode)
                                    stable_count = 0
                                    load_more_found = True
                                    logger.info("Clicked 'Load more comments' button")
                                    break
                                except:
                                    pass
                        except NoSuchElementException:
                            continue
                    
                    if not load_more_found:
                        logger.info("All comments loaded (no 'Load more' button found)")
                        break
            else:
                stable_count = 0
            
            last_comment_count = len(comments)
            
            # Scroll within comments section
            try:
                if comments_container and comments_container != driver:
                    # Scroll the comments container
                    driver.execute_script(
                        "arguments[0].scrollTop = arguments[0].scrollHeight",
                        comments_container
                    )
                else:
                    # Scroll the page
                    scroll_amount = random.randint(300, 500)
                    driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            except Exception as e:
                logger.warning(f"Error scrolling: {e}")
                # Fallback: simple page scroll
                driver.execute_script("window.scrollBy(0, 500);")
            
            time.sleep(random.uniform(1, 2) + slow_mode)
            scroll_attempts += 1
            
            # Log progress every 5 attempts
            if scroll_attempts % 5 == 0:
                logger.info(f"Comment collection progress: {len(comments)} comments (attempt {scroll_attempts})")
        
        logger.info(f"Collected {len(comments)} unique comments after {scroll_attempts} scroll attempts")
        return comments
        
    except Exception as e:
        logger.error(f"Error collecting comments: {e}", exc_info=True)
        return comments


def extract_creator_handle(driver):
    """
    Extract the creator's Instagram handle from a post.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        str: Creator handle or empty string if not found
    """
    try:
        # Try multiple selectors for creator handle
        selectors = [
            "//header//a[contains(@href, '/') and not(contains(@href, '/p/')) and not(contains(@href, '/explore/'))]",
            "//div[@role='dialog']//header//a[contains(@href, '/')]",
            "//article//header//a[contains(@href, '/')]",
            "//a[contains(@href, '/') and contains(@role, 'link')]",
            "//span[contains(text(), '@')]/ancestor::a",
        ]
        
        seen_handles = set()
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    try:
                        href = element.get_attribute('href')
                        if href:
                            # Extract handle from URL
                            parts = [p for p in href.split('/') if p]
                            if len(parts) >= 2:
                                handle = parts[-1]
                                # Filter out invalid handles
                                if (handle and 
                                    handle not in ['accounts', 'explore', 'p', 'reel', 'stories'] and
                                    not handle.startswith('?') and
                                    'instagram.com' not in handle and
                                    handle not in seen_handles):
                                    seen_handles.add(handle)
                                    # Verify it looks like a handle (alphanumeric, dots, underscores)
                                    if handle.replace('_', '').replace('.', '').isalnum():
                                        logger.info(f"Extracted creator handle: {handle}")
                                        return handle
                    except:
                        continue
            except:
                continue
        
        # Fallback: try to extract from page source or URL
        try:
            current_url = driver.current_url
            if '/p/' in current_url or '/reel/' in current_url:
                # URL format: instagram.com/username/p/...
                parts = current_url.split('/')
                for i, part in enumerate(parts):
                    if part in ['p', 'reel'] and i > 0:
                        potential_handle = parts[i-1]
                        if potential_handle and potential_handle not in ['www', 'instagram', 'com']:
                            logger.info(f"Extracted creator handle from URL: {potential_handle}")
                            return potential_handle
        except:
            pass
        
        logger.warning("Could not extract creator handle")
        return ""
    except Exception as e:
        logger.warning(f"Error extracting creator handle: {e}")
        return ""


def save_posts_csv(posts_data, output_path):
    """
    Save posts data to CSV file.
    
    Args:
        posts_data (list): List of dictionaries containing post data
        output_path (str): Path to output CSV file
    """
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Create DataFrame
        df = pd.DataFrame(posts_data)
        
        # Ensure all required columns exist
        required_columns = [
            'creator_handle', 'post_url', 'total_comments',
            'text_percentage', 'emoji_percentage', 'mixed_percentage',
            'unique_commenters_ratio', 'EQS', 'pass'
        ]
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''
        
        # Reorder columns
        df = df[required_columns]
        
        # Save to CSV
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"Posts data saved to {output_path}")
        logger.info(f"Total posts: {len(posts_data)}")
        
    except Exception as e:
        logger.error(f"Error saving posts CSV: {e}")
        raise


def save_creators_csv(creators_data, output_path):
    """
    Save creators data to CSV file.
    
    Args:
        creators_data (list): List of dictionaries containing creator data
        output_path (str): Path to output CSV file
    """
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Create DataFrame
        df = pd.DataFrame(creators_data)
        
        # Ensure all required columns exist
        required_columns = [
            'creator_handle', 'posts_analyzed', 'posts_passed',
            'avg_text_percentage', 'avg_emoji_percentage', 'avg_mixed_percentage',
            'avg_EQS', 'best_EQS', 'worst_EQS'
        ]
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''
        
        # Reorder columns
        df = df[required_columns]
        
        # Save to CSV
        df.to_csv(output_path, index=False, encoding='utf-8')
        logger.info(f"Creators data saved to {output_path}")
        logger.info(f"Total creators: {len(creators_data)}")
        
    except Exception as e:
        logger.error(f"Error saving creators CSV: {e}")
        raise
def save_raw_comments(creator_handle, post_url, comments, output_path=None):
    """
    Append raw comment text to output/raw_comments.csv for later offline analysis
    (e.g. transformer-based sentiment classification).
    """
    if not comments:
        logger.info(f"No raw comments to save for post: {post_url}")
        return

    if output_path is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(project_root, 'output', 'raw_comments.csv')

    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        existing_pairs = set()
        file_exists = os.path.isfile(output_path)

        if file_exists:
            try:
                with open(output_path, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        existing_pairs.add((row.get('post_url', ''), row.get('comment_text', '')))
            except Exception as e:
                logger.warning(f"Could not read existing raw_comments.csv for dedup check: {e}")

        write_header = not file_exists
        saved_count = 0
        skipped_count = 0
        scraped_at = datetime.now().isoformat()

        with open(output_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            if write_header:
                writer.writerow(['creator_handle', 'post_url', 'comment_text', 'scraped_at'])

            for comment in comments:
                if not comment:
                    continue

                pair = (post_url, comment)
                if pair in existing_pairs:
                    skipped_count += 1
                    continue

                writer.writerow([creator_handle, post_url, comment, scraped_at])
                existing_pairs.add(pair)
                saved_count += 1

        logger.info(
            f"Saved {saved_count} raw comments to {output_path} "
            f"({skipped_count} duplicates skipped) for post: {post_url}"
        )

    except Exception as e:
        logger.error(f"Error saving raw comments for post {post_url}: {e}", exc_info=True)

