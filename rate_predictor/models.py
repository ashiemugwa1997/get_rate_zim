from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SocialMediaSource(models.Model):
    """Model for tracking social media profiles to monitor"""
    name = models.CharField(max_length=100)
    platform = models.CharField(max_length=50)  # Twitter, Facebook, etc.
    account_id = models.CharField(max_length=100)
    influence_score = models.FloatField(default=1.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.platform})"


class NewsSource(models.Model):
    """Model for news sources to monitor"""
    name = models.CharField(max_length=100)
    url = models.URLField()
    reliability_score = models.FloatField(default=1.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Post(models.Model):
    """Model for social media posts and news articles"""
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]
    SOURCE_TYPE_CHOICES = [
        ('social', 'Social Media'),
        ('news', 'News Article'),
    ]
    
    source_type = models.CharField(max_length=10, choices=SOURCE_TYPE_CHOICES)
    social_source = models.ForeignKey(SocialMediaSource, on_delete=models.CASCADE, null=True, blank=True)
    news_source = models.ForeignKey(NewsSource, on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    url = models.URLField(null=True, blank=True)
    published_at = models.DateTimeField()
    collected_at = models.DateTimeField(auto_now_add=True)
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, default='neutral')
    sentiment_score = models.FloatField(default=0.0)  # -1.0 to 1.0
    impact_score = models.FloatField(default=0.0)
    
    def __str__(self):
        return f"{self.source_type} post from {self.published_at.strftime('%Y-%m-%d')}"


class ExchangeRate(models.Model):
    """Model for ZWL to USD exchange rates"""
    date = models.DateField()
    official_rate = models.DecimalField(max_digits=20, decimal_places=2)
    parallel_rate = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Rate on {self.date}: Official {self.official_rate} ZWL/USD"


class RatePrediction(models.Model):
    """Model for exchange rate predictions"""
    prediction_date = models.DateField()
    target_date = models.DateField()
    predicted_official_rate = models.DecimalField(max_digits=20, decimal_places=2)
    predicted_parallel_rate = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    confidence_score = models.FloatField(default=0.5)  # 0.0 to 1.0
    influencing_posts = models.ManyToManyField(Post, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-prediction_date', '-target_date']
    
    def __str__(self):
        return f"Prediction on {self.prediction_date} for {self.target_date}"


class UserAlert(models.Model):
    """Model for user alerts based on exchange rate thresholds"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rate_threshold = models.DecimalField(max_digits=20, decimal_places=2)
    is_above = models.BooleanField(default=True)  # True if alert when above threshold
    is_active = models.BooleanField(default=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        direction = "above" if self.is_above else "below"
        return f"Alert for {self.user.username} when rate is {direction} {self.rate_threshold}"


class TaskProgress(models.Model):
    """Model to track progress of background tasks like scraping and training"""
    TASK_TYPES = (
        ('scraping', 'Data Scraping'),
        ('training', 'Model Training'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    task_id = models.CharField(max_length=255, unique=True)
    task_type = models.CharField(max_length=50, choices=TASK_TYPES)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField(default=0)  # Progress percentage
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.task_type} - {self.status} ({self.progress}%)"
