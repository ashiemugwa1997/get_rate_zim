"""
Web utility functions for ZimRate Predictor scraping modules

This module contains shared web scraping utilities to improve robustness
and avoid detection when scraping websites.
"""

import requests
import random
import logging
import time
import backoff
from typing import Dict, Optional, List
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from django.conf import settings
from fake_useragent import UserAgent

# Configure logging
logger = logging.getLogger("web_utils")

# Try to create a UserAgent instance once for reuse
try:
    user_agent_generator = UserAgent()
    UA_AVAILABLE = True
except Exception as e:
    logger.warning(f"Failed to initialize fake_useragent: {e}")
    UA_AVAILABLE = False

# List of fallback user agents if fake_useragent fails
FALLBACK_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
]

def get_random_headers() -> Dict[str, str]:
    """
    Generate random headers to avoid bot detection.
    
    Returns:
        Dictionary with HTTP headers
    """
    try:
        if UA_AVAILABLE:
            ua_string = user_agent_generator.random
        else:
            ua_string = random.choice(FALLBACK_USER_AGENTS)
            
        return {
            "User-Agent": ua_string,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",  # Do Not Track
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    except Exception as e:
        logger.error(f"Error generating random headers: {e}")
        # Return basic headers if all else fails
        return {
            "User-Agent": FALLBACK_USER_AGENTS[0],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }

def get_retry_session(retries: int = None, backoff_factor: float = None) -> requests.Session:
    """
    Create a requests session with retry capabilities.
    
    Args:
        retries: Number of retries to attempt (default from settings)
        backoff_factor: Backoff factor between retries (default from settings)
        
    Returns:
        Requests session with retry configuration
    """
    scrape_config = getattr(settings, 'SCRAPING', {})
    
    if retries is None:
        retries = scrape_config.get('MAX_RETRIES', 3)
    
    if backoff_factor is None:
        backoff_factor = 0.3  # Default backoff factor
    
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "HEAD"],
        raise_on_status=True
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def get_proxies() -> Optional[Dict[str, str]]:
    """
    Get a random proxy from the configured proxy list.
    
    Returns:
        Proxy configuration dict or None if no proxies configured
    """
    scrape_config = getattr(settings, 'SCRAPING', {})
    use_proxies = scrape_config.get('PROXY_ROTATION', False)
    
    if not use_proxies:
        return None
        
    proxy_list = getattr(settings, 'PROXY_LIST', [])
    if not proxy_list:
        return None
        
    proxy = random.choice(proxy_list)
    return {
        "http": proxy,
        "https": proxy
    }

@backoff.on_exception(
    backoff.expo, 
    (requests.exceptions.RequestException, requests.exceptions.Timeout), 
    max_tries=5
)
def fetch_url(url: str, timeout: int = None, use_proxy: bool = None) -> Optional[str]:
    """
    Fetch content from a URL with retry logic.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        use_proxy: Whether to use a proxy (None = use settings value)
        
    Returns:
        HTML content as string or None if failed
    """
    scrape_config = getattr(settings, 'SCRAPING', {})
    
    if timeout is None:
        timeout = scrape_config.get('REQUEST_TIMEOUT', 15)
    
    if use_proxy is None:
        use_proxy = scrape_config.get('PROXY_ROTATION', False)
        
    try:
        session = get_retry_session()
        headers = get_random_headers()
        proxies = get_proxies() if use_proxy else None
        
        logger.debug(f"Fetching URL: {url} (proxy: {'yes' if proxies else 'no'})")
        
        response = session.get(
            url, 
            headers=headers, 
            proxies=proxies,
            timeout=timeout
        )
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch URL {url}: {e}")
        raise  # Let backoff handle it
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        return None

def safe_get(url: str, max_tries: int = 3, delay: float = 2.0, **kwargs) -> Optional[requests.Response]:
    """
    Safely get a URL with multiple retries and error handling.
    
    Args:
        url: URL to fetch
        max_tries: Maximum number of tries
        delay: Delay between retries
        **kwargs: Additional arguments to pass to requests.get
        
    Returns:
        Response object or None if all tries failed
    """
    for attempt in range(max_tries):
        try:
            if attempt > 0:
                # Add jitter to delay
                jittered_delay = delay * (1 + random.random())
                time.sleep(jittered_delay)
                
            session = get_retry_session()
            headers = kwargs.pop('headers', get_random_headers())
            proxies = kwargs.pop('proxies', get_proxies())
            
            response = session.get(
                url,
                headers=headers,
                proxies=proxies,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt+1}/{max_tries} failed for {url}: {e}")
            if attempt == max_tries - 1:
                logger.error(f"All {max_tries} attempts failed for {url}")
                return None
        except Exception as e:
            logger.error(f"Unexpected error while fetching {url}: {e}")
            return None
            
    return None