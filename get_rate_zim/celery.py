import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'get_rate_zim.settings')

# Create the Celery app
app = Celery('get_rate_zim')

# Configure Celery using settings from Django settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all registered Django apps
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    'update-model-every-6-hours': {
        'task': 'rate_predictor.tasks.update_model_periodic',
        'schedule': crontab(hour='*/6'),  # Run every 6 hours
    },
}