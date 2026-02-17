from collections import Counter
from datetime import datetime
from django.db.models import Count, Q
from ..models import Track, MonthlySummary, WeeklySummary

class DataAggregator:
    @staticmethod
    def get_week_of_month(date):
        """Calculate which week of the month a date falls into"""
        first_day = date.replace(day=1)
        day_of_month = date.day
        adjusted_dom = day_of_month + first_day.weekday()
        return (adjusted_dom - 1) // 7 + 1
    
    @staticmethod
    def aggregate_monthly(user, year, month):
        """Aggregate monthly stats for a user"""
        month_str = f"{year}-{month:02d}"
        
        # Get all tracks for the month
        tracks = Track.objects.filter(
            spotify_user=user,
            year=year,
            month=month_str
        )
        
        if not tracks.exists():
            return None
        
        # Calculate basic stats
        total_plays = tracks.count()
        unique_tracks = tracks.values('spotify_track_id').distinct().count()
        unique_artists = tracks.values('artist_id').distinct().count()
        
        # Get top tracks
        track_counts = Counter(tracks.values_list('track_name', 'artist_name', 'spotify_track_id'))
        top_tracks = [
            {
                'name': track[0],
                'artist': track[1],
                'track_id': track[2],
                'plays': count
            }
            for track, count in track_counts.most_common(10)
        ]
        
        # Get top artists
        artist_counts = Counter(tracks.values_list('artist_name', 'artist_id'))
        top_artists = [
            {
                'name': artist[0],
                'artist_id': artist[1],
                'plays': count
            }
            for artist, count in artist_counts.most_common(10)
        ]
        
        # Create or update monthly summary
        summary, created = MonthlySummary.objects.update_or_create(
            spotify_user=user,
            month=month_str,
            defaults={
                'total_plays': total_plays,
                'unique_tracks': unique_tracks,
                'unique_artists': unique_artists,
                'top_tracks': top_tracks,
                'top_artists': top_artists
            }
        )
        
        return summary
    
    @staticmethod
    def aggregate_weekly(user, year, month, week):
        """Aggregate weekly stats for a user"""
        month_str = f"{year}-{month:02d}"
        
        # Get tracks for specific week
        tracks = Track.objects.filter(
            spotify_user=user,
            year=year,
            month=month_str,
            week=week
        )
        
        if not tracks.exists():
            return None
        
        # Calculate basic stats
        total_plays = tracks.count()
        unique_tracks = tracks.values('spotify_track_id').distinct().count()
        unique_artists = tracks.values('artist_id').distinct().count()
        
        # Get top tracks
        track_counts = Counter(tracks.values_list('track_name', 'artist_name', 'spotify_track_id'))
        top_tracks = [
            {
                'name': track[0],
                'artist': track[1],
                'track_id': track[2],
                'plays': count
            }
            for track, count in track_counts.most_common(10)
        ]
        
        # Get top artists
        artist_counts = Counter(tracks.values_list('artist_name', 'artist_id'))
        top_artists = [
            {
                'name': artist[0],
                'artist_id': artist[1],
                'plays': count
            }
            for artist, count in artist_counts.most_common(10)
        ]
        
        # Create or update weekly summary
        summary, created = WeeklySummary.objects.update_or_create(
            spotify_user=user,
            month=month_str,
            week=week,
            defaults={
                'total_plays': total_plays,
                'unique_tracks': unique_tracks,
                'unique_artists': unique_artists,
                'top_tracks': top_tracks,
                'top_artists': top_artists
            }
        )
        
        return summary
    
    @staticmethod
    def get_available_months(user):
        """Get all months with data for a user"""
        months = Track.objects.filter(
            spotify_user=user
        ).values_list('year', 'month').distinct().order_by('-year', '-month')
        
        return [(year, month) for year, month in months]