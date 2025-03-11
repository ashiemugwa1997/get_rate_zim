"""
Social media scraper module for ZimRate Predictor

This module contains functions to scrape social media posts from Twitter (X) 
and other platforms about Zimbabwean currency exchange rates.
"""

import requests
import json
import logging
import time
import datetime
import re
from typing import List, Dict, Any, Optional
from django.utils import timezone
import random
import os
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("social_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("social_scraper")

# Keywords to search for related to Zimbabwe's currency and economy
SEARCH_KEYWORDS = [
    "Zimbabwe dollar", "ZWL", "Zimbabwe forex", "Zimbabwe exchange rate", 
    "Zimbabwe USD", "Zimbabwe currency", "RBZ rate", "parallel market Zimbabwe",
    "Zimbabwe inflation", "Zimbabwe bond note", "Zimbabwe monetary policy",
    "Zimbabwe black market rate"
]

# List of influential accounts to monitor (usernames without @)
INFLUENTIAL_ACCOUNTS = [
    "ReserveBankZIM",    # Reserve Bank of Zimbabwe
    "ZimTreasury",       # Ministry of Finance Zimbabwe
    "MthuliNcube",       # Zimbabwe's Finance Minister
    "InfoMinZW",         # Zimbabwe Ministry of Information
    "ZimTradeAlerts",    # Zimbabwe Trade
    "ZimEye",            # Zimbabwe News
    "BitiTendai",        # Prominent Zimbabwean politician
    "ZimLive",           # Zimbabwe News Source
    "263Chat",           # Popular Zimbabwean News Platform
    "daddyhope"          # Prominent Zimbabwean activist
]


class TwitterScraper:
    """Class to handle Twitter (X) scraping operations"""
    
    def __init__(self):
        """Initialize the Twitter scraper with necessary configurations"""
        # User agent for requests
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self.base_url = "https://nitter.net"  # Nitter instance for Twitter scraping
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})
    
    def rotate_nitter_instance(self):
        """Rotate between available Nitter instances to avoid rate limiting"""
        nitter_instances = [
            "https://nitter.net",
            "https://nitter.lacontrevoie.fr",
            "https://nitter.1d4.us",
            "https://nitter.kavin.rocks",
            "https://nitter.poast.org"
        ]
        self.base_url = random.choice(nitter_instances)
        logger.info(f"Rotated to Nitter instance: {self.base_url}")
    
    def search_tweets(self, query: str, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Search for tweets matching a query
        
        Args:
            query: Search query string
            days_back: How many days back to search
            
        Returns:
            List of tweet dictionaries
        """
        tweets = []
        params = {"f": "tweets", "q": query}
        search_url = f"{self.base_url}/search?{urlencode(params)}"
        
        cutoff_date = timezone.now().date() - datetime.timedelta(days=days_back)
        
        try:
            logger.info(f"Searching Twitter for: {query}")
            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()
            
            # Basic parsing of the HTML response
            # Ideally use BeautifulSoup here, but for simplicity using regex
            tweet_pattern = r'<div class="tweet-content[^>]*>(.*?)</div>.*?<a[^>]*class="tweet-date[^>]*><span[^>]*>(.*?)</span>'
            username_pattern = r'<a[^>]*class="username"[^>]*>@([^<]+)</a>'
            
            tweet_matches = re.finditer(tweet_pattern, response.text, re.DOTALL)
            username_matches = re.finditer(username_pattern, response.text, re.DOTALL)
            
            # Extract content, dates, and usernames
            for tweet_match, username_match in zip(tweet_matches, username_matches):
                content = tweet_match.group(1).strip()
                date_text = tweet_match.group(2).strip()
                username = username_match.group(1).strip()
                
                # Parse date (simplified approach)
                if "ago" in date_text:
                    # Recent post (assume within cutoff)
                    post_date = timezone.now().date()
                else:
                    try:
                        # Format can vary; this is simplified
                        date_parts = date_text.split()
                        if len(date_parts) >= 2:
                            month = date_parts[0]
                            day = int(date_parts[1].replace(",", ""))
                            year = int(date_parts[2]) if len(date_parts) > 2 else timezone.now().year
                            
                            month_mapping = {
                                "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                                "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
                            }
                            
                            if month in month_mapping:
                                post_date = datetime.date(year, month_mapping[month], day)
                            else:
                                continue
                        else:
                            continue
                    except (ValueError, IndexError):
                        continue
                
                # Check if post is within the date range
                if post_date >= cutoff_date:
                    tweets.append({
                        "content": content,
                        "username": username,
                        "published_at": post_date,
                        "url": f"https://twitter.com/{username}/status/PLACEHOLDER",  # Actual URL not easily accessible this way
                        "platform": "Twitter"
                    })
            
            logger.info(f"Found {len(tweets)} tweets for query: {query}")
            
        except requests.RequestException as e:
            logger.error(f"Error searching Twitter: {e}")
            # Rotate to another Nitter instance
            self.rotate_nitter_instance()
        
        return tweets
    
    def get_user_tweets(self, username: str, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Get tweets from a specific user
        
        Args:
            username: Twitter username (without @)
            days_back: How many days back to fetch
            
        Returns:
            List of tweet dictionaries
        """
        tweets = []
        user_url = f"{self.base_url}/{username}"
        
        cutoff_date = timezone.now().date() - datetime.timedelta(days=days_back)
        
        try:
            logger.info(f"Fetching tweets from user: {username}")
            response = self.session.get(user_url, timeout=15)
            
            if response.status_code == 404:
                logger.warning(f"User not found: {username}")
                return tweets
                
            response.raise_for_status()
            
            # Similar parsing as search_tweets method
            tweet_pattern = r'<div class="tweet-content[^>]*>(.*?)</div>.*?<a[^>]*class="tweet-date[^>]*><span[^>]*>(.*?)</span>'
            tweet_matches = re.finditer(tweet_pattern, response.text, re.DOTALL)
            
            for match in tweet_matches:
                content = match.group(1).strip()
                date_text = match.group(2).strip()
                
                # Parse date (simplified)
                if "ago" in date_text:
                    post_date = timezone.now().date()
                else:
                    try:
                        date_parts = date_text.split()
                        if len(date_parts) >= 2:
                            month = date_parts[0]
                            day = int(date_parts[1].replace(",", ""))
                            year = int(date_parts[2]) if len(date_parts) > 2 else timezone.now().year
                            
                            month_mapping = {
                                "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                                "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
                            }
                            
                            if month in month_mapping:
                                post_date = datetime.date(year, month_mapping[month], day)
                            else:
                                continue
                        else:
                            continue
                    except (ValueError, IndexError):
                        continue
                
                # Check if tweet contains finance-related keywords (simplified)
                if post_date >= cutoff_date and is_relevant_to_currency(content):
                    tweets.append({
                        "content": content,
                        "username": username,
                        "published_at": post_date,
                        "url": f"https://twitter.com/{username}/status/PLACEHOLDER",
                        "platform": "Twitter"
                    })
            
            logger.info(f"Found {len(tweets)} relevant tweets from {username}")
            
        except requests.RequestException as e:
            logger.error(f"Error fetching tweets from {username}: {e}")
            self.rotate_nitter_instance()
        
        return tweets


def is_relevant_to_currency(text: str) -> bool:
    """
    Check if text is relevant to Zimbabwe currency/exchange rates
    
    Args:
        text: Text content to check
        
    Returns:
        Boolean indicating relevance
    """
    relevant_keywords = [
        "exchange rate", "forex", "currency", "dollar", "USD", "ZWL", "Zimbabwe dollar", 
        "RBZ", "Reserve Bank", "inflation", "economy", "finance", "monetary", 
        "currency trading", "black market", "parallel market", "bond note"
    ]
    
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in relevant_keywords)


def save_posts_to_db(posts: List[Dict[str, Any]]) -> int:
    """
    Save scraped social media posts to the database
    
    Args:
        posts: List of post dictionaries to save
        
    Returns:
        Number of posts successfully saved
    """
    from rate_predictor.models import SocialMediaSource, Post
    
    saved_count = 0
    
    for post in posts:
        try:
            # Get or create social media source based on username and platform
            source, _ = SocialMediaSource.objects.get_or_create(
                name=post["username"],
                platform=post["platform"],
                defaults={
                    "account_id": post["username"],
                    "influence_score": 1.0  # Default score, can be updated later
                }
            )
            
            # Check if post already exists (simplified check by content and username)
            if not Post.objects.filter(
                social_source=source,
                content=post["content"][:100]  # Check first 100 chars for uniqueness
            ).exists():
                # Create new post
                db_post = Post(
                    social_source=source,
                    source_type='social',
                    content=post["content"],
                    url=post.get("url", ""),
                    published_at=timezone.make_aware(
                        datetime.datetime.combine(post["published_at"], datetime.time())
                    ),
                    # These will be updated by the sentiment analysis process
                    sentiment='neutral',
                    impact_score=0.0
                )
                db_post.save()
                saved_count += 1
        
        except Exception as e:
            logger.error(f"Error saving social post from {post.get('username', 'Unknown')}: {e}")
    
    logger.info(f"Saved {saved_count} new social media posts to the database")
    return saved_count


def run_twitter_scraper(days_back: int = 7) -> int:
    """
    Run the Twitter scraper to collect tweets
    
    Args:
        days_back: Number of days back to consider
        
    Returns:
        Number of posts scraped and saved
    """
    twitter = TwitterScraper()
    all_tweets = []
    
    # Scrape tweets from influential accounts
    for account in INFLUENTIAL_ACCOUNTS:
        try:
            tweets = twitter.get_user_tweets(account, days_back)
            all_tweets.extend(tweets)
            # Be respectful to the service
            time.sleep(random.uniform(2, 5))
        except Exception as e:
            logger.error(f"Error scraping tweets from {account}: {e}")
    
    # Scrape tweets based on keywords
    for keyword in SEARCH_KEYWORDS:
        try:
            tweets = twitter.search_tweets(keyword, days_back)
            all_tweets.extend(tweets)
            # Be respectful to the service
            time.sleep(random.uniform(2, 5))
        except Exception as e:
            logger.error(f"Error searching tweets for keyword {keyword}: {e}")
    
    # Save unique tweets to the database
    # Simple deduplication by content
    unique_tweets = []
    seen_content = set()
    
    for tweet in all_tweets:
        # Use first 100 chars as a signature to avoid duplicates
        content_signature = tweet["content"][:100]
        if content_signature not in seen_content:
            seen_content.add(content_signature)
            unique_tweets.append(tweet)
    
    # Save posts to database
    saved_count = save_posts_to_db(unique_tweets)
    
    return saved_count


def run_scraper(days_back: int = 7) -> int:
    """
    Main function to run the social media scrapers
    
    Args:
        days_back: Number of days back to consider
        
    Returns:
        Number of posts scraped and saved
    """
    logger.info(f"Starting social media scraping process for the past {days_back} days")
    
    # Currently only Twitter scraping implemented
    saved_count = run_twitter_scraper(days_back)
    
    logger.info(f"Completed social media scraping. Saved {saved_count} new posts.")
    return saved_count


if __name__ == "__main__":
    # When run as script, execute the scraper
    run_scraper()