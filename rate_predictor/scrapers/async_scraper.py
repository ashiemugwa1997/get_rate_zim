"""
Asynchronous web scraping module for ZimRate Predictor

This module provides asynchronous scraping capabilities to improve
performance when collecting data from multiple sources.
"""

import aiohttp
import asyncio
import logging
import random
import time
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from django.utils import timezone
from django.conf import settings

from rate_predictor.scrapers.web_utils import get_random_headers
from rate_predictor.scrapers.news_scraper import (
    extract_date, extract_article_text, NEWS_SOURCES, get_page_url
)
from rate_predictor.scrapers.relevance_detector import is_relevant

# Configure logging
logger = logging.getLogger("async_scraper")

async def fetch_url_async(url: str, session: aiohttp.ClientSession) -> Optional[str]:
    """
    Asynchronously fetch content from URL with error handling.
    
    Args:
        url: URL to fetch
        session: aiohttp ClientSession to use
        
    Returns:
        HTML content as string or None if failed
    """
    scrape_config = getattr(settings, 'SCRAPING', {})
    timeout = aiohttp.ClientTimeout(total=scrape_config.get('REQUEST_TIMEOUT', 15))
    
    try:
        headers = get_random_headers()
        async with session.get(url, headers=headers, timeout=timeout) as response:
            if response.status != 200:
                logger.warning(f"Non-200 status code ({response.status}) for {url}")
                return None
            return await response.text()
    except asyncio.TimeoutError:
        logger.error(f"Timeout fetching {url}")
        return None
    except aiohttp.ClientError as e:
        logger.error(f"aiohttp client error fetching {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return None

async def scrape_articles_async(source: Dict[str, Any], days_back: int) -> List[Dict[str, Any]]:
    """
    Asynchronously scrape articles from a source.
    
    Args:
        source: Dictionary containing information about the news source
        days_back: Number of days back to consider articles from
        
    Returns:
        List of dictionaries containing scraped articles
    """
    articles = []
    cutoff_date = timezone.now().date() - timezone.timedelta(days=days_back)
    scrape_config = getattr(settings, 'SCRAPING', {})
    max_articles = scrape_config.get('MAX_ARTICLES_PER_SOURCE', 100)
    
    # Connector with connection limiting and other options
    conn = aiohttp.TCPConnector(
        limit=10,  # Limit number of simultaneous connections
        enable_cleanup_closed=True,
        force_close=True,
        ssl=False  # Don't verify SSL for better performance
    )
    
    async with aiohttp.ClientSession(connector=conn, trust_env=True) as session:
        # First fetch and parse index pages to collect article URLs
        logger.info(f"Starting to asynchronously scrape articles from {source['name']}")
        
        article_urls = []
        article_titles = []
        article_dates = []
        
        # Process each page of the source
        for page in range(1, source["max_pages"] + 1):
            current_url = get_page_url(source["url"], page)
            logger.info(f"Scraping page {page}: {current_url}")
            
            # Fetch the index page
            html = await fetch_url_async(current_url, session)
            if not html:
                continue
                
            # Parse the index page
            soup = BeautifulSoup(html, 'html.parser')
            article_elements = soup.select(source["article_selector"])
            
            if not article_elements:
                logger.warning(f"No articles found on page {page} using selector: {source['article_selector']}")
                continue
                
            logger.info(f"Found {len(article_elements)} articles on page {page}")
            
            # Extract URLs, titles, and dates from the index page
            for article in article_elements:
                # Stop if we've reached the maximum number of articles
                if len(article_urls) >= max_articles:
                    break
                    
                # Extract title and URL
                title_element = article.select_one(source["title_selector"])
                if not title_element:
                    continue
                    
                title = title_element.get_text(strip=True)
                url = title_element.get('href')
                
                if not url:
                    continue
                    
                # Make relative URLs absolute
                if not url.startswith(('http://', 'https://')):
                    url = urljoin(source["url"], url)
                
                # Extract date
                date_element = article.select_one(source["date_selector"])
                if not date_element:
                    continue
                    
                date_text = date_element.get_text(strip=True)
                article_date = extract_date(date_text, source["date_format"])
                
                if not article_date or article_date < cutoff_date:
                    # Skip old articles
                    continue
                
                # Add to our lists
                article_urls.append(url)
                article_titles.append(title)
                article_dates.append(article_date)
            
            # Add delay between index pages
            await asyncio.sleep(random.uniform(1, 3))
            
            if len(article_urls) >= max_articles:
                break
        
        # Now fetch and process article content in parallel with rate limiting
        logger.info(f"Found {len(article_urls)} article URLs to process for {source['name']}")
        
        # Process articles in batches to avoid overloading the server
        batch_size = 5  # Process 5 articles at a time
        for i in range(0, len(article_urls), batch_size):
            batch_urls = article_urls[i:i+batch_size]
            batch_titles = article_titles[i:i+batch_size]
            batch_dates = article_dates[i:i+batch_size]
            
            # Create tasks for fetching article content
            tasks = []
            for url in batch_urls:
                # Add small random delay between creating tasks
                await asyncio.sleep(random.uniform(0.1, 0.5))
                tasks.append(fetch_url_async(url, session))
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for url, html, title, article_date in zip(batch_urls, results, batch_titles, batch_dates):
                # Skip if fetch failed
                if html is None or isinstance(html, Exception):
                    continue
                
                try:
                    # Extract main content
                    content = extract_article_text(html, source["content_selector"])
                    
                    # Check relevance
                    if not is_relevant(title, content, scrape_config.get('RELEVANCE_THRESHOLD', 0.4)):
                        continue
                    
                    # Add article to our results
                    articles.append({
                        "title": title,
                        "content": content,
                        "url": url,
                        "published_at": article_date,
                        "source_name": source["name"]
                    })
                    
                    logger.info(f"Scraped article: {title} from {source['name']}")
                    
                except Exception as e:
                    logger.error(f"Error processing article {url}: {e}")
            
            # Add delay between batches
            await asyncio.sleep(random.uniform(1, 2))
    
    logger.info(f"Finished scraping {source['name']}. Found {len(articles)} relevant articles")
    return articles

async def run_news_scraper_async(days_back: int = 7, sources: List[str] = None) -> int:
    """
    Run the news scraper asynchronously for better performance.
    
    Args:
        days_back: Number of days back to consider
        sources: Optional list of specific source names to scrape
        
    Returns:
        Number of scraped articles saved to database
    """
    from rate_predictor.scrapers.news_scraper import save_articles_to_db
    
    logger.info(f"Starting asynchronous news scraping for the past {days_back} days")
    
    all_articles = []
    tasks = []
    
    # Filter sources if specified
    sources_to_scrape = NEWS_SOURCES
    if sources:
        sources_to_scrape = [s for s in NEWS_SOURCES if s['name'] in sources]
        if not sources_to_scrape:
            logger.warning(f"No matching sources found for: {sources}")
            return 0
        logger.info(f"Using filtered sources: {[s['name'] for s in sources_to_scrape]}")
    
    # Create tasks for scraping each source
    for source in sources_to_scrape:
        tasks.append(scrape_articles_async(source, days_back))
    
    # Execute all tasks concurrently and wait for results
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for source, result in zip(sources_to_scrape, results):
        if isinstance(result, Exception):
            logger.error(f"Error scraping {source['name']}: {result}")
        else:
            all_articles.extend(result)
    
    # Sort articles by date, newest first
    all_articles.sort(key=lambda x: x["published_at"], reverse=True)
    logger.info(f"Scraped a total of {len(all_articles)} articles from all sources")
    
    # Save to DB (can't be async unless using async ORM)
    saved_count = save_articles_to_db(all_articles)
    
    # Update model incrementally
    try:
        from rate_predictor.scrapers.news_scraper import update_model_incrementally
        update_model_incrementally(days_back)
    except Exception as e:
        logger.error(f"Error updating model: {e}")
    
    return saved_count