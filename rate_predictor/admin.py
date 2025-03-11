from django.contrib import admin
from .models import (
    SocialMediaSource,
    NewsSource,
    Post,
    ExchangeRate,
    RatePrediction,
    UserAlert
)

@admin.register(SocialMediaSource)
class SocialMediaSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'platform', 'influence_score', 'is_active')
    list_filter = ('platform', 'is_active')
    search_fields = ('name', 'account_id')


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'reliability_score', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'url')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('source_type', 'published_at', 'sentiment', 'impact_score')
    list_filter = ('source_type', 'sentiment', 'published_at')
    search_fields = ('content',)
    date_hierarchy = 'published_at'


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('date', 'official_rate', 'parallel_rate')
    list_filter = ('date',)
    date_hierarchy = 'date'


@admin.register(RatePrediction)
class RatePredictionAdmin(admin.ModelAdmin):
    list_display = ('prediction_date', 'target_date', 'predicted_official_rate', 'confidence_score')
    list_filter = ('prediction_date', 'target_date')
    date_hierarchy = 'target_date'
    filter_horizontal = ('influencing_posts',)


@admin.register(UserAlert)
class UserAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'rate_threshold', 'is_above', 'is_active', 'last_triggered')
    list_filter = ('is_above', 'is_active')
    search_fields = ('user__username',)
