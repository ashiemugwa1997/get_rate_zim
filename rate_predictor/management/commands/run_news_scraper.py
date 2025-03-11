import os
from django.core.management.base import BaseCommand
from rate_predictor.scrapers.news_scraper import run_news_scraper

class Command(BaseCommand):
    help = 'Run the news scraper to collect articles'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days_back',
            type=int,
            default=7,
            help='Number of days back to consider articles from',
        )

    def handle(self, *args, **options):
        days_back = options['days_back']
        self.stdout.write(self.style.SUCCESS(f'Starting news scraper for the past {days_back} days...'))
        saved_count = run_news_scraper(days_back)
        self.stdout.write(self.style.SUCCESS(f'Successfully saved {saved_count} articles.'))
