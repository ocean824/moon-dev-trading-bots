'''
Truth Social Scraper - Tracks posts from realDonaldTrump
https://truthsocial.com/@realDonaldTrump
Created by Moon Dev 🌙 using Selenium for JavaScript rendering
'''

import pandas as pd
import time
from datetime import datetime
import os
import emoji
import json
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import subprocess
import platform
from selenium.webdriver.common.action_chains import ActionChains
import uuid

# Constants
URL = "https://truthsocial.com/@realDonaldTrump"
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "truth_social_posts.csv")
SLEEP_TIME = 30  # seconds

def load_existing_posts():
    """Load existing posts or create new DataFrame"""
    if os.path.exists(DATA_FILE):
        print(f"🌙 Moon Dev: Loading existing posts from {DATA_FILE}")
        df = pd.read_csv(DATA_FILE)
        # Convert timestamp to datetime for sorting
        if 'timestamp' in df.columns and not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    else:
        print("🌙 Moon Dev: Creating new posts database")
        return pd.DataFrame(columns=['timestamp', 'post_id', 'content', 'likes', 'reposts', 'post_timestamp'])

def setup_driver():
    """Setup Chrome driver with appropriate options"""
    print("🚀 Moon Dev: Setting up Chrome driver...")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # Hide automation
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        # Use the built-in webdriver manager
        driver = webdriver.Chrome(options=chrome_options)
        print("✅ Moon Dev: Chrome driver setup successful!")
        return driver
    except Exception as e:
        print(f"❌ Moon Dev: Error setting up Chrome driver: {str(e)}")
        print("\n💡 Moon Dev: Try installing Chrome with: brew install --cask google-chrome")
        raise

def wait_for_element(driver, by, selector, timeout=20):
    """Wait for an element to be present and return it"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, selector))
        )
        return element
    except TimeoutException:
        print(f"⚠️ Moon Dev: Timeout waiting for element {selector}")
        return None

def clean_text_for_csv(text):
    """Clean text to make it suitable for CSV storage"""
    if not text:
        return ""
    
    # Replace newlines with spaces
    text = text.replace('\n', ' ')
    
    # Replace consecutive spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def scrape_posts(driver):
    """Scrape Truth Social posts using Selenium"""
    try:
        print(f"🚀 Moon Dev: Launching scrape mission at {datetime.now()}")
        driver.get(URL)
        
        print("🔄 Moon Dev: Waiting for page to load...")
        
        # Wait for initial load
        time.sleep(5)
        
        # Scroll down a bit to load more content
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(2)
        
        # Save debug info on first run
        if not os.path.exists(DATA_FILE):
            print("🔍 Moon Dev: First run! Here's what we're working with:")
            print("Current URL:", driver.current_url)
            print("Page title:", driver.title)
            
            # Save page source and screenshot for debugging
            with open('debug_truth_social.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("💾 Moon Dev: Saved page source to debug_truth_social.html")
            
            driver.save_screenshot('debug_screenshot.png')
            print("📸 Moon Dev: Saved screenshot to debug_screenshot.png")
        
        # Extract posts using Selenium directly
        posts_data = []
        
        # Look for the main feed
        feed_elements = driver.find_elements(By.CSS_SELECTOR, ".item-list, .account__feed")
        if feed_elements:
            print(f"🎯 Moon Dev: Found feed element")
            
            # Now look for articles inside the feed
            post_elements = driver.find_elements(By.CSS_SELECTOR, "article")
            
            if post_elements:
                print(f"🎯 Moon Dev: Found {len(post_elements)} potential posts!")
                
                # Take a full page screenshot for debugging
                driver.save_screenshot('full_page.png')
                print("📸 Moon Dev: Saved full page screenshot")
                
                for i, post in enumerate(post_elements):
                    try:
                        # Take screenshot of this post
                        post_filename = f'post_{i+1}.png'
                        post.screenshot(post_filename)
                        print(f"📸 Moon Dev: Saved post screenshot to {post_filename}")
                        
                        # Get full post text
                        post_text = post.text
                        print(f"📝 Post {i+1} text: {post_text[:300]}")
                        
                        # Parse data from the post
                        
                        # Extract post ID
                        post_id = post.get_attribute('data-id') or post.get_attribute('id') or f"post_{uuid.uuid4()}"
                        
                        # Extract timestamp
                        time_elements = post.find_elements(By.CSS_SELECTOR, "time, a[href*='/status/']")
                        post_timestamp = ""
                        for elem in time_elements:
                            datetime_attr = elem.get_attribute('datetime')
                            if datetime_attr:
                                post_timestamp = datetime_attr
                                break
                            # Try to find time indicators like "47m", "10h"
                            if re.search(r'\d+[smhd]', elem.text):
                                post_timestamp = elem.text.strip()
                                break
                        
                        # Try to find the main post content - the most important part
                        content = ""
                        
                        # First try standard content selectors
                        content_elements = post.find_elements(By.CSS_SELECTOR, 
                            ".status__content, .post-content, [data-testid='post-content'], .content, .item-description, p")
                        
                        for elem in content_elements:
                            elem_text = elem.text.strip()
                            if elem_text and len(elem_text) > 5 and "@realDonaldTrump" not in elem_text:
                                content = elem_text
                                break
                        
                        # If we couldn't find content in specific elements, parse from full post text
                        if not content:
                            # Split the text to separate header/content/footer
                            lines = post_text.split('\n')
                            
                            if len(lines) >= 3:
                                # Try to identify a pattern that looks like a post
                                
                                # Typically we have:
                                # Donald J. Trump @realDonaldTrump · time_indicator
                                # [empty line]
                                # ACTUAL POST CONTENT HERE
                                # [optional media/other content]
                                # [metrics like likes/reposts]
                                
                                header_index = -1
                                for j, line in enumerate(lines):
                                    if "@realDonaldTrump" in line:
                                        header_index = j
                                        break
                                
                                if header_index != -1 and header_index < len(lines) - 2:
                                    # Content starts after header (and possibly an empty line)
                                    content_start = header_index + 1
                                    if content_start < len(lines) and not lines[content_start].strip():
                                        content_start += 1
                                    
                                    # Find where content ends (usually at metrics)
                                    content_end = len(lines)
                                    for j in range(len(lines) - 1, content_start, -1):
                                        # Metrics lines usually have numbers like "123", "4.5K", etc.
                                        if re.search(r'^\s*\d+(?:\.\d+)?[KMB]?\s*$', lines[j]):
                                            content_end = j
                                            break
                                    
                                    # Extract the content
                                    content = '\n'.join(lines[content_start:content_end])
                        
                        # Extract metrics (likes, reposts)
                        likes = "0"
                        reposts = "0"
                        
                        # Look for metrics in the text using regex
                        metrics_lines = [line for line in post_text.split('\n') if re.search(r'^\s*\d+(?:,\d+)*\s*$', line)]
                        if len(metrics_lines) >= 3:
                            # Usually format is: replies, reposts, likes
                            try:
                                reposts = metrics_lines[-2].strip()
                                likes = metrics_lines[-1].strip()
                            except:
                                pass
                        
                        # Format the complete post
                        username_line = next((line for line in post_text.split('\n') if "@realDonaldTrump" in line), "Donald J. Trump @realDonaldTrump")
                        
                        # Clean content for CSV
                        csv_content = clean_text_for_csv(content)
                        
                        post_data = {
                            'timestamp': datetime.now().isoformat(),
                            'post_id': post_id,
                            'content': csv_content,
                            'likes': likes,
                            'reposts': reposts,
                            'post_timestamp': post_timestamp
                        }
                        
                        posts_data.append(post_data)
                        print(f"📝 Moon Dev: Found post with ID: {post_id}")
                        print(f"🔖 Moon Dev: Content: {content}")
                    
                    except Exception as e:
                        print(f"⚠️ Moon Dev: Error parsing post {i+1}: {str(e)}")
        
        # If we didn't find any posts using the standard approach, try a more aggressive approach
        if not posts_data:
            print("🔍 Moon Dev: Trying alternative extraction method...")
            
            # Get all page text
            body_text = driver.find_element(By.TAG_NAME, 'body').text
            
            # Save all text for debugging
            with open('full_text.txt', 'w', encoding='utf-8') as f:
                f.write(body_text)
            print("💾 Moon Dev: Saved full page text")
            
            # Try to identify posts by looking for patterns
            
            # Pattern 1: Split by the account header
            trump_chunks = re.split(r'Donald J\. Trump\s*@realDonaldTrump\s*·\s*', body_text)
            
            if len(trump_chunks) > 1:
                # First chunk is before any Trump content
                trump_chunks = trump_chunks[1:]
                
                for i, chunk in enumerate(trump_chunks):
                    # Process each chunk
                    lines = chunk.split('\n')
                    
                    # First line is typically the timestamp
                    timestamp = lines[0].strip() if lines else ""
                    
                    # Extract content, stopping at numeric patterns that might be metrics
                    content_lines = []
                    for line in lines[1:]:
                        # Stop at lines that look like metrics (just numbers)
                        if re.match(r'^\s*\d+(?:,\d+)*\s*$', line):
                            break
                        content_lines.append(line)
                    
                    content = '\n'.join(content_lines).strip()
                    
                    # Clean up any trailing metrics or other patterns
                    content = re.sub(r'\s*\d+(?:,\d+)*\s*\d+(?:,\d+)*\s*\d+(?:,\d+)*\s*$', '', content)
                    
                    # Clean content for CSV
                    csv_content = clean_text_for_csv(content)
                    
                    if content:
                        post_data = {
                            'timestamp': datetime.now().isoformat(),
                            'post_id': f"chunk_{i}_{uuid.uuid4()}",
                            'content': csv_content,
                            'likes': "0",
                            'reposts': "0",
                            'post_timestamp': timestamp
                        }
                        
                        posts_data.append(post_data)
                        print(f"📝 Moon Dev: Found text chunk {i+1}")
                        print(f"🔖 Moon Dev: Content: {content[:100]}...")
        
        if not posts_data:
            print("⚠️ Moon Dev: No posts found with any method!")
        else:
            print(f"🎉 Moon Dev: Successfully extracted {len(posts_data)} posts!")
        
        return posts_data
    
    except Exception as e:
        print(f"❌ Moon Dev: Houston, we have a problem! {str(e)}")
        return []

def main():
    """Main scraping loop"""
    print("🌙 Moon Dev: Truth Social Scraper Initializing with Selenium...")
    
    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    
    print(f"📁 Moon Dev: Saving data to {DATA_FILE}")
    
    driver = setup_driver()
    df = load_existing_posts()
    
    try:
        while True:
            try:
                new_posts = scrape_posts(driver)
                
                if new_posts:
                    new_df = pd.DataFrame(new_posts)
                    
                    # Clean the post_id column to ensure proper comparison
                    if 'post_id' in df.columns and not df.empty:
                        df['post_id'] = df['post_id'].astype(str)
                    new_df['post_id'] = new_df['post_id'].astype(str)
                    
                    # Remove any posts with very short content
                    new_df = new_df[new_df['content'].str.len() > 20]
                    
                    # Only append posts we haven't seen before
                    if not df.empty:
                        # Check if we already have posts with similar content (first 50 chars)
                        existing_contents = set(df['content'].str.slice(0, 50))
                        new_contents = set(new_df['content'].str.slice(0, 50))
                        
                        # Only keep posts with new content
                        content_filter = ~new_df['content'].str.slice(0, 50).isin(existing_contents)
                        new_posts_df = new_df[content_filter]
                    else:
                        new_posts_df = new_df
                    
                    if not new_posts_df.empty:
                        print(f"🎉 Moon Dev: Found {len(new_posts_df)} new posts!")
                        
                        # Convert timestamp to datetime for sorting
                        if 'timestamp' in new_posts_df.columns:
                            new_posts_df['timestamp'] = pd.to_datetime(new_posts_df['timestamp'])
                        
                        # Add to our dataframe (new posts at top)
                        df = pd.concat([new_posts_df, df], ignore_index=True)
                        
                        # Sort by timestamp (newest first)
                        df = df.sort_values('timestamp', ascending=False)
                        
                        # Convert back to string for CSV storage
                        df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S')
                        
                        # Save to CSV
                        df.to_csv(DATA_FILE, index=False)
                        print("💾 Moon Dev: Posts saved to CSV!")
                        
                        # Print a preview of the new posts
                        for idx, (_, post) in enumerate(new_posts_df.iterrows()):
                            content_preview = post['content'][:100]
                            if len(post['content']) > 100:
                                content_preview += "..."
                            print(f"📊 New post {idx+1}: {content_preview}")
                    else:
                        print("😴 Moon Dev: No new posts found")
                
                print(f"🌙 Moon Dev: Taking a {SLEEP_TIME} second nap...")
                time.sleep(SLEEP_TIME)
                
            except Exception as e:
                print(f"⚠️ Moon Dev: Unexpected error: {str(e)}")
                print("🔄 Moon Dev: Retrying in 30 seconds...")
                time.sleep(SLEEP_TIME)
    
    except KeyboardInterrupt:
        print("👋 Moon Dev: Scraper stopped by user. Goodbye!")
    finally:
        driver.quit()
        print("🔚 Moon Dev: Chrome driver closed")

if __name__ == "__main__":
    main()
