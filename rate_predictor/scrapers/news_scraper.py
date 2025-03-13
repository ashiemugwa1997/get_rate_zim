"""
News scraper module for ZimRate Predictor

This module contains functions to scrape news articles from top Zimbabwean news websites.
The scraped data is used for sentiment analysis and exchange rate prediction.
"""

import datetime
import logging
import re
import time
from typing import List, Dict, Any, Optional
from django.utils import timezone
import random
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from django.conf import settings
from rate_predictor.scrapers.web_utils import fetch_url, get_retry_session, get_random_headers, safe_get
from rate_predictor.scrapers.relevance_detector import is_relevant

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("news_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("news_scraper")

# Keywords for simple relevance detection fallback
CURRENCY_KEYWORDS = [
    "zimbabwe dollar", "zwl", "zim dollar", "rtgs", "bond note",
    "exchange rate", "forex", "rbz", "reserve bank", "zim currency",
    "parallel market", "black market", "usd", "us dollar"
]

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
    # Keep other sources...
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

def simple_keyword_relevance(title: str, content: str) -> bool:
    """Simple keyword-based relevance detection."""
    combined_text = (title + " " + content).lower()
    
    # Check if any of our currency keywords are in the text
    for keyword in CURRENCY_KEYWORDS:
        if keyword in combined_text:
            return True
            
    return False

def get_page_url(base_url: str, page: int) -> str:
    """Generate URL for pagination based on the website structure."""
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
    scrape_config = getattr(settings, 'SCRAPING', {})
    max_articles = scrape_config.get('MAX_ARTICLES_PER_SOURCE', 100)
    
    try:
        logger.info(f"Starting to scrape articles from {source['name']}")
        
        for page in range(1, source["max_pages"] + 1):
            # Get URL for current page
            current_url = get_page_url(source["url"], page)
            logger.info(f"Scraping page {page}: {current_url}")
            
            # Using improved fetch utility
            response = safe_get(
                current_url,
                timeout=scrape_config.get('REQUEST_TIMEOUT', 15)
            )
            
            if not response:
                logger.error(f"Failed to fetch page {page} from {source['name']}")
                continue
            
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
                if len(articles) >= max_articles:
                    logger.info(f"Reached maximum articles limit ({max_articles}) for {source['name']}")
                    break
                    
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
                    
                    # Fetch full article content using our backoff-enabled fetch_url
                    article_html = fetch_url(article_url)
                    if not article_html:
                        continue
                        
                    # Extract main text content
                    content = extract_article_text(article_html, source["content_selector"])
                    
                    # Check if the article is relevant to our topic using our enhanced detector
                    if not is_relevant(title, content, scrape_config.get('RELEVANCE_THRESHOLD', 0.4)):
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
            
            # Avoid overloading the server - get delay from settings
            delay = scrape_config.get('DEFAULT_DELAY', 2)
            time.sleep(random.uniform(delay, delay * 1.5))
            
            if len(articles) >= max_articles:
                break
            
    except Exception as e:
        logger.error(f"Unexpected error while scraping {source['name']}: {e}")
    
    logger.info(f"Finished scraping {source['name']}. Found {len(articles)} relevant articles")
    return articles

def scrape_all_news_sources(days_back: int = 7, sources: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Scrape articles from all configured news sources.
    
    Args:
        days_back: Number of days back to consider articles from
        sources: Optional list of specific sources to scrape
        
    Returns:
        List of all scraped articles across all sources
    """
    all_articles = []
    sources_to_scrape = sources or NEWS_SOURCES
    
    for source in sources_to_scrape:
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
    
    Args:
        articles: List of article dictionaries
        
    Returns:
        Number of articles saved to database
    """
    # Import models here to avoid circular imports
    from rate_predictor.models import NewsSource, Post
    from django.utils import timezone
    
    saved_count = 0
    
    for article in articles:
        try:
            # Check if article already exists to avoid duplicates
            if not Post.objects.filter(url=article['url']).exists():
                # Get or create the news source
                source, created = NewsSource.objects.get_or_create(
                    name=article['source_name'],
                    defaults={
                        'url': article['url'].split('/')[0] + '//' + article['url'].split('/')[2],
                        'reliability_score': 0.7, 
                        'is_active': True
                    }  
                )
                
                # Create the post
                Post.objects.create(
                    source_type='news',
                    news_source=source,
                    content=article['content'],
                    url=article['url'],
                    published_at=timezone.make_aware(
                        datetime.datetime.combine(article['published_at'], datetime.time())
                    ),
                    sentiment='neutral',  # Default sentiment
                    sentiment_score=0.0   # Will be updated by sentiment analyzer
                )
                saved_count += 1
                logger.info(f"Saved article: {article.get('title', 'Untitled')}")
        except Exception as e:
            logger.error(f"Error saving article to database: {e}")
            continue
    
    logger.info(f"Saved {saved_count} new articles to database")
    return saved_count

def run_news_scraper(days_back: int = 7, initial_scrape: bool = False, sources: List[str] = None) -> int:
    """
    Run the news scraper to collect articles
    
    Args:
        days_back: Number of days back to consider
        initial_scrape: Whether this is the initial scrape for the last 2 years
        sources: Optional list of specific source names to scrape (for selective updates)
        
    Returns:
        Number of articles scraped and saved
    """
    if initial_scrape:
        days_back = 365 * 2  # Scrape the last 2 years of news articles
        logger.info(f"Starting initial news scraping process for the past {days_back} days (2 years)")
    else:
        logger.info(f"Starting news scraping process for the past {days_back} days")
    
    # Filter sources if specified
    filtered_sources = None
    if sources:
        filtered_sources = [s for s in NEWS_SOURCES if s['name'] in sources]
        if not filtered_sources:
            logger.warning(f"No matching sources found for: {sources}")
            return 0
        logger.info(f"Using filtered sources: {[s['name'] for s in filtered_sources]}")
    
    # Scrape articles from news sources
    articles = scrape_all_news_sources(days_back, filtered_sources)
    
    # Save articles to the database
    saved_count = save_articles_to_db(articles)
    
    # Update the model based on whether this is initial or incremental
    try:
        if initial_scrape:
            train_model_with_initial_data()
        else:
            update_model_incrementally(days_back)
    except Exception as e:
        logger.error(f"Error updating model: {e}")
        # Continue anyway, as we've already saved the articles
    
    logger.info(f"Completed news scraping. Saved {saved_count} new articles.")
    return saved_count

def train_model_with_initial_data() -> None:
    """
    Train the model using the initial data scraped from the last 2 years.
    This is a placeholder for the actual model training functionality.
    """
    logger.info("Training model with initial data...")
    # This would contain the actual model training code

def update_model_incrementally(days_back: int = 7) -> None:
    """
    Update the model incrementally with new data.
    This is a placeholder for the actual model update functionality.
    """
    logger.info(f"Incrementally updating model with data from the past {days_back} days...")
    # This would contain the actual incremental model update code

async def scrape_articles_async(source: Dict[str, Any], days_back: int) -> List[Dict[str, Any]]:
    """
    Asynchronously scrape articles from a source.
    This is a placeholder for the async implementation.
    """
    # This would contain the async implementation as described in the specification
    logger.warning("Async scraping not yet implemented, falling back to synchronous scraping")
    return scrape_articles_from_source(source, days_back)

async def run_news_scraper_async(days_back: int = 7) -> int:
    """
    Run the news scraper asynchronously for better performance.
    This is a placeholder for the async implementation.
    """
    # This would contain the async implementation as described in the specification
    logger.warning("Async scraping not fully implemented, falling back to synchronous scraping")
    return run_news_scraper(days_back)

if __name__ == "__main__":
    # For testing the scraper from command line
    run_news_scraper(days_back=3, initial_scrape=False)

# New function to fetch last 2000 articles and train ML model
def fetch_and_train_model() -> None:
    logger.info("Fetching last 2000 articles and training ML model...")
    articles = scrape_all_news_sources(days_back=365 * 2)  # Adjust days_back to fetch more articles
    save_articles_to_db(articles)
    train_model_with_initial_data()
    logger.info("Model training completed.")