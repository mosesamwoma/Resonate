import base64
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings

class SpotifyAuth:
    def __init__(self):
        self.client_id = settings.SPOTIPY_CLIENT_ID
        self.client_secret = settings.SPOTIPY_CLIENT_SECRET
        self.redirect_uri = settings.SPOTIPY_REDIRECT_URI
        
    def get_auth_url(self):
        scope = 'user-read-recently-played user-top-read'
        auth_url = (
            f"https://accounts.spotify.com/authorize"
            f"?client_id={self.client_id}"
            f"&response_type=code"
            f"&redirect_uri={self.redirect_uri}"
            f"&scope={scope}"
        )
        return auth_url
    
    def get_token(self, code):
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('utf-8')
        auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        url = "https://accounts.spotify.com/api/token"
        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_info = response.json()
            token_info['expires_at'] = timezone.now() + timedelta(seconds=token_info['expires_in'])
            return token_info
        return None
    
    def refresh_token(self, refresh_token):
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('utf-8')
        auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        url = "https://accounts.spotify.com/api/token"
        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 200:
            token_info = response.json()
            token_info['expires_at'] = timezone.now() + timedelta(seconds=token_info['expires_in'])
            return token_info
        return None