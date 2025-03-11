from django.urls import path
from . import views

app_name = 'rate_predictor'

urlpatterns = [
    # Main site URLs
    path('', views.HomeView.as_view(), name='home'),
    path('rates/', views.RateListView.as_view(), name='rate_list'),
    path('rates/<int:pk>/', views.RateDetailView.as_view(), name='rate_detail'),
    path('predictions/', views.PredictionListView.as_view(), name='prediction_list'),
    path('predictions/<int:pk>/', views.PredictionDetailView.as_view(), name='prediction_detail'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # API endpoints
    path('api/latest-rate/', views.latest_rate_api, name='api_latest_rate'),
    path('api/predictions/', views.prediction_api, name='api_predictions'),
]