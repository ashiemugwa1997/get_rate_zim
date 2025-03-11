from celery import shared_task
from django.core.management import call_command
from rate_predictor.models import RatePrediction, TaskProgress
from rate_predictor.scrapers.news_scraper import run_news_scraper
from rate_predictor.scrapers.social_scraper import run_scraper
import logging

logger = logging.getLogger(__name__)

def update_progress(task_id, task_type, progress, message, status='running'):
    """Update task progress in database"""
    TaskProgress.objects.update_or_create(
        task_id=task_id,
        defaults={
            'task_type': task_type,
            'progress': progress,
            'message': message,
            'status': status
        }
    )

@shared_task(bind=True)
def update_model_periodic(self):
    """Periodic task to update the model with new data"""
    try:
        # Initialize progress
        update_progress(self.request.id, 'scraping', 0, "Starting periodic update...")
        
        # Run news scraper (50% of progress)
        update_progress(self.request.id, 'scraping', 10, "Scraping news articles...")
        run_news_scraper(days_back=7)
        update_progress(self.request.id, 'scraping', 50, "News articles scraped")
        
        # Run social scraper (next 50% of progress)
        update_progress(self.request.id, 'scraping', 60, "Scraping social media...")
        run_scraper(days_back=7)
        
        # Mark as completed
        update_progress(self.request.id, 'scraping', 100, "Update completed", 'completed')
        logger.info("Completed periodic model update")
        
    except Exception as e:
        update_progress(self.request.id, 'scraping', 0, f"Error: {str(e)}", 'failed')
        logger.error(f"Error in periodic model update: {e}")
        raise

@shared_task(bind=True)
def initial_model_training(self):
    """Task for initial model training with historical data"""
    try:
        # Initialize progress tracking
        update_progress(self.request.id, 'training', 0, "Starting initial training...")
        
        # News data collection (40% of progress)
        update_progress(self.request.id, 'training', 5, "Collecting historical news data...")
        run_news_scraper(initial_scrape=True)
        update_progress(self.request.id, 'training', 40, "News data collected")
        
        # Social media data collection (40% of progress)
        update_progress(self.request.id, 'training', 45, "Collecting social media data...")
        run_scraper(initial_scrape=True)
        update_progress(self.request.id, 'training', 80, "Social media data collected")
        
        # Final processing
        update_progress(self.request.id, 'training', 90, "Processing collected data...")
        
        # Mark as completed
        update_progress(self.request.id, 'training', 100, "Initial training completed", 'completed')
        logger.info("Completed initial model training")
        
    except Exception as e:
        update_progress(self.request.id, 'training', 0, f"Error: {str(e)}", 'failed')
        logger.error(f"Error in initial model training: {e}")
        raise

@shared_task(bind=True)
def update_model_task(self, is_initial=False):
    """Task to update the model (can be used for both initial and incremental updates)"""
    try:
        if is_initial and not RatePrediction.objects.exists():
            return initial_model_training.delay()
        else:
            return update_model_periodic.delay()
    except Exception as e:
        logger.error(f"Error in update_model_task: {e}")
        raise