import requests
from datetime import datetime
from django.utils import timezone

class SpotifyAPI:
    def __init__(self, access_token):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}"
        }
    
    def get_recently_played(self, limit=50):
        url = f"https://api.spotify.com/v1/me/player/recently-played?limit={limit}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json().get('items', [])
        return []
    
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