"""
Relevance detector for ZimRate Predictor

This module provides functions to detect whether content is relevant to
Zimbabwe's currency and exchange rates.
"""

import re
import logging
from typing import Optional, List, Dict, Union

logger = logging.getLogger("relevance_detector")

# Keywords with weighted relevance scores
KEYWORD_WEIGHTS = {
    # Currency terms - highest relevance
    "zimbabwe dollar": 1.0,
    "zwl": 1.0,
    "rtgs dollar": 1.0, 
    "bond note": 0.9,
    "zim dollar": 0.9,
    
    # Exchange rate terms
    "exchange rate": 0.7,
    "currency rate": 0.7,
    "parallel rate": 0.8,
    "parallel market": 0.8,
    "black market rate": 0.8,
    "official rate": 0.8,
    "rbz rate": 0.8,
    "forex rate": 0.7,
    "zw/usd": 0.9,
    "zwl/usd": 0.9,
    "z$/usd": 0.9,
    
    # Financial institutions
    "reserve bank of zimbabwe": 0.6,
    "rbz": 0.6,
    "zimbabwe central bank": 0.6,
    "zimswitch": 0.5,
    "bureau de change": 0.5,
    
    # Economic indicators
    "zimbabwe inflation": 0.6,
    "zim inflation": 0.6,
    "currency depreciation": 0.5,
    "monetary policy": 0.5,
    "forex shortage": 0.6,
    "currency shortage": 0.6,
    "currency control": 0.5,
    
    # Less specific but still relevant
    "zimbabwe economy": 0.4,
    "zim economy": 0.4,
    "economic crisis": 0.3,
    "foreign currency": 0.3,
    "usd": 0.2,
    "us dollar": 0.2
}

# Regex patterns for currency values and rates
CURRENCY_PATTERNS = [
    r'\b\d+(?:[\.,]\d+)?\s*(?:ZWL|zwl|Z\$|RTGS|rtgs)\b',  # e.g. 350 ZWL, 350.50 Z$
    r'\b(?:ZWL|zwl|Z\$|RTGS|rtgs)\s*\d+(?:[\.,]\d+)?\b',  # e.g. ZWL 350, Z$ 350.50
    r'\b\d+(?:[\.,]\d+)?\s*(?:USD|usd|\$)(?:\s*:\s*|\s*=\s*)\d+(?:[\.,]\d+)?\s*(?:ZWL|zwl|Z\$)\b',  # e.g. 1 USD = 350 ZWL
    r'\b\$1\s*(?:to|:|\=)\s*(?:ZWL|zwl|Z\$|RTGS|rtgs)?\s*\d+(?:[\.,]\d+)?\b'  # e.g. $1 to ZWL 350
]

def is_relevant(title: str, content: str, threshold: float = 0.4) -> bool:
    """
    Determine if content is relevant to Zimbabwe currency rates.
    
    Args:
        title: Title or headline of the content
        content: Main text content
        threshold: Minimum relevance score to consider relevant (0.0-1.0)
        
    Returns:
        Boolean indicating relevance
    """
    # Combine title and content, with title having more weight
    full_text = f"{title} {title} {content}".lower()
    
    # Initialize relevance score
    relevance_score = 0.0
    matches_found = 0
    
    # Check for currency patterns (high relevance indicators)
    for pattern in CURRENCY_PATTERNS:
        if re.search(pattern, full_text, re.IGNORECASE):
            relevance_score += 0.5
            matches_found += 1
            
    # Check for keyword matches
    for keyword, weight in KEYWORD_WEIGHTS.items():
        if keyword.lower() in full_text:
            relevance_score += weight
            matches_found += 1
    
    # Normalize score based on matches found
    if matches_found > 0:
        # Cap at 1.0
        relevance_score = min(1.0, relevance_score)
    
    logger.debug(f"Relevance score: {relevance_score:.2f} (threshold: {threshold})")
    return relevance_score >= threshold

def get_relevance_keywords() -> List[str]:
    """Get a list of relevance keywords for searching."""
    return list(KEYWORD_WEIGHTS.keys())

def calculate_relevance_score(text: str) -> float:
    """Calculate a relevance score for the given text."""
    return is_relevant("", text, threshold=0.0)  # We want the score, not the boolean

if __name__ == "__main__":
    # Test the relevance detector
    test_texts = [
        "Zimbabwe's official exchange rate hits 350 ZWL to 1 USD",
        "RBZ announces new monetary policy measures",
        "Currency shortage impacts Zimbabwe's economy",
        "Cricket match between Zimbabwe and South Africa",
        "Zimbabwe dollar continues to depreciate against the US dollar",
        "New regulations for bureau de change operators",
        "Weather forecast for Harare this week"
    ]
    
    for text in test_texts:
        is_rel = is_relevant("Test", text)
        score = calculate_relevance_score(text)
        print(f"Text: {text}")
        print(f"Relevant: {is_rel}, Score: {score:.2f}")
        print("---")