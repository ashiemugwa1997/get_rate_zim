"""
Social media scraping module for ZimRate Predictor

This module contains functions to gather data from social media platforms
about Zimbabwe's currency and economy.
"""

import logging
import datetime
import time
import random
import re
from typing import List, Dict, Any, Optional
from django.utils import timezone
from django.conf import settings

from rate_predictor.scrapers.relevance_detector import is_relevant
from rate_predictor.scrapers.web_utils import get_random_headers, safe_get

# Configure logging
logger = logging.getLogger("social_scraper")

# Flag to track if tweepy is available
TWEEPY_AVAILABLE = False

# Try to import tweepy, but handle if it's not available
try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    logger.warning("Tweepy not found. Twitter scraping functionality will be disabled.")

# Twitter search keywords
TWITTER_KEYWORDS = [
    "zimbabwe dollar", "zwl", "zim dollar", "rtgs", 
    "exchange rate", "forex", "rbz", "reserve bank", 
    "parallel market", "black market", "zimbabwe currency"
]


def get_twitter_api():
    """Configure Twitter API client with credentials."""
    if not TWEEPY_AVAILABLE:
        logger.warning("Tweepy library not available. Cannot initialize Twitter API.")
        return None
        
    try:
        auth = tweepy.OAuthHandler(
            settings.TWITTER_API_KEY, 
            settings.TWITTER_API_SECRET
        )
        auth.set_access_token(
            settings.TWITTER_ACCESS_TOKEN, 
            settings.TWITTER_ACCESS_SECRET
        )
        api = tweepy.API(auth, wait_on_rate_limit=True)
        
        # Test the credentials
        api.verify_credentials()
        logger.info("Twitter API initialized successfully")
        return api
    except Exception as e:
        logger.error(f"Twitter API initialization error: {e}")
        return None


def scrape_twitter_posts(keywords: List[str] = None, days_back: int = 7) -> List[Dict]:
    """
    Scrape Twitter posts related to Zimbabwe's currency using the Twitter API.
    
    Args:
        keywords: List of keywords to search for (default uses predefined list)
        days_back: Number of days back to scrape
        
    Returns:
        List of post dictionaries
    """
    posts = []
    api = get_twitter_api()
    
    if not api:
        logger.error("Twitter API not initialized")
        return posts
    
    # Use provided keywords or default list
    search_keywords = keywords or TWITTER_KEYWORDS
    
    # Construct search query - combine keywords with OR
    query = " OR ".join([f'"{k}"' for k in search_keywords])
    query += " lang:en"  # Limit to English tweets
    
    cutoff_date = timezone.now() - datetime.timedelta(days=days_back)
    max_tweets = 300  # Limit the number of tweets to process
    
    logger.info(f"Searching Twitter for: {query}")
    
    try:
        # Search for tweets
        tweets = tweepy.Cursor(
            api.search_tweets,
            q=query,
            lang="en",
            tweet_mode="extended",
            count=100,
            result_type="mixed"  # Get a mix of popular and recent tweets
        ).items(max_tweets)
        
        tweet_count = 0
        relevant_count = 0
        
        for tweet in tweets:
            tweet_count += 1
            
            # Check if tweet is within our time range
            created_at = tweet.created_at
            if created_at.replace(tzinfo=timezone.utc) < cutoff_date:
                continue
            
            # Skip retweets (we want original content)
            if hasattr(tweet, 'retweeted_status'):
                continue
                
            # Get the full text
            if hasattr(tweet, 'full_text'):
                content = tweet.full_text
            else:
                content = tweet.text
                
            # Skip short tweets and likely irrelevant ones
            if len(content) < 30:
                continue
                
            # Check relevance
            title = f"Tweet by {tweet.user.screen_name}"
            if not is_relevant(title, content):
                continue
                
            relevant_count += 1
            
            # Create post dictionary
            post = {
                "source_name": f"Twitter {tweet.user.screen_name}",
                "content": content,
                "published_at": created_at,
                "platform": "Twitter",
                "url": f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}",
                "followers": tweet.user.followers_count,
                "retweets": tweet.retweet_count,
                "likes": tweet.favorite_count
            }
            posts.append(post)
            
            # Avoid hitting rate limits
            if tweet_count % 50 == 0:
                time.sleep(1)
                
        logger.info(f"Scraped {tweet_count} tweets, {relevant_count} were relevant")
        
    except tweepy.TweepyException as e:
        logger.error(f"Twitter API error: {e}")
    except Exception as e:
        logger.error(f"Error scraping Twitter: {e}")
    
    return posts


def calculate_influence_score(post: Dict[str, Any]) -> float:
    """
    Calculate an influence score for a social media post.
    
    Args:
        post: Dictionary with post data
        
    Returns:
        Influence score between 0.0 and 1.0
    """
    # Base score
    score = 0.2
    
    # Add points based on engagement
    if post.get('platform') == 'Twitter':
        followers = post.get('followers', 0)
        retweets = post.get('retweets', 0)
        likes = post.get('likes', 0)
        
        # Followers impact (capped)
        if followers > 100000:
            score += 0.3
        elif followers > 10000:
            score += 0.2
        elif followers > 1000:
            score += 0.1
        
        # Engagement impact
        engagement = (retweets * 2) + likes
        if engagement > 1000:
            score += 0.3
        elif engagement > 100:
            score += 0.2
        elif engagement > 10:
            score += 0.1
            
        # Check for verified accounts
        if post.get('verified', False):
            score += 0.1
    
    # Check for mentions of banks or government institutions
    important_entities = [
        "reserve bank", "rbz", "ministry of finance", "government", 
        "central bank", "treasury", "imf", "world bank"
    ]
    
    content = post.get('content', '').lower()
    for entity in important_entities:
        if entity in content:
            score += 0.05  # Max 0.25 for entity mentions
            
    # Cap the score at 1.0
    return min(1.0, score)


def save_posts_to_db(posts: List[Dict[str, Any]]) -> int:
    """
    Save scraped social media posts to the database.
    
    Args:
        posts: List of post dictionaries
        
    Returns:
        Number of posts saved to database
    """
    # Import models here to avoid circular imports
    from rate_predictor.models import SocialMediaSource, Post
    
    saved_count = 0
    
    for post_data in posts:
        try:
            # Check if post already exists to avoid duplicates
            if Post.objects.filter(url=post_data['url']).exists():
                continue
                
            # Get or create the social media source
            source_name = post_data['source_name'].split(' ')[1] if ' ' in post_data['source_name'] else post_data['source_name']
            
            source, created = SocialMediaSource.objects.get_or_create(
                name=source_name,
                platform=post_data['platform'],
                defaults={
                    'account_id': source_name,
                    'influence_score': 0.5,
                    'is_active': True
                }
            )
            
            # Calculate influence score for this post
            impact_score = calculate_influence_score(post_data)
            
            # Create the post
            Post.objects.create(
                source_type='social',
                social_source=source,
                content=post_data['content'],
                url=post_data['url'],
                published_at=post_data['published_at'],
                sentiment='neutral',  # Default sentiment, will be updated by analyzer
                sentiment_score=0.0,  # Default sentiment score
                impact_score=impact_score
            )
            
            saved_count += 1
            logger.info(f"Saved social media post from {source_name}")
            
        except Exception as e:
            logger.error(f"Error saving social media post to database: {e}")
            continue
    
    logger.info(f"Saved {saved_count} new social media posts")
    return saved_count


def scrape_key_accounts(days_back: int = 7) -> List[Dict[str, Any]]:
    """
    Scrape posts from key financial accounts/sources.
    
    Args:
        days_back: Number of days to scrape
        
    Returns:
        List of post dictionaries
    """
    from rate_predictor.models import SocialMediaSource
    
    posts = []
    api = get_twitter_api()
    
    if not api:
        return posts
    
    # Get key accounts from database
    key_accounts = SocialMediaSource.objects.filter(
        platform='Twitter',
        is_active=True,
        influence_score__gte=0.7
    )
    
    for account in key_accounts:
        try:
            logger.info(f"Scraping tweets from {account.name}")
            
            # Get tweets from this user
            user_tweets = api.user_timeline(
                screen_name=account.account_id,
                count=50,
                tweet_mode="extended"
            )
            
            cutoff_date = timezone.now() - datetime.timedelta(days=days_back)
            
            for tweet in user_tweets:
                # Check if within time range
                if tweet.created_at.replace(tzinfo=timezone.utc) < cutoff_date:
                    continue
                
                # Get the full text
                if hasattr(tweet, 'full_text'):
                    content = tweet.full_text
                else:
                    content = tweet.text
                
                # Check relevance - for key accounts, use a lower threshold
                title = f"Tweet by {tweet.user.screen_name}"
                if not is_relevant(title, content, threshold=0.3):
                    continue
                
                # Add to our results
                posts.append({
                    "source_name": f"Twitter {tweet.user.screen_name}",
                    "content": content,
                    "published_at": tweet.created_at,
                    "platform": "Twitter",
                    "url": f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}",
                    "followers": tweet.user.followers_count,
                    "retweets": tweet.retweet_count,
                    "likes": tweet.favorite_count,
                    "verified": tweet.user.verified
                })
                
            # Avoid hitting rate limits
            time.sleep(1)
            
        except tweepy.TweepyException as e:
            logger.error(f"Twitter API error for {account.name}: {e}")
        except Exception as e:
            logger.error(f"Error scraping tweets from {account.name}: {e}")
    
    return posts


def run_scraper(days_back: int = 7, initial_scrape: bool = False) -> int:
    """
    Run the social media scraper.
    
    Args:
        days_back: Number of days back to scrape
        initial_scrape: Whether this is an initial scrape
        
    Returns:
        Number of posts saved
    """
    logger.info(f"Starting social media scraper for past {days_back} days")
    
    # Adjust days back for initial scrape
    if initial_scrape:
        days_back = 30  # For initial scrape, go back a month
        logger.info(f"Initial scrape - extending to {days_back} days")
    
    # Get posts from keyword search
    keyword_posts = scrape_twitter_posts(days_back=days_back)
    logger.info(f"Scraped {len(keyword_posts)} posts from keyword search")
    
    # Get posts from key accounts
    account_posts = scrape_key_accounts(days_back=days_back)
    logger.info(f"Scraped {len(account_posts)} posts from key accounts")
    
    # Combine results
    all_posts = keyword_posts + account_posts
    
    # Sort by date, newest first
    all_posts.sort(key=lambda x: x["published_at"], reverse=True)
    
    # Save to database
    saved_count = save_posts_to_db(all_posts)
    
    logger.info(f"Social media scraping completed. Total posts saved: {saved_count}")
    return saved_count


if __name__ == "__main__":
    # For testing the scraper from command line
    run_scraper(days_back=7, initial_scrape=False)