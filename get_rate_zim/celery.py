import os
import logging
from celery import Celery
from celery.utils.log import get_task_logger
from celery.signals import setup_logging

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = get_task_logger(__name__)

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'get_rate_zim.settings')

# Create the Celery app
app = Celery('get_rate_zim')

# Configure Celery using settings from Django settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all registered Django apps
app.autodiscover_tasks()

# Configure Celery logging
@setup_logging.connect
def configure_logging(sender=None, **kwargs):
    pass  # Let Django handle the logging configuration

@app.task(bind=True)
def debug_task(self):
    """Task to help debug celery configuration"""
    logger.info(f'Request: {self.request!r}')
    return "Debug task completed successfully"

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Set up periodic tasks if needed"""
    logger.info("Setting up periodic tasks for Celery")
    # Add periodic tasks here if needed