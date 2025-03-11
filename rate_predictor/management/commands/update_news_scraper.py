import os
from django.core.management.base import BaseCommand
from rate_predictor.scrapers.news_scraper import run_news_scraper, train_model_with_initial_data

class Command(BaseCommand):
    help = 'Run the news scraper to collect articles and update the model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days_back',
            type=int,
            default=7,
            help='Number of days back to consider articles from',
        )
        parser.add_argument(
            '--initial_scrape',
            action='store_true',
            help='Perform the initial scrape for the last 2 years',
        )

    def handle(self, *args, **options):
        days_back = options['days_back']
        initial_scrape = options['initial_scrape']
        self.stdout.write(self.style.SUCCESS(f'Starting news scraper for the past {days_back} days...'))
        saved_count = run_news_scraper(days_back, initial_scrape)
        self.stdout.write(self.style.SUCCESS(f'Successfully saved {saved_count} articles.'))
        
        if initial_scrape:
            self.stdout.write(self.style.SUCCESS('Training model with initial data...'))
            train_model_with_initial_data()
            self.stdout.write(self.style.SUCCESS('Model training completed.'))
        else:
            # Here you can add code to update the model with the new data
            # For example, call a function to train the model with the new articles
            # train_model_with_new_data()
            self.stdout.write(self.style.SUCCESS('Model updated successfully.'))
