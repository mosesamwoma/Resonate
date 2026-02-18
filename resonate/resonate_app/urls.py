# resonate_app/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.spotify_login, name='spotify_login'),
    path('callback/', views.spotify_callback, name='spotify_callback'),
    path('logout/', views.logout_view, name='logout'),
    path('monthly/<int:year>/<int:month>/', views.monthly_wrapped, name='monthly_wrapped'),
    path('weekly/<int:year>/<int:month>/<int:week>/', views.weekly_wrapped, name='weekly_wrapped'),
    path('fetch/', views.fetch_tracks_view, name='fetch_tracks'),
    path('fetch/date-range/', views.custom_date_range, name='date_range'),
    path('custom-wrapped/', views.custom_wrapped, name='custom_wrapped'),
]