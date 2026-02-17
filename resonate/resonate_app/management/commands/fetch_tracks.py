from django.core.management.base import BaseCommand
from django.utils import timezone
from resonate_app.models import SpotifyUser, Track
from resonate_app.utils.spotify_api import SpotifyAPI
from resonate_app.utils.auth import SpotifyAuth
from resonate_app.utils.aggregator import DataAggregator
from datetime import datetime

class Command(BaseCommand):
    help = 'Fetch recent tracks for all users'
    
    def handle(self, *args, **options):
        users = SpotifyUser.objects.all()
        
        for user in users:
            self.stdout.write(f"Processing user: {user.display_name}")
            
            # Check if token needs refresh
            if not user.is_token_valid():
                self.stdout.write("Token expired, refreshing...")
                auth = SpotifyAuth()
                new_token = auth.refresh_token(user.refresh_token)
                
                if new_token:
                    user.access_token = new_token['access_token']
                    user.token_expires_at = new_token['expires_at']
                    if 'refresh_token' in new_token:
                        user.refresh_token = new_token['refresh_token']
                    user.save()
                else:
                    self.stdout.write(self.style.ERROR("Failed to refresh token"))
                    continue
            
            # Fetch recent tracks
            api = SpotifyAPI(user.access_token)
            recent_tracks = api.get_recently_played(limit=50)
            
            tracks_created = 0
            for item in recent_tracks:
                track = item['track']
                played_at = datetime.strptime(item['played_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
                
                # Calculate month and week
                month_str = played_at.strftime('%Y-%m')
                week = DataAggregator.get_week_of_month(played_at)
                
                # Check if track already exists
                if not Track.objects.filter(
                    spotify_user=user,
                    spotify_track_id=track['id'],
                    played_at=played_at
                ).exists():
                    
                    Track.objects.create(
                        spotify_user=user,
                        spotify_track_id=track['id'],
                        track_name=track['name'],
                        artist_name=track['artists'][0]['name'],
                        artist_id=track['artists'][0]['id'],
                        album_name=track['album']['name'],
                        album_image_url=track['album']['images'][0]['url'] if track['album']['images'] else None,
                        duration_ms=track['duration_ms'],
                        played_at=played_at,
                        month=month_str,
                        week=week,
                        year=played_at.year
                    )
                    tracks_created += 1
            
            self.stdout.write(self.style.SUCCESS(f"Created {tracks_created} new tracks"))
            
            # Update monthly and weekly summaries
            current_date = timezone.now()
            DataAggregator.aggregate_monthly(user, current_date.year, current_date.month)
            DataAggregator.aggregate_weekly(user, current_date.year, current_date.month, 
                                          DataAggregator.get_week_of_month(current_date))