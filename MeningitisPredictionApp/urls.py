from django.urls import path
from . import views

urlpatterns = [
    path('MeningitisPredictionApp/', views.mapView, name='RiskMap'),
    path('MeningitisPredictionApp/Article/<int:article_id>/', views.articleView, name='article'),
    path('MeningitisPredictionApp/Methodology/<int:metho_id>/', views.methodologyView, name='methodology'),
    path('MeningitisPredictionApp/Weather', views.weatherView, name='weather'),
]