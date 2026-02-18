# resonate_app/utils/spotify_api.py

import requests
from datetime import datetime, timedelta
from django.utils import timezone

class SpotifyAPI:
    def __init__(self, access_token):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}"
        }
    
    def get_recently_played(self, limit=50, after=None, before=None):
        """Get recently played tracks with optional time filters"""
        url = "https://api.spotify.com/v1/me/player/recently-played"
        params = {'limit': min(limit, 50)}
        
        if after:
            params['after'] = int(after.timestamp() * 1000)
        if before:
            params['before'] = int(before.timestamp() * 1000)
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            return response.json().get('items', [])
        elif response.status_code == 401:
            # Token expired
            return None
        return []
    
    def get_all_recently_played(self, limit=50, max_requests=10):
        """Fetch multiple pages of recently played tracks"""
        all_tracks = []
        last_timestamp = None
        
        for _ in range(max_requests):
            if last_timestamp:
                # Get tracks before the last timestamp
                tracks = self.get_recently_played(limit=50, before=last_timestamp)
            else:
                tracks = self.get_recently_played(limit=50)
            
            if not tracks:
                break
                
            all_tracks.extend(tracks)
            
            if len(tracks) < 50:
                break
                
            # Get the oldest track's timestamp for next page
            last_timestamp = datetime.strptime(
                tracks[-1]['played_at'].split('.')[0], 
                '%Y-%m-%dT%H:%M:%S'
            )
            last_timestamp = timezone.make_aware(last_timestamp)
        
        return all_tracks[:limit] if limit else all_tracks
    
    def get_recently_played_date_range(self, start_date, end_date):
        """Get all tracks between two dates"""
        all_tracks = []
        current_end = end_date
        
        while current_end > start_date:
            # Get tracks before current_end
            tracks = self.get_recently_played(limit=50, before=current_end)
            
            if not tracks:
                break
            
            # Filter tracks within date range
            for item in tracks:
                played_at = datetime.strptime(
                    item['played_at'].split('.')[0], 
                    '%Y-%m-%dT%H:%M:%S'
                )
                played_at = timezone.make_aware(played_at)
                
                if played_at >= start_date:
                    all_tracks.append(item)
                else:
                    # If we've gone past start_date, break the loop
                    return all_tracks
            
            if len(tracks) < 50:
                break
                
            # Update current_end to the oldest track's timestamp
            current_end = datetime.strptime(
                tracks[-1]['played_at'].split('.')[0], 
                '%Y-%m-%dT%H:%M:%S'
            )
            current_end = timezone.make_aware(current_end)
        
        return all_tracks
    
    def get_user_profile(self):
        url = "https://api.spotify.com/v1/me"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        return None
    
    def get_track_details(self, track_id):
        url = f"https://api.spotify.com/v1/tracks/{track_id}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        return None