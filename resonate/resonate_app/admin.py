from django.contrib import admin
from .models import SpotifyUser, Track, MonthlySummary, WeeklySummary

@admin.register(SpotifyUser)
class SpotifyUserAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'spotify_id', 'email', 'last_login']
    search_fields = ['display_name', 'email']

@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ['track_name', 'artist_name', 'played_at', 'spotify_user']
    list_filter = ['spotify_user', 'year', 'month']
    search_fields = ['track_name', 'artist_name']
    date_hierarchy = 'played_at'

@admin.register(MonthlySummary)
class MonthlySummaryAdmin(admin.ModelAdmin):
    list_display = ['spotify_user', 'month', 'total_plays', 'unique_tracks']
    list_filter = ['spotify_user', 'month']

@admin.register(WeeklySummary)
class WeeklySummaryAdmin(admin.ModelAdmin):
    list_display = ['spotify_user', 'month', 'week', 'total_plays']
    list_filter = ['spotify_user', 'month']