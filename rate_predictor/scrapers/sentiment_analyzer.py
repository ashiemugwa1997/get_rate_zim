"""
Sentiment analysis module for ZimRate Predictor

This module processes content from social media and news sources to determine sentiment
and potential impact on Zimbabwe's currency exchange rates.
"""

import logging
import re
import nltk
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from datetime import timedelta
from django.utils import timezone

# Set up NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon')

from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sentiment_analyzer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("sentiment_analyzer")

# Initialize NLTK components
stop_words = set(stopwords.words('english'))
sentiment_analyzer = SentimentIntensityAnalyzer()

# Keywords specifically relevant to Zimbabwe's currency with their impact weights
ZIM_CURRENCY_KEYWORDS = {
    "devaluation": -0.8,
    "depreciation": -0.7,
    "inflation": -0.6,
    "hyperinflation": -0.9,
    "rbz auction": 0.4,
    "reserve bank": 0.3,
    "monetary policy": 0.4,
    "foreign currency": 0.3,
    "forex shortage": -0.7,
    "forex reserves": 0.5,
    "black market": -0.6,
    "parallel market": -0.5,
    "exchange control": -0.4,
    "currency stability": 0.7,
    "currency reform": 0.5,
    "dollarization": 0.5,
    "zimbabwe dollar": 0.0,  # neutral but important
    "bond note": -0.3,
    "foreign exchange": 0.0,  # neutral but important
    "imf": 0.4,
    "world bank": 0.4,
    "export earnings": 0.6,
    "trade deficit": -0.6,
    "budget deficit": -0.5,
    "economic growth": 0.7,
    "economic crisis": -0.8,
    "treasury bill": -0.3,
    "money supply": -0.4,
    "liquidity": 0.3,
    "interest rate": 0.0,  # depends on context
    "investor confidence": 0.7,
    "foreign investment": 0.8,
    "debt": -0.5,
    "loan": 0.0,  # depends on context
    "sanctions": -0.6,
    "corruption": -0.7,
    "economic policy": 0.0,  # depends on context
    "zim dollar": 0.0,  # neutral but important
    "rtgs": -0.1
}


def preprocess_text(text: str) -> str:
    """
    Preprocess the text by removing URLs, special characters, etc.
    
    Args:
        text: Raw text content
        
    Returns:
        Preprocessed text
    """
    # Convert to lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    
    # Remove special characters and numbers (keep letters and spaces)
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def get_vader_sentiment(text: str) -> Dict[str, float]:
    """
    Get sentiment scores using NLTK's VADER
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with sentiment scores
    """
    return sentiment_analyzer.polarity_scores(text)


def get_domain_specific_sentiment(text: str) -> Tuple[float, float]:
    """
    Calculate domain-specific sentiment for Zimbabwe currency
    
    Args:
        text: Text to analyze
        
    Returns:
        Tuple of (sentiment_score, impact_score) where:
            sentiment_score ranges from -1 (very negative) to 1 (very positive)
            impact_score ranges from 0 (no impact) to 1 (high impact)
    """
    text = text.lower()
    tokens = word_tokenize(text)
    filtered_tokens = [w for w in tokens if w not in stop_words]
    
    # Check for currency-specific keywords
    matched_keywords = []
    sentiment_values = []
    
    for keyword, value in ZIM_CURRENCY_KEYWORDS.items():
        if ' ' in keyword:  # Multi-word keyword
            if keyword in text:
                matched_keywords.append(keyword)
                sentiment_values.append(value)
        else:  # Single word keyword
            if keyword in filtered_tokens:
                matched_keywords.append(keyword)
                sentiment_values.append(value)
    
    # Calculate domain-specific sentiment
    if matched_keywords:
        domain_sentiment = sum(sentiment_values) / len(sentiment_values)
        # Impact is based on number of matched keywords and their absolute values
        impact = min(1.0, (len(matched_keywords) / 10) + (sum(abs(v) for v in sentiment_values) / len(sentiment_values)))
    else:
        # No domain-specific keywords, use default values
        domain_sentiment = 0
        impact = 0.1  # Low impact
    
    return domain_sentiment, impact


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyze sentiment of text, combining VADER and domain-specific analysis
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with sentiment analysis results
    """
    # Preprocess the text
    clean_text = preprocess_text(text)
    
    # Get VADER sentiment
    vader_scores = get_vader_sentiment(clean_text)
    
    # Get domain-specific sentiment
    domain_sentiment, impact_score = get_domain_specific_sentiment(clean_text)
    
    # Combine the sentiment scores (weighted approach)
    # VADER compound score ranges from -1 (negative) to 1 (positive)
    combined_sentiment = 0.7 * vader_scores['compound'] + 0.3 * domain_sentiment
    
    # Determine sentiment label
    if combined_sentiment >= 0.05:
        sentiment_label = 'positive'
    elif combined_sentiment <= -0.05:
        sentiment_label = 'negative'
    else:
        sentiment_label = 'neutral'
    
    # Adjust impact score based on VADER intensity
    intensity = abs(vader_scores['compound'])
    adjusted_impact = 0.7 * impact_score + 0.3 * intensity
    
    # Cap the impact score at 1.0
    final_impact = min(1.0, adjusted_impact)
    
    return {
        'sentiment': sentiment_label,
        'sentiment_score': combined_sentiment,
        'impact_score': final_impact,
        'vader_compound': vader_scores['compound'],
        'domain_sentiment': domain_sentiment
    }


def adjust_impact_by_source(analysis: Dict[str, Any], source_influence: float = 1.0) -> Dict[str, Any]:
    """
    Adjust the impact score based on the influence of the source
    
    Args:
        analysis: Original sentiment analysis
        source_influence: Source influence score (1.0 is default/neutral)
        
    Returns:
        Updated sentiment analysis
    """
    # Adjust impact score based on source influence, capping at 1.0
    analysis['impact_score'] = min(1.0, analysis['impact_score'] * source_influence)
    return analysis


def process_post(post: Any) -> Dict[str, Any]:
    """
    Process a post/article and update its sentiment and impact score
    
    Args:
        post: Post model instance
        
    Returns:
        Dictionary with updated sentiment and impact values
    """
    try:
        # Get the post content
        content = post.content
        
        # Get source influence
        source_influence = 1.0  # Default
        if post.source_type == 'social' and post.social_source:
            source_influence = post.social_source.influence_score
        elif post.source_type == 'news' and post.news_source:
            source_influence = post.news_source.reliability_score
        
        # Analyze sentiment
        analysis = analyze_sentiment(content)
        
        # Adjust based on source
        adjusted_analysis = adjust_impact_by_source(analysis, source_influence)
        
        # Return the update values
        return {
            'sentiment': adjusted_analysis['sentiment'],
            'impact_score': adjusted_analysis['impact_score']
        }
        
    except Exception as e:
        logger.error(f"Error processing post (ID: {post.id if hasattr(post, 'id') else 'unknown'}): {e}")
        return {
            'sentiment': 'neutral',
            'impact_score': 0.1
        }


def analyze_posts_batch(days_back: int = 7) -> int:
    """
    Analyze a batch of recent posts from the database
    
    Args:
        days_back: Number of days back to analyze
        
    Returns:
        Number of posts processed
    """
    from rate_predictor.models import Post
    
    # Get posts from the specified period that haven't been analyzed yet
    # (neutral sentiment and very low impact score indicates no analysis)
    cutoff_date = timezone.now() - timedelta(days=days_back)
    
    posts = Post.objects.filter(
        published_at__gte=cutoff_date,
        impact_score__lt=0.2  # Assume these haven't been properly analyzed
    )
    
    processed_count = 0
    
    for post in posts:
        try:
            # Analyze the post
            results = process_post(post)
            
            # Update the post with the analysis results
            post.sentiment = results['sentiment']
            post.impact_score = results['impact_score']
            post.save(update_fields=['sentiment', 'impact_score'])
            
            processed_count += 1
            
            if processed_count % 100 == 0:
                logger.info(f"Processed {processed_count} posts so far...")
                
        except Exception as e:
            logger.error(f"Error processing post {post.id}: {e}")
    
    logger.info(f"Completed sentiment analysis. Processed {processed_count} posts.")
    return processed_count


def get_overall_sentiment(days_back: int = 7) -> Dict[str, Any]:
    """
    Calculate the overall sentiment from recent posts
    
    Args:
        days_back: Number of days back to analyze
        
    Returns:
        Dictionary with overall sentiment metrics
    """
    from rate_predictor.models import Post
    
    cutoff_date = timezone.now() - timedelta(days=days_back)
    
    # Get processed posts from the period
    posts = Post.objects.filter(
        published_at__gte=cutoff_date,
        impact_score__gt=0.1  # Only include analyzed posts
    )
    
    if not posts:
        return {
            'overall_sentiment': 'neutral',
            'sentiment_score': 0,
            'average_impact': 0,
            'positive_ratio': 0,
            'negative_ratio': 0,
            'neutral_ratio': 0,
            'post_count': 0,
            'high_impact_count': 0
        }
    
    # Count sentiments
    sentiment_counts = {
        'positive': 0,
        'negative': 0,
        'neutral': 0
    }
    
    # Track weighted impact
    total_impact = 0
    high_impact_count = 0
    
    for post in posts:
        sentiment_counts[post.sentiment] += 1
        total_impact += post.impact_score
        if post.impact_score > 0.6:  # High impact threshold
            high_impact_count += 1
    
    # Calculate metrics
    post_count = len(posts)
    average_impact = total_impact / post_count if post_count > 0 else 0
    
    # Calculate sentiment ratios
    positive_ratio = sentiment_counts['positive'] / post_count if post_count > 0 else 0
    negative_ratio = sentiment_counts['negative'] / post_count if post_count > 0 else 0
    neutral_ratio = sentiment_counts['neutral'] / post_count if post_count > 0 else 0
    
    # Calculate overall sentiment score (-1 to 1)
    sentiment_score = positive_ratio - negative_ratio
    
    # Determine overall sentiment label
    if sentiment_score > 0.1:
        overall_sentiment = 'positive'
    elif sentiment_score < -0.1:
        overall_sentiment = 'negative'
    else:
        overall_sentiment = 'neutral'
    
    return {
        'overall_sentiment': overall_sentiment,
        'sentiment_score': sentiment_score,
        'average_impact': average_impact,
        'positive_ratio': positive_ratio,
        'negative_ratio': negative_ratio,
        'neutral_ratio': neutral_ratio,
        'post_count': post_count,
        'high_impact_count': high_impact_count
    }


if __name__ == "__main__":
    # When run as script, process recent posts
    analyze_posts_batch()