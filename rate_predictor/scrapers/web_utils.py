"""
Web utilities for scraping operations with robust error handling and retry mechanisms.

This module provides functions for making robust HTTP requests with features like:
- Automatic retries with exponential backoff
- Timeout handling
- User-agent rotation
- Proxy support
- Error handling for common HTTP/network issues
"""

import time
import random
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Any, Optional, Tuple, List, Union
from requests import Response, Session

logger = logging.getLogger(__name__)

# List of common user agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
]

def get_random_headers() -> Dict[str, str]:
    """
    Generate random headers with a rotated user agent to avoid detection.
    
    Returns:
        Dictionary of HTTP headers
    """
    user_agent = random.choice(USER_AGENTS)
    
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    return headers

def get_retry_session(
    retries: int = 3,
    backoff_factor: float = 0.3,
    status_forcelist: Tuple = (429, 500, 502, 503, 504),
    allowed_methods: List[str] = None
) -> Session:
    """
    Create a requests Session with retry capabilities.
    
    Args:
        retries: Maximum number of retries
        backoff_factor: Exponential backoff factor
        status_forcelist: Status codes that trigger a retry
        allowed_methods: HTTP methods to retry (defaults to all)
        
    Returns:
        Requests Session with retry configuration
    """
    if allowed_methods is None:
        allowed_methods = ["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"]
        
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=allowed_methods
    )
    
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    return session

def safe_get(
    url: str,
    headers: Dict[str, str] = None,
    timeout: int = 10,
    retries: int = 3,
    proxies: Dict[str, str] = None
) -> Optional[Response]:
    """
    Make a GET request with error handling and retries.
    
    Args:
        url: URL to request
        headers: HTTP headers (will use random headers if None)
        timeout: Request timeout in seconds
        retries: Maximum number of retries
        proxies: Optional proxy configuration
        
    Returns:
        Response object or None if request failed
    """
    if headers is None:
        headers = get_random_headers()
        
    session = get_retry_session(retries=retries)
    
    try:
        response = session.get(
            url,
            headers=headers,
            timeout=timeout,
            proxies=proxies
        )
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logger.error(f"Error requesting {url}: {str(e)}")
        return None

def safe_post(
    url: str,
    data: Dict[str, Any] = None,
    json: Dict[str, Any] = None,
    headers: Dict[str, str] = None,
    timeout: int = 10,
    retries: int = 3,
    proxies: Dict[str, str] = None
) -> Optional[Response]:
    """
    Make a POST request with error handling and retries.
    
    Args:
        url: URL to request
        data: Form data to post
        json: JSON data to post
        headers: HTTP headers (will use random headers if None)
        timeout: Request timeout in seconds
        retries: Maximum number of retries
        proxies: Optional proxy configuration
        
    Returns:
        Response object or None if request failed
    """
    if headers is None:
        headers = get_random_headers()
        
    session = get_retry_session(retries=retries)
    
    try:
        response = session.post(
            url,
            data=data,
            json=json,
            headers=headers,
            timeout=timeout,
            proxies=proxies
        )
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logger.error(f"Error posting to {url}: {str(e)}")
        return None

def fetch_url(url: str, max_retries: int = 3) -> Optional[str]:
    """
    Fetch URL content with retries and error handling.
    
    Args:
        url: URL to fetch
        max_retries: Maximum number of retries
        
    Returns:
        HTML content as string or None if failed
    """
    for attempt in range(max_retries):
        try:
            response = safe_get(
                url, 
                timeout=15,
                retries=max_retries - attempt
            )
            
            if response and response.status_code == 200:
                return response.text
                
            if attempt < max_retries - 1:
                # Add exponential backoff
                sleep_time = 2 ** attempt + random.uniform(0, 1)
                time.sleep(sleep_time)
                
        except Exception as e:
            logger.error(f"Error fetching {url} (attempt {attempt+1}): {e}")
            
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt + random.uniform(0, 1))
    
    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
    return None

def get_proxy_list() -> List[Dict[str, str]]:
    """
    Get a list of proxy configurations from settings.
    Falls back to empty list if no proxies configured.
    
    Returns:
        List of proxy configurations
    """
    try:
        from django.conf import settings
        proxy_list = getattr(settings, 'PROXY_LIST', [])
        
        formatted_proxies = []
        for proxy in proxy_list:
            if proxy and proxy.strip():
                formatted_proxies.append({
                    'http': f'http://{proxy}',
                    'https': f'http://{proxy}'
                })
        
        return formatted_proxies
    except (ImportError, AttributeError):
        return []

def get_random_proxy() -> Dict[str, str]:
    """
    Get a random proxy configuration from the available list.
    
    Returns:
        Proxy configuration dict or empty dict if no proxies available
    """
    proxies = get_proxy_list()
    if proxies:
        return random.choice(proxies)
    return {}

if __name__ == "__main__":
    # Test the functions
    test_url = "https://www.example.com"
    response = safe_get(test_url)
    
    if response:
        print(f"Successfully fetched {test_url} with status code {response.status_code}")
    else:
        print(f"Failed to fetch {test_url}")