# Generated by Django 5.1.7 on 2025-03-11 06:25

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='NewsSource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('url', models.URLField()),
                ('reliability_score', models.FloatField(default=1.0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='SocialMediaSource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('platform', models.CharField(max_length=50)),
                ('account_id', models.CharField(max_length=100)),
                ('influence_score', models.FloatField(default=1.0)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='ExchangeRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('official_rate', models.DecimalField(decimal_places=2, max_digits=20)),
                ('parallel_rate', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-date'],
                'unique_together': {('date',)},
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_type', models.CharField(choices=[('social', 'Social Media'), ('news', 'News Article')], max_length=10)),
                ('content', models.TextField()),
                ('url', models.URLField(blank=True, null=True)),
                ('published_at', models.DateTimeField()),
                ('collected_at', models.DateTimeField(auto_now_add=True)),
                ('sentiment', models.CharField(choices=[('positive', 'Positive'), ('neutral', 'Neutral'), ('negative', 'Negative')], default='neutral', max_length=10)),
                ('sentiment_score', models.FloatField(default=0.0)),
                ('impact_score', models.FloatField(default=0.0)),
                ('news_source', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rate_predictor.newssource')),
                ('social_source', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rate_predictor.socialmediasource')),
            ],
        ),
        migrations.CreateModel(
            name='RatePrediction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prediction_date', models.DateField()),
                ('target_date', models.DateField()),
                ('predicted_official_rate', models.DecimalField(decimal_places=2, max_digits=20)),
                ('predicted_parallel_rate', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('confidence_score', models.FloatField(default=0.5)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('influencing_posts', models.ManyToManyField(blank=True, to='rate_predictor.post')),
            ],
            options={
                'ordering': ['-prediction_date', '-target_date'],
            },
        ),
        migrations.CreateModel(
            name='UserAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rate_threshold', models.DecimalField(decimal_places=2, max_digits=20)),
                ('is_above', models.BooleanField(default=True)),
                ('is_active', models.BooleanField(default=True)),
                ('last_triggered', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
