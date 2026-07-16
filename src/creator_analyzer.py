"""
Creator Analyzer Module

Analyzes Instagram creator profiles:
- Fetches creator's profile page
- Collects multiple posts from creator
- Aggregates creator-level statistics
"""

import time
import random
import logging
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException
)

logger = logging.getLogger(__name__)


def get_creator_profile_url(creator_handle: str) -> str:
    """
    Construct Instagram profile URL from handle.
    
    Args:
        creator_handle (str): Creator's Instagram handle
        
    Returns:
        str: Profile URL
    """
    # Remove @ if present
    handle = creator_handle.lstrip('@')
    return f"https://www.instagram.com/{handle}/"


def fetch_creator_posts(
    driver: webdriver.Chrome,
    creator_handle: str,
    num_posts: int,
    scroll_delay_range: List[int],
    slow_mode: int = 0
) -> List[str]:
    """
    Navigate to creator's profile and collect post URLs.
    
    Args:
        driver: Selenium WebDriver instance
        creator_handle (str): Creator's Instagram handle
        num_posts (int): Number of posts to collect
        scroll_delay_range (List[int]): [min, max] delay range for scrolling
        slow_mode (int): Additional delay in seconds
        
    Returns:
        List[str]: List of post URLs
    """
    post_urls = []
    
    try:
        profile_url = get_creator_profile_url(creator_handle)
        logger.info(f"Navigating to creator profile: {profile_url}")
        
        driver.get(profile_url)
        time.sleep(4 + slow_mode)
        
        # Wait for profile to load
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
            logger.info("Creator profile loaded successfully")
        except TimeoutException:
            logger.warning("Profile may not have loaded completely, continuing anyway...")
        
        # Collect post URLs by scrolling
        scroll_attempts = 0
        max_scrolls = 30
        seen_urls = set()
        no_new_posts_count = 0
        
        logger.info(f"Collecting {num_posts} posts from creator: {creator_handle}")
        
        while len(post_urls) < num_posts and scroll_attempts < max_scrolls:
            # Find all post links
            post_selectors = [
                "//a[contains(@href, '/p/')]",
                "//a[contains(@href, '/reel/')]",
                "//article//a[contains(@href, '/p/')]",
                "//article//a[contains(@href, '/reel/')]",
            ]
            
            post_links = []
            for selector in post_selectors:
                try:
                    links = driver.find_elements(By.XPATH, selector)
                    post_links.extend(links)
                except:
                    continue
            
            # Extract unique URLs
            previous_count = len(post_urls)
            for link in post_links:
                try:
                    href = link.get_attribute('href')
                    if href and ('/p/' in href or '/reel/' in href):
                        # Clean URL (remove query parameters)
                        clean_url = href.split('?')[0]
                        if clean_url not in seen_urls:
                            post_urls.append(clean_url)
                            seen_urls.add(clean_url)
                            if len(post_urls) >= num_posts:
                                break
                except:
                    continue
            
            # Check if we found new posts
            if len(post_urls) == previous_count:
                no_new_posts_count += 1
                if no_new_posts_count >= 3:
                    logger.warning("No new posts found after multiple scrolls, stopping...")
                    break
            else:
                no_new_posts_count = 0
            
            if len(post_urls) >= num_posts:
                break
            
            # Scroll down gradually
            scroll_amount = random.randint(500, 800)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            
            min_delay, max_delay = scroll_delay_range
            delay = random.uniform(min_delay, max_delay) + slow_mode
            time.sleep(delay)
            
            scroll_attempts += 1
            
            # Log progress
            if scroll_attempts % 5 == 0:
                logger.info(f"Progress: {len(post_urls)}/{num_posts} posts collected (scroll {scroll_attempts})")
        
        logger.info(f"Collected {len(post_urls)} posts from creator: {creator_handle}")
        return post_urls[:num_posts]
        
    except Exception as e:
        logger.error(f"Error fetching creator posts for {creator_handle}: {e}", exc_info=True)
        return post_urls


def aggregate_creator_stats(post_results: List[Dict]) -> Dict:
    """
    Aggregate statistics across all posts from a creator.
    
    Args:
        post_results (List[Dict]): List of post analysis results
        
    Returns:
        Dict: Aggregated creator statistics
    """
    if not post_results:
        return {
            'posts_analyzed': 0,
            'posts_passed': 0,
            'avg_text_percentage': 0.0,
            'avg_emoji_percentage': 0.0,
            'avg_mixed_percentage': 0.0,
            'avg_EQS': 0.0,
            'best_EQS': 0.0,
            'worst_EQS': 0.0
        }
    
    posts_analyzed = len(post_results)
    posts_passed = sum(1 for p in post_results if p.get('pass') == 'Pass')
    
    # Calculate averages
    text_percentages = [p.get('text_percentage', 0.0) for p in post_results]
    emoji_percentages = [p.get('emoji_percentage', 0.0) for p in post_results]
    mixed_percentages = [p.get('mixed_percentage', 0.0) for p in post_results]
    eqs_scores = [p.get('EQS', 0.0) for p in post_results]
    
    avg_text = sum(text_percentages) / len(text_percentages) if text_percentages else 0.0
    avg_emoji = sum(emoji_percentages) / len(emoji_percentages) if emoji_percentages else 0.0
    avg_mixed = sum(mixed_percentages) / len(mixed_percentages) if mixed_percentages else 0.0
    avg_eqs = sum(eqs_scores) / len(eqs_scores) if eqs_scores else 0.0
    
    # Find best and worst EQS
    best_eqs = max(eqs_scores) if eqs_scores else 0.0
    worst_eqs = min(eqs_scores) if eqs_scores else 0.0
    
    return {
        'posts_analyzed': posts_analyzed,
        'posts_passed': posts_passed,
        'avg_text_percentage': round(avg_text, 2),
        'avg_emoji_percentage': round(avg_emoji, 2),
        'avg_mixed_percentage': round(avg_mixed, 2),
        'avg_EQS': round(avg_eqs, 2),
        'best_EQS': round(best_eqs, 2),
        'worst_EQS': round(worst_eqs, 2)
    }

