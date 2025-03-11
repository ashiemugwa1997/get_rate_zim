import os
from celery import Celery
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'get_rate_zim.settings')

# Create the Celery app
app = Celery('get_rate_zim')

# Configure Celery using settings from Django settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all registered Django apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    """Task to help debug celery configuration"""
    logger.info(f'Request: {self.request!r}')