"""
Sentiment analyzer for ZimRate Predictor

This module provides functions to analyze the sentiment of social media posts
and news articles related to Zimbabwe's currency.
"""

import re
import logging
from typing import Dict, List, Any, Tuple, Optional
from django.utils import timezone
import datetime
import statistics

logger = logging.getLogger("sentiment_analyzer")

# Simple sentiment lexicon for financial/economic contexts
# Format: word -> (positive_score, negative_score)
SENTIMENT_LEXICON = {
    # Positive terms
    "gain": (0.8, 0.0),
    "strengthen": (0.7, 0.0),
    "strengthen": (0.7, 0.0),
    "recovery": (0.6, 0.0),
    "positive": (0.6, 0.0),
    "good": (0.5, 0.0),
    "rise": (0.6, 0.0),
    "rising": (0.6, 0.0),
    "grew": (0.5, 0.0),
    "grew": (0.5, 0.0),
    "growth": (0.5, 0.0),
    "profit": (0.7, 0.0),
    "profits": (0.7, 0.0),
    "confidence": (0.6, 0.0),
    "bullish": (0.8, 0.0),
    "strong": (0.5, 0.0),
    "stable": (0.6, 0.0),
    "stability": (0.6, 0.0),
    "improvement": (0.5, 0.0),
    "improved": (0.5, 0.0),
    
    # Negative terms
    "loss": (0.0, 0.7),
    "losses": (0.0, 0.7),
    "weaken": (0.0, 0.6),
    "weakened": (0.0, 0.6),
    "decline": (0.0, 0.5),
    "declining": (0.0, 0.5),
    "negative": (0.0, 0.6),
    "down": (0.0, 0.4),
    "fall": (0.0, 0.5),
    "fell": (0.0, 0.5),
    "decrease": (0.0, 0.5),
    "decreased": (0.0, 0.5),
    "drop": (0.0, 0.5),
    "dropped": (0.0, 0.5),
    "bearish": (0.0, 0.8),
    "weak": (0.0, 0.5),
    "unstable": (0.0, 0.6),
    "instability": (0.0, 0.6),
    "risk": (0.0, 0.5),
    "risky": (0.0, 0.5),
    "crisis": (0.0, 0.7),
    "trouble": (0.0, 0.6),
    "inflation": (0.0, 0.6),
    "hyperinflation": (0.0, 0.9),
    "shortage": (0.0, 0.6),
    "shortages": (0.0, 0.6),
    "corruption": (0.0, 0.7),
    "debt": (0.0, 0.5),
    "deficit": (0.0, 0.5),
    
    # Financial/currency specific
    "devalue": (0.0, 0.8),
    "devaluation": (0.0, 0.8),
    "depreciate": (0.0, 0.7),
    "depreciation": (0.0, 0.7),
    "appreciate": (0.7, 0.0),
    "appreciation": (0.7, 0.0),
    "rebound": (0.6, 0.0),
    "collapse": (0.0, 0.9),
    "plummet": (0.0, 0.8),
    "soar": (0.7, 0.0),
    "surge": (0.6, 0.0),
    "crash": (0.0, 0.9),
    "boom": (0.7, 0.0),
    "bust": (0.0, 0.7),
}

# Negation words that reverse sentiment
NEGATION_WORDS = [
    "not", "no", "never", "neither", "nor", "none", "hardly", 
    "barely", "scarcely", "doesn't", "isn't", "wasn't", "shouldn't",
    "wouldn't", "couldn't", "won't", "don't", "aren't", "haven't"
]

def analyze_sentiment(text: str) -> Tuple[str, float]:
    """
    Analyze sentiment of a text using lexicon-based approach.
    
    Args:
        text: Text to analyze
        
    Returns:
        Tuple of (sentiment category, sentiment score)
    """
    # Clean text
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    words = text.split()
    
    positive_score = 0.0
    negative_score = 0.0
    
    # Check for negation in a sliding window
    window_size = 5
    negation_active = False
    
    for i, word in enumerate(words):
        # Check for negation words
        if word in NEGATION_WORDS:
            negation_active = True
            continue
            
        # Reset negation after window size
        if negation_active and i > 0 and i % window_size == 0:
            negation_active = False
            
        # Check if word is in sentiment lexicon
        if word in SENTIMENT_LEXICON:
            pos, neg = SENTIMENT_LEXICON[word]
            
            # Flip sentiment if negation is active
            if negation_active:
                positive_score += neg
                negative_score += pos
            else:
                positive_score += pos
                negative_score += neg
                
    # Reset negation at the end of analysis
    negation_active = False
    
    # Calculate final sentiment score (-1.0 to 1.0)
    total = positive_score + negative_score
    if total > 0:
        sentiment_score = (positive_score - negative_score) / total
    else:
        sentiment_score = 0.0
    
    # Determine sentiment category
    if sentiment_score >= 0.2:
        sentiment = "positive"
    elif sentiment_score <= -0.2:
        sentiment = "negative"
    else:
        sentiment = "neutral"
        
    return sentiment, sentiment_score

def update_post_sentiment(post_id: int) -> bool:
    """
    Update sentiment analysis for a specific post in the database.
    
    Args:
        post_id: ID of the post to analyze
        
    Returns:
        Boolean indicating success
    """
    from rate_predictor.models import Post
    
    try:
        post = Post.objects.get(id=post_id)
        sentiment, score = analyze_sentiment(post.content)
        
        post.sentiment = sentiment
        post.sentiment_score = score
        post.save(update_fields=['sentiment', 'sentiment_score'])
        
        logger.info(f"Updated sentiment for post {post_id}: {sentiment} ({score:.2f})")
        return True
    except Exception as e:
        logger.error(f"Error updating sentiment for post {post_id}: {e}")
        return False

def analyze_recent_posts(days_back: int = 7) -> int:
    """
    Analyze sentiment for all recent posts.
    
    Args:
        days_back: Number of days back to analyze
        
    Returns:
        Number of posts analyzed
    """
    from rate_predictor.models import Post
    
    cutoff_date = timezone.now() - datetime.timedelta(days=days_back)
    
    # Get posts without sentiment analysis or with neutral sentiment
    posts = Post.objects.filter(
        published_at__gte=cutoff_date
    ).exclude(
        sentiment_score__lt=-0.1
    ).exclude(
        sentiment_score__gt=0.1
    )
    
    count = 0
    
    for post in posts:
        try:
            sentiment, score = analyze_sentiment(post.content)
            
            post.sentiment = sentiment
            post.sentiment_score = score
            post.save(update_fields=['sentiment', 'sentiment_score'])
            
            count += 1
            
        except Exception as e:
            logger.error(f"Error analyzing post {post.id}: {e}")
            continue
            
    logger.info(f"Analyzed sentiment for {count} posts")
    return count

def get_overall_sentiment(days_back: int = 7) -> Dict[str, Any]:
    """
    Get overall sentiment statistics for recent content.
    
    Args:
        days_back: Number of days back to analyze
        
    Returns:
        Dictionary with sentiment statistics
    """
    from rate_predictor.models import Post
    
    cutoff_date = timezone.now() - datetime.timedelta(days=days_back)
    posts = Post.objects.filter(published_at__gte=cutoff_date)
    
    if not posts.exists():
        return {
            "positive_percent": 33.3,
            "neutral_percent": 33.3, 
            "negative_percent": 33.3,
            "average_score": 0.0,
            "trend": "neutral",
            "trend_strength": 0.0
        }
    
    # Count sentiment categories
    positive_count = posts.filter(sentiment="positive").count()
    neutral_count = posts.filter(sentiment="neutral").count()
    negative_count = posts.filter(sentiment="negative").count()
    
    total_count = posts.count()
    
    if total_count > 0:
        positive_pct = (positive_count / total_count) * 100
        neutral_pct = (neutral_count / total_count) * 100
        negative_pct = (negative_count / total_count) * 100
    else:
        positive_pct = neutral_pct = negative_pct = 33.3
    
    # Calculate average sentiment score
    all_scores = [p.sentiment_score for p in posts if p.sentiment_score is not None]
    avg_score = statistics.mean(all_scores) if all_scores else 0.0
    
    # Determine trend
    if avg_score > 0.2:
        trend = "positive"
        trend_strength = min(abs(avg_score) * 2, 1.0)  # Scale to 0-1
    elif avg_score < -0.2:
        trend = "negative"
        trend_strength = min(abs(avg_score) * 2, 1.0)  # Scale to 0-1
    else:
        trend = "neutral"
        trend_strength = 0.0
    
    return {
        "positive_percent": positive_pct,
        "neutral_percent": neutral_pct,
        "negative_percent": negative_pct,
        "average_score": avg_score,
        "trend": trend,
        "trend_strength": trend_strength
    }

if __name__ == "__main__":
    # For testing the sentiment analyzer from the command line
    test_texts = [
        "The Zimbabwe dollar strengthened against the US dollar in today's trading.",
        "Currency shortages and hyperinflation continue to plague the economy.",
        "The Reserve Bank announced new measures to stabilize the exchange rate.",
        "The ZWL is not showing any significant movement against major currencies.",
        "Experts predict the currency will depreciate further due to policy failures."
    ]
    
    for text in test_texts:
        sentiment, score = analyze_sentiment(text)
        print(f"Text: {text}")
        print(f"Sentiment: {sentiment}, Score: {score:.2f}")
        print("---")