from django.core.management.base import BaseCommand
from rate_predictor.tasks import update_model_task

class Command(BaseCommand):
    help = 'Update the prediction model with new data using Celery tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--initial',
            action='store_true',
            help='Perform initial training with 2 years of historical data',
        )

    def handle(self, *args, **options):
        is_initial = options['initial']
        
        try:
            self.stdout.write(self.style.NOTICE(
                'Queueing model update task...'
                f'{"(initial training)" if is_initial else "(incremental update)"}'
            ))
            
            # Queue the task using Celery
            task = update_model_task.delay(is_initial=is_initial)
            
            self.stdout.write(self.style.SUCCESS(
                f'Task queued successfully (task_id: {task.id})'
            ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error queueing task: {str(e)}'))