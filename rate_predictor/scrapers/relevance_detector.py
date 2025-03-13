"""
Relevance detection module for ZimRate Predictor

This module contains functions to determine the relevance of articles and posts
to Zimbabwe's currency and economy using advanced NLP techniques.
"""

import logging
import re
from typing import Dict, List, Set, Optional

# Configure logging
logger = logging.getLogger("relevance_detector")

# Try to import spaCy if available
try:
    import spacy
    try:
        nlp = spacy.load("en_core_web_sm")
        SPACY_AVAILABLE = True
        logger.info("Using spaCy for enhanced relevance detection")
    except IOError:
        logger.warning("spaCy model not found. To install: python -m spacy download en_core_web_sm")
        SPACY_AVAILABLE = False
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not available. Using fallback keyword matching")

# Currency-related entity types for spaCy
CURRENCY_ENTITIES = {"MONEY", "PERCENT", "QUANTITY"}

# Enhanced keywords with categories and weights
KEYWORDS = {
    "high_relevance": {
        "zimbabwe dollar": 1.0, 
        "zwl": 1.0, 
        "zim dollar": 1.0,
        "zimbabwean currency": 1.0,
        "rbz": 0.9,
        "reserve bank of zimbabwe": 0.9
    },
    "medium_relevance": {
        "exchange rate": 0.7,
        "forex": 0.7,
        "foreign currency": 0.7,
        "parallel market": 0.8,
        "black market": 0.8,
        "currency trading": 0.6
    },
    "context": {
        "inflation": 0.4,
        "economy": 0.3,
        "monetary policy": 0.5,
        "interest rate": 0.4,
        "zimbabwe": 0.3,
        "harare": 0.2
    }
}

def simple_keyword_relevance(text: str) -> float:
    """
    Calculate relevance score based on simple keyword matching.
    
    Args:
        text: Text to analyze
        
    Returns:
        Relevance score between 0.0 and 1.0
    """
    if not text:
        return 0.0
        
    text_lower = text.lower()
    score = 0.0
    
    # Check for keywords in each category
    for category, words in KEYWORDS.items():
        for word, weight in words.items():
            if word in text_lower:
                score += weight
    
    # Cap the score at 1.0
    return min(1.0, score)

def calculate_relevance_score(text: str) -> float:
    """
    Calculate relevance score using NLP techniques if available.
    
    Args:
        text: Text to analyze
        
    Returns:
        Relevance score between 0.0 and 1.0
    """
    if not text:
        return 0.0
    
    if not SPACY_AVAILABLE:
        # Fallback to keyword matching if NLP not available
        return simple_keyword_relevance(text)
    
    try:
        # Normalize text
        text_lower = text.lower()
        
        # Process with SpaCy
        doc = nlp(text[:10000])  # Limit text length to avoid memory issues
        
        # Check for currency entities
        entity_score = 0.0
        has_currency = False
        for entity in doc.ents:
            if entity.label_ in CURRENCY_ENTITIES:
                entity_score += 0.3
                has_currency = True
            if "ZIM" in entity.text or "Zimbabwe" in entity.text:
                entity_score += 0.2
        
        # Cap entity score
        entity_score = min(0.5, entity_score)
        
        # Keyword scoring with context
        keyword_score = simple_keyword_relevance(text_lower)
        
        # Cap keyword score
        keyword_score = min(0.7, keyword_score)
        
        # Combine scores
        score = entity_score + keyword_score
        
        # Ensure we don't exceed 1.0
        return min(1.0, score)
    except Exception as e:
        logger.error(f"Error in NLP relevance detection: {e}")
        # Fall back to simple keyword matching
        return simple_keyword_relevance(text)

def is_relevant(title: str, content: str, threshold: float = 0.4) -> bool:
    """
    Determine if content is relevant based on title and body.
    
    Args:
        title: Content title
        content: Content body
        threshold: Minimum score to consider relevant
        
    Returns:
        Boolean indicating if content is relevant
    """
    # Title is more important, so weight it higher
    title_score = calculate_relevance_score(title) * 1.5
    content_score = calculate_relevance_score(content)
    
    # Combined score
    combined_score = (title_score + content_score) / 2.5
    
    return combined_score >= threshold

if __name__ == "__main__":
    # Test the relevance detection
    test_texts = [
        "Zimbabwe's currency stabilized today after the central bank's intervention.",
        "The exchange rate fell to 350 ZWL per USD on the parallel market.",
        "Football match results for the weekend games in Harare.",
        "RBZ announces new monetary policy to combat inflation in Zimbabwe."
    ]
    
    for text in test_texts:
        score = calculate_relevance_score(text)
        print(f"Text: {text}")
        print(f"Relevance score: {score}")
        print(f"Is relevant: {score >= 0.4}")
        print("-" * 50)