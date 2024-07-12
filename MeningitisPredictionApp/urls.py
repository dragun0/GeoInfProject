from django.urls import path
from . import views

urlpatterns = [
    path('', views.mapView, name='RiskMap'),
    path('Article/<int:article_id>/', views.articleView, name='article'),
    path('Methodology/<int:metho_id>/', views.methodologyView, name='methodology'),
    path('Weather', views.weatherView, name='weather'),
]