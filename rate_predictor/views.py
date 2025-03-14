from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
import datetime
import logging

logger = logging.getLogger(__name__)

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
        try:
            historical_rates = ExchangeRate.objects.all().order_by('date')[:90]  # Last 90 days
            context['historical_rates'] = historical_rates
            logger.info(f"Fetched {len(historical_rates)} historical rates")
        except Exception as e:
            logger.error(f"Error fetching historical rates: {e}")
        
        # Get future predictions for chart
        try:
            future_predictions = RatePrediction.objects.filter(
                target_date__gte=timezone.now().date()
            ).order_by('target_date')[:30]  # Next 30 days
            context['future_predictions'] = future_predictions
            logger.info(f"Fetched {len(future_predictions)} future predictions")
        except Exception as e:
            logger.error(f"Error fetching future predictions: {e}")
        
        # Get sentiment metrics from recent content
        try:
            sentiment_metrics = self.get_sentiment_metrics()
            context.update(sentiment_metrics)
            logger.info("Fetched sentiment metrics")
        except Exception as e:
            logger.error(f"Error fetching sentiment metrics: {e}")
        
        # Calculate trend
        try:
            if len(historical_rates) >= 2:
                oldest_rate = historical_rates.first().official_rate
                newest_rate = historical_rates.last().official_rate
                trend_pct = ((newest_rate - oldest_rate) / oldest_rate) * 100
                context['trend_percentage'] = abs(trend_pct)
                context['trend_direction'] = 'up' if trend_pct > 0 else 'down' if trend_pct < 0 else 'stable'
                logger.info(f"Calculated trend: {context['trend_direction']} ({context['trend_percentage']}%)")
        except Exception as e:
            logger.error(f"Error calculating trend: {e}")
        
        # Calculate premium if parallel rate exists
        try:
            if historical_rates and historical_rates[0].parallel_rate:
                premium = ((historical_rates[0].parallel_rate - historical_rates[0].official_rate) 
                          / historical_rates[0].official_rate * 100)
                context['premium_percentage'] = premium
                logger.info(f"Calculated premium: {context['premium_percentage']}%")
        except Exception as e:
            logger.error(f"Error calculating premium: {e}")
        
        return context
    
    def get_sentiment_metrics(self):
        """Get sentiment analysis metrics for the dashboard"""
        # Safely import sentiment analyzer handling potential import errors
        try:
            from rate_predictor.scrapers.sentiment_analyzer import get_overall_sentiment
            sentiment_metrics = get_overall_sentiment(days_back=7)
            logger.info("Sentiment metrics fetched successfully")
        except ImportError as e:
            logger.warning(f"Could not import sentiment analyzer: {e}")
            sentiment_metrics = {
                'positive': 30,
                'neutral': 50,
                'negative': 20
            }
        except Exception as e:
            logger.error(f"Error getting sentiment metrics: {e}")
            sentiment_metrics = {
                'positive': 30,
                'neutral': 50,
                'negative': 20
            }
        
        # Count posts by source type
        try:
            social_count = Post.objects.filter(
                source_type='social',
                published_at__gte=timezone.now() - datetime.timedelta(days=7)
            ).count()
            news_count = Post.objects.filter(
                source_type='news',
                published_at__gte=timezone.now() - datetime.timedelta(days=7)
            ).count()
            announcements_count = Post.objects.filter(
                published_at__gte=timezone.now() - datetime.timedelta(days=7),
                impact_score__gte=0.7
            ).count()
            logger.info(f"Post counts - Social: {social_count}, News: {news_count}, Announcements: {announcements_count}")
        except Exception as e:
            logger.error(f"Error counting posts: {e}")
            social_count = news_count = announcements_count = 0
        
        return {
            'sentiment_metrics': sentiment_metrics,
            'social_media_count': social_count,
            'news_count': news_count,
            'announcements_count': announcements_count
        }
    
    def get(self, request, *args, **kwargs):
        """Handle GET requests and trigger updates"""
        from rate_predictor.tasks import update_model_task
        from rate_predictor.models import RatePrediction, TaskProgress
        from kombu.exceptions import OperationalError
        
        try:
            # Check if initial training is needed
            initial_training_needed = not RatePrediction.objects.exists()
            logger.info(f"Initial training needed: {initial_training_needed}")
            
            # Create task progress record
            task_id = 'task_' + timezone.now().strftime('%Y%m%d_%H%M%S')
            task_type = 'training' if initial_training_needed else 'scraping'
            
            task_progress, created = TaskProgress.objects.get_or_create(
                task_id=task_id,
                defaults={
                    'task_type': task_type,
                    'status': 'pending',
                    'message': 'Task starting...'
                }
            )
            logger.info(f"Task progress record created: {task_id}")
            
            try:
                # Execute task - handle Celery connection errors gracefully
                task = update_model_task.delay(is_initial=initial_training_needed)
                
                # Update task ID with actual Celery task ID if available
                if hasattr(task, 'id') and task.id:
                    task_progress.task_id = task.id
                    task_progress.save()
                    logger.info(f"Task ID updated: {task.id}")
                
            except OperationalError as e:
                # Update the task progress with the error
                task_progress.status = 'failed'
                task_progress.message = f"Connection error: {str(e)}. Is the message broker running?"
                task_progress.save()
                logger.error(f"Error in dashboard task execution: {e}")
                
                # Continue with the page load despite the error
            except Exception as e:
                # Update the task progress with the error
                task_progress.status = 'failed'
                task_progress.message = f"Error: {str(e)}"
                task_progress.save()
                logger.error(f"Error in dashboard task execution: {e}")
            
        except Exception as e:
            logger.error(f"Error in dashboard task execution: {e}")
        
        # Continue with regular page load
        return super().get(request, *args, **kwargs)


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


def task_progress_api(request):
    """API endpoint to get task progress"""
    from .models import TaskProgress
    
    # Get the latest task
    latest_task = TaskProgress.objects.first()
    
    if latest_task:
        data = {
            'task_id': latest_task.task_id,
            'task_type': latest_task.task_type,
            'status': latest_task.status,
            'progress': latest_task.progress,
            'message': latest_task.message,
            'updated_at': latest_task.updated_at.isoformat()
        }
        return JsonResponse({'status': 'success', 'data': data})
    return JsonResponse({'status': 'error', 'message': 'No tasks found'}, status=404)
