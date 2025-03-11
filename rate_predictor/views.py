from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
import datetime

from .models import ExchangeRate, RatePrediction, Post, SocialMediaSource, NewsSource


class HomeView(TemplateView):
    template_name = 'rate_predictor/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get latest exchange rates
        try:
            latest_rate = ExchangeRate.objects.latest('date')
            context['latest_rate'] = latest_rate
        except ExchangeRate.DoesNotExist:
            context['latest_rate'] = None
        
        # Get latest predictions
        latest_predictions = RatePrediction.objects.filter(
            target_date__gte=timezone.now().date()
        ).order_by('target_date')[:5]
        context['latest_predictions'] = latest_predictions
        
        # Recent influential posts
        recent_posts = Post.objects.filter(
            published_at__gte=timezone.now() - datetime.timedelta(days=7)
        ).order_by('-impact_score')[:10]
        context['recent_posts'] = recent_posts
        
        return context


class RateListView(ListView):
    model = ExchangeRate
    template_name = 'rate_predictor/rate_list.html'
    context_object_name = 'rates'
    ordering = ['-date']
    paginate_by = 20


class RateDetailView(DetailView):
    model = ExchangeRate
    template_name = 'rate_predictor/rate_detail.html'
    context_object_name = 'rate'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rate_date = self.object.date
        
        # Get predictions made for this date
        context['predictions'] = RatePrediction.objects.filter(target_date=rate_date)
        
        # Get posts from around this date that might have influenced the rate
        posts_before = Post.objects.filter(
            published_at__date__gte=rate_date - datetime.timedelta(days=3),
            published_at__date__lt=rate_date
        ).order_by('-impact_score')[:10]
        context['posts_before'] = posts_before
        
        return context


class PredictionListView(ListView):
    model = RatePrediction
    template_name = 'rate_predictor/prediction_list.html'
    context_object_name = 'predictions'
    ordering = ['-prediction_date', 'target_date']
    paginate_by = 20


class PredictionDetailView(DetailView):
    model = RatePrediction
    template_name = 'rate_predictor/prediction_detail.html'
    context_object_name = 'prediction'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get the influencing posts
        context['influencing_posts'] = self.object.influencing_posts.all().order_by('-impact_score')
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'rate_predictor/dashboard.html'
    login_url = '/login/'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get historical rates for chart
        historical_rates = ExchangeRate.objects.all().order_by('date')[:90]  # Last 90 days
        context['historical_rates'] = historical_rates
        
        # Get future predictions for chart
        future_predictions = RatePrediction.objects.filter(
            target_date__gte=timezone.now().date()
        ).order_by('target_date')[:30]  # Next 30 days
        context['future_predictions'] = future_predictions
        
        return context


# API Views
def latest_rate_api(request):
    """API endpoint to get the latest exchange rate"""
    try:
        latest = ExchangeRate.objects.latest('date')
        data = {
            'date': latest.date.isoformat(),
            'official_rate': float(latest.official_rate),
            'parallel_rate': float(latest.parallel_rate) if latest.parallel_rate else None,
            'last_updated': latest.updated_at.isoformat()
        }
        return JsonResponse({'status': 'success', 'data': data})
    except ExchangeRate.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'No exchange rates available'}, status=404)


def prediction_api(request):
    """API endpoint to get future predictions"""
    days = request.GET.get('days', 7)
    try:
        days = int(days)
    except ValueError:
        days = 7
        
    predictions = RatePrediction.objects.filter(
        target_date__gte=timezone.now().date()
    ).order_by('target_date')[:days]
    
    data = []
    for pred in predictions:
        data.append({
            'prediction_date': pred.prediction_date.isoformat(),
            'target_date': pred.target_date.isoformat(),
            'predicted_official_rate': float(pred.predicted_official_rate),
            'predicted_parallel_rate': float(pred.predicted_parallel_rate) if pred.predicted_parallel_rate else None,
            'confidence_score': pred.confidence_score
        })
    
    return JsonResponse({'status': 'success', 'data': data})
