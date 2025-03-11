"""
News scraper module for ZimRate Predictor

This module contains functions to scrape news articles from top Zimbabwean news websites.
The scraped data is used for sentiment analysis and exchange rate prediction.
"""

import requests
from bs4 import BeautifulSoup
import datetime
import logging
import re
import time
from typing import List, Dict, Any, Optional
from django.utils import timezone
import random
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname=s - %(message)s',
    handlers=[
        logging.FileHandler("news_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("news_scraper")

# List of top Zimbabwean news websites to scrape
NEWS_SOURCES = [
    {
        "name": "The Herald",
        "url": "https://www.herald.co.zw/category/business/",
        "article_selector": "article.entry",
        "title_selector": "h2.entry-title a",
        "content_selector": ".entry-content",
        "date_selector": ".entry-date",
        "date_format": "%B %d, %Y",
        "max_pages": 2
    },
    {
        "name": "NewsDay Zimbabwe",
        "url": "https://www.newsday.co.zw/business/",
        "article_selector": "article",
        "title_selector": "h3 a",
        "content_selector": ".entry-content",
        "date_selector": ".entry-date",
        "date_format": "%B %d, %Y",
        "max_pages": 2
    },
    {
        "name": "Chronicle",
        "url": "https://www.chronicle.co.zw/category/business/",
        "article_selector": "article.entry",
        "title_selector": "h2.entry-title a",
        "content_selector": ".entry-content",
        "date_selector": ".entry-date",
        "date_format": "%B %d, %Y",
        "max_pages": 2
    },
    {
        "name": "The Zimbabwe Independent",
        "url": "https://www.theindependent.co.zw/category/business/",
        "article_selector": "article",
        "title_selector": "h2.entry-title a",
        "content_selector": ".entry-content",
        "date_selector": ".entry-date",
        "date_format": "%B %d, %Y",
        "max_pages": 2
    },
    {
        "name": "Zimbabwe Situation",
        "url": "https://www.zimbabwesituation.com/news/category/business-news/",
        "article_selector": "article",
        "title_selector": "h2.entry-title a",
        "content_selector": ".entry-content",
        "date_selector": ".entry-date",
        "date_format": "%B %d, %Y",
        "max_pages": 2
    },
    {
        "name": "Bulawayo24",
        "url": "https://bulawayo24.com/index-id-business.html",
        "article_selector": ".story",
        "title_selector": "h3 a",
        "content_selector": ".article-body",
        "date_selector": ".story-date",
        "date_format": "%d %b %Y",
        "max_pages": 2
    },
    {
        "name": "Financial Gazette",
        "url": "https://www.financialgazette.co.zw/category/economy/",
        "article_selector": "article",
        "title_selector": "h2 a",
        "content_selector": ".entry-content",
        "date_selector": ".entry-date",
        "date_format": "%B %d, %Y",
        "max_pages": 2
    },
    {
        "name": "New Zimbabwe",
        "url": "https://www.newzimbabwe.com/business-news/",
        "article_selector": "article",
        "title_selector": "h3.entry-title a",
        "content_selector": ".entry-content",
        "date_selector": ".entry-date",
        "date_format": "%B %d, %Y",
        "max_pages": 2
    },
    {
        "name": "TechZim",
        "url": "https://www.techzim.co.zw/category/business/",
        "article_selector": "article",
        "title_selector": "h2.entry-title a",
        "content_selector": ".entry-content",
        "date_selector": ".entry-date",
        "date_format": "%B %d, %Y",
        "max_pages": 2
    },
    {
        "name": "ZimEye",
        "url": "https://www.zimeye.net/category/business/",
        "article_selector": "article",
        "title_selector": "h3.entry-title a",
        "content_selector": ".entry-content",
        "date_selector": ".entry-date",
        "date_format": "%B %d, %Y",
        "max_pages": 2
    }
]

# Headers to rotate when making requests to avoid detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36"
]

# Keywords to filter articles related to currency and economy
CURRENCY_KEYWORDS = [
    "zimbabwe dollar", "zwl", "zimbabwe currency", "zimbabwean dollar", "zim dollar",
    "exchange rate", "forex", "foreign exchange", "currency depreciation", "currency appreciation",
    "rbz", "reserve bank", "monetary policy", "inflation", "bond note", "nostro",
    "parallel market", "black market", "interbank rate", "auction system", "us dollar",
    "usd", "foreign currency", "currency trading", "currency manipulation", "devaluation"
]


def get_random_headers() -> Dict[str, str]:
    """Generate random headers to avoid bot detection."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def extract_date(date_text: str, date_format: str) -> Optional[datetime.date]:
    """Extract date from text using specified format."""
    try:
        # Clean the date text (remove extra spaces, etc.)
        clean_date = re.sub(r'\s+', ' ', date_text).strip()
        parsed_date = datetime.datetime.strptime(clean_date, date_format).date()
        return parsed_date
    except ValueError as e:
        logger.error(f"Failed to parse date '{date_text}' with format '{date_format}': {e}")
        return None


def fetch_article_content(url: str) -> Optional[str]:
    """Fetch the full content of an article from its URL."""
    try:
        response = requests.get(url, headers=get_random_headers(), timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"Failed to fetch article content from {url}: {e}")
        return None


def extract_article_text(html_content: str, content_selector: str) -> str:
    """Extract the main text content from an article HTML."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        content_element = soup.select_one(content_selector)
        
        if content_element:
            # Remove unwanted elements like ads, social buttons, etc.
            for unwanted in content_element.select('script, .social-share, .advertisement, .related-posts, iframe'):
                unwanted.extract()
                
            # Get text and clean it
            text = content_element.get_text(separator=' ', strip=True)
            text = re.sub(r'\s+', ' ', text)
            return text
        return ""
    except Exception as e:
        logger.error(f"Error extracting article text: {e}")
        return ""


def is_relevant_article(title: str, content: str) -> bool:
    """Check if an article is relevant to currency/economy based on keywords."""
    combined_text = (title + " " + content).lower()
    
    # Check if any of our currency keywords are in the text
    for keyword in CURRENCY_KEYWORDS:
        if keyword in combined_text:
            return True
            
    return False


def get_page_url(base_url: str, page: int) -> str:
    """Generate URL for pagination based on the website structure."""
    # Different sites have different pagination structures
    if "herald.co.zw" in base_url or "chronicle.co.zw" in base_url:
        return f"{base_url}page/{page}/" if page > 1 else base_url
    elif "newsday.co.zw" in base_url:
        return f"{base_url}?page={page}" if page > 1 else base_url
    elif "bulawayo24.com" in base_url:
        # Bulawayo24 has special pagination
        return f"{base_url.replace('.html', '')}-{page}.html" if page > 1 else base_url
    else:
        # Generic pagination pattern
        return f"{base_url}/page/{page}" if page > 1 else base_url


def scrape_articles_from_source(source: Dict[str, Any], days_back: int = 7) -> List[Dict[str, Any]]:
    """
    Scrape articles from a specific news source.
    
    Args:
        source: Dictionary containing information about the news source
        days_back: Number of days back to consider articles from
        
    Returns:
        List of dictionaries containing scraped articles
    """
    articles = []
    cutoff_date = timezone.now().date() - datetime.timedelta(days=days_back)
    
    try:
        logger.info(f"Starting to scrape articles from {source['name']}")
        
        for page in range(1, source["max_pages"] + 1):
            # Get URL for current page
            current_url = get_page_url(source["url"], page)
            logger.info(f"Scraping page {page}: {current_url}")
            
            # Fetch page content
            response = requests.get(current_url, headers=get_random_headers(), timeout=15)
            response.raise_for_status()
            
            # Parse the page HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all articles on the page
            article_elements = soup.select(source["article_selector"])
            
            if not article_elements:
                logger.warning(f"No articles found on page {page} using selector: {source['article_selector']}")
                continue
                
            logger.info(f"Found {len(article_elements)} articles on page {page}")
            
            # Process each article
            for article in article_elements:
                try:
                    # Extract article title
                    title_element = article.select_one(source["title_selector"])
                    if not title_element:
                        continue
                        
                    title = title_element.get_text(strip=True)
                    
                    # Extract article URL
                    article_url = title_element.get('href')
                    if not article_url:
                        continue
                        
                    # Make relative URLs absolute
                    if not article_url.startswith(('http://', 'https://')):
                        article_url = urljoin(source["url"], article_url)
                    
                    # Extract date
                    date_element = article.select_one(source["date_selector"])
                    if not date_element:
                        # Skip articles without dates
                        continue
                        
                    date_text = date_element.get_text(strip=True)
                    article_date = extract_date(date_text, source["date_format"])
                    
                    if not article_date or article_date < cutoff_date:
                        # Skip old articles
                        continue
                    
                    # Fetch full article content
                    article_html = fetch_article_content(article_url)
                    if not article_html:
                        continue
                        
                    # Extract main text content
                    content = extract_article_text(article_html, source["content_selector"])
                    
                    # Check if the article is relevant to our topic
                    if not is_relevant_article(title, content):
                        continue
                    
                    # Add the article to our results
                    articles.append({
                        "title": title,
                        "content": content,
                        "url": article_url,
                        "published_at": article_date,
                        "source_name": source["name"]
                    })
                    
                    logger.info(f"Scraped article: {title} from {source['name']}")
                    
                except Exception as e:
                    logger.error(f"Error processing article: {e}")
                    continue
            
            # Avoid overloading the server
            time.sleep(random.uniform(1, 3))
            
    except requests.RequestException as e:
        logger.error(f"Failed to fetch page from {source['name']}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while scraping {source['name']}: {e}")
    
    logger.info(f"Finished scraping {source['name']}. Found {len(articles)} relevant articles")
    return articles


def scrape_all_news_sources(days_back: int = 7) -> List[Dict[str, Any]]:
    """
    Scrape articles from all configured news sources.
    
    Args:
        days_back: Number of days back to consider articles from
        
    Returns:
        List of all scraped articles across all sources
    """
    all_articles = []
    
    for source in NEWS_SOURCES:
        try:
            source_articles = scrape_articles_from_source(source, days_back)
            all_articles.extend(source_articles)
            
            # Avoid overloading servers or getting blocked
            time.sleep(random.uniform(2, 5))
        except Exception as e:
            logger.error(f"Error scraping source {source['name']}: {e}")
    
    # Sort articles by date, newest first
    all_articles.sort(key=lambda x: x["published_at"], reverse=True)
    
    logger.info(f"Scraped a total of {len(all_articles)} articles from all sources")
    return all_articles


def save_articles_to_db(articles: List[Dict[str, Any]]) -> int:
    """
    Save scraped articles to the database.
    
    This function would interact with Django models to save the data.
    Would need to be implemented based on your exact model structure.
    
    Args:
        articles: List of article dictionaries
        
    Returns:
        Number of articles saved to database
    """
    # This is a placeholder for the actual implementation
    # In a real application, you would import your Django models and save to database
    
    # Example pseudo-code:
    # from rate_predictor.models import NewsSource, Post
    # 
    # saved_count = 0
    # for article in articles:
    #     # Check if article already exists to avoid duplicates
    #     if not Post.objects.filter(url=article['url']).exists():
    #         # Get or create the news source
    #         source, _ = NewsSource.objects.get_or_create(
    #             name=article['source_name'],
    #             defaults={'reliability_score': 0.7, 'is_active': True}  
    #         )
    #         
    #         # Create the post
    #         Post.objects.create(
    #             title=article['title'],
    #             content=article['content'],
    #             url=article['url'],
    #             published_at=article['published_at'],
    #             source_type='news',
    #             news_source=source
    #         )
    #         saved_count += 1
    # 
    # return saved_count
    
    return len(articles)  # Placeholder


def run_news_scraper(days_back: int = 7, initial_scrape: bool = False) -> int:
    """
    Run the news scraper to collect articles
    
    Args:
        days_back: Number of days back to consider
        initial_scrape: Whether this is the initial scrape for the last 2 years
        
    Returns:
        Number of articles scraped and saved
    """
    if initial_scrape:
        days_back = 365 * 2  # Scrape the last 2 years of news articles
        logger.info(f"Starting initial news scraping process for the past {days_back} days (2 years)")
    else:
        logger.info(f"Starting news scraping process for the past {days_back} days")
    
    # Scrape articles from all news sources
    articles = scrape_all_news_sources(days_back)
    
    # Save articles to the database
    saved_count = save_articles_to_db(articles)
    
    logger.info(f"Completed news scraping. Saved {saved_count} new articles.")
    return saved_count


def train_model_with_initial_data() -> None:
    """
    Train the model using the initial data scraped from the last 2 years.
    
    This is a placeholder function. Implement the actual model training logic here.
    """
    logger.info("Training model with initial data...")
    # Placeholder for model training logic
    # For example, load the scraped articles from the database and train the model
    # train_model(articles)
    logger.info("Model training completed.")

if __name__ == "__main__":
    # For testing the scraper from command line
    run_news_scraper(days_back=3, initial_scrape=True)