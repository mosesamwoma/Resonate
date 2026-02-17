from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

class SpotifyUser(models.Model):
    spotify_id = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=200)
    email = models.EmailField(null=True, blank=True)
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name

    def is_token_valid(self):
        return timezone.now() < self.token_expires_at

class Track(models.Model):
    spotify_user = models.ForeignKey(SpotifyUser, on_delete=models.CASCADE, related_name='tracks')
    spotify_track_id = models.CharField(max_length=100)
    track_name = models.CharField(max_length=300)
    artist_name = models.CharField(max_length=300)
    artist_id = models.CharField(max_length=100, null=True, blank=True)
    album_name = models.CharField(max_length=300, null=True, blank=True)
    album_image_url = models.URLField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    played_at = models.DateTimeField()
    month = models.CharField(max_length=7)  # YYYY-MM
    week = models.IntegerField()  # 1-5
    year = models.IntegerField()
    
    class Meta:
        ordering = ['-played_at']
        indexes = [
            models.Index(fields=['spotify_user', 'month']),
            models.Index(fields=['spotify_user', 'year']),
            models.Index(fields=['played_at']),
        ]

    def __str__(self):
        return f"{self.track_name} - {self.artist_name}"

class MonthlySummary(models.Model):
    spotify_user = models.ForeignKey(SpotifyUser, on_delete=models.CASCADE)
    month = models.CharField(max_length=7)  # YYYY-MM
    total_plays = models.IntegerField(default=0)
    unique_tracks = models.IntegerField(default=0)
    unique_artists = models.IntegerField(default=0)
    top_tracks = models.JSONField(default=list)  # Store top tracks as JSON
    top_artists = models.JSONField(default=list)  # Store top artists as JSON
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['spotify_user', 'month']

class WeeklySummary(models.Model):
    spotify_user = models.ForeignKey(SpotifyUser, on_delete=models.CASCADE)
    month = models.CharField(max_length=7)
    week = models.IntegerField()  # 1-5
    total_plays = models.IntegerField(default=0)
    unique_tracks = models.IntegerField(default=0)
    unique_artists = models.IntegerField(default=0)
    top_tracks = models.JSONField(default=list)
    top_artists = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['spotify_user', 'month', 'week']