# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import base64
import requests
from collections import Counter
import sqlite3
import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import time
import urllib.parse
import secrets

# ============ Configuration and Setup ============
st.set_page_config(
    page_title="Resonate - Spotify Wrapped",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1DB954 0%, #1ED760 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    .stat-card {
        background: #282828;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        color: white;
        border-left: 4px solid #1DB954;
        margin: 0.5rem 0;
    }
    .track-item {
        background: #181818;
        padding: 0.8rem;
        margin: 0.3rem 0;
        border-radius: 5px;
        border-left: 3px solid #1DB954;
    }
    .artist-item {
        background: #181818;
        padding: 0.8rem;
        margin: 0.3rem 0;
        border-radius: 5px;
        border-left: 3px solid #1ED760;
    }
    .badge-success {
        background: #1DB954;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.9rem;
    }
    .stButton button {
        background-color: #1DB954;
        color: white;
        border: none;
        border-radius: 20px;
        padding: 0.5rem 2rem;
        font-weight: bold;
        width: 100%;
    }
    .stButton button:hover {
        background-color: #1ED760;
    }
    .auth-container {
        text-align: center;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin: 2rem 0;
        color: white;
    }
    .auth-button {
        background-color: #1DB954;
        color: white;
        border: none;
        padding: 1rem 2rem;
        border-radius: 30px;
        font-size: 1.2rem;
        font-weight: bold;
        cursor: pointer;
        text-decoration: none;
        display: inline-block;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    .auth-button:hover {
        background-color: #1ED760;
        transform: scale(1.05);
    }
    .info-box {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ============ Database Setup ============
def init_database():
    conn = sqlite3.connect('resonate.db')
    c = conn.cursor()
    
    # Create users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spotify_id TEXT UNIQUE,
            display_name TEXT,
            email TEXT,
            access_token TEXT,
            refresh_token TEXT,
            token_expires_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create tracks table
    c.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            spotify_user_id INTEGER,
            spotify_track_id TEXT,
            track_name TEXT,
            artist_name TEXT,
            artist_id TEXT,
            album_name TEXT,
            album_image_url TEXT,
            duration_ms INTEGER,
            played_at TEXT,
            month TEXT,
            week INTEGER,
            year INTEGER,
            FOREIGN KEY (spotify_user_id) REFERENCES users (id)
        )
    ''')
    
    # Create indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_tracks_user_month ON tracks(spotify_user_id, month)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_tracks_played_at ON tracks(played_at)')
    
    conn.commit()
    conn.close()

# Initialize database
init_database()

# ============ Database Helper Functions ============
def get_db_connection():
    return sqlite3.connect('resonate.db')

def save_user(user_data):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Check if user exists
    c.execute('SELECT id FROM users WHERE spotify_id = ?', (user_data['spotify_id'],))
    existing = c.fetchone()
    
    if existing:
        # Update existing user
        c.execute('''
            UPDATE users 
            SET display_name = ?, email = ?, access_token = ?, refresh_token = ?, token_expires_at = ?, last_login = CURRENT_TIMESTAMP
            WHERE spotify_id = ?
        ''', (
            user_data['display_name'],
            user_data['email'],
            user_data['access_token'],
            user_data['refresh_token'],
            user_data['token_expires_at'],
            user_data['spotify_id']
        ))
        user_id = existing[0]
    else:
        # Insert new user
        c.execute('''
            INSERT INTO users 
            (spotify_id, display_name, email, access_token, refresh_token, token_expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_data['spotify_id'],
            user_data['display_name'],
            user_data['email'],
            user_data['access_token'],
            user_data['refresh_token'],
            user_data['token_expires_at']
        ))
        user_id = c.lastrowid
    
    conn.commit()
    conn.close()
    return user_id

def get_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    
    if user:
        return {
            'id': user[0],
            'spotify_id': user[1],
            'display_name': user[2],
            'email': user[3],
            'access_token': user[4],
            'refresh_token': user[5],
            'token_expires_at': user[6]
        }
    return None

def save_tracks(user_id, tracks):
    if not tracks:
        return 0
        
    conn = get_db_connection()
    c = conn.cursor()
    tracks_created = 0
    
    for track in tracks:
        # Check if track already exists
        c.execute('''
            SELECT id FROM tracks 
            WHERE spotify_user_id = ? AND spotify_track_id = ? AND played_at = ?
        ''', (user_id, track['track_id'], track['played_at']))
        
        if not c.fetchone():
            c.execute('''
                INSERT INTO tracks 
                (spotify_user_id, spotify_track_id, track_name, artist_name, artist_id, 
                 album_name, album_image_url, duration_ms, played_at, month, week, year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                track['track_id'],
                track['track_name'],
                track['artist_name'],
                track['artist_id'],
                track['album_name'],
                track['album_image_url'],
                track['duration_ms'],
                track['played_at'],
                track['month'],
                track['week'],
                track['year']
            ))
            tracks_created += 1
    
    conn.commit()
    conn.close()
    return tracks_created

def get_user_tracks(user_id, start_date=None, end_date=None, month=None, week=None):
    conn = get_db_connection()
    c = conn.cursor()
    
    query = 'SELECT * FROM tracks WHERE spotify_user_id = ?'
    params = [user_id]
    
    if start_date and end_date:
        query += ' AND played_at BETWEEN ? AND ?'
        params.extend([start_date, end_date])
    
    if month:
        query += ' AND month = ?'
        params.append(month)
    
    if week is not None:
        query += ' AND week = ?'
        params.append(week)
    
    query += ' ORDER BY played_at DESC'
    
    c.execute(query, params)
    tracks = c.fetchall()
    conn.close()
    
    return [{
        'id': t[0],
        'spotify_user_id': t[1],
        'spotify_track_id': t[2],
        'track_name': t[3],
        'artist_name': t[4],
        'artist_id': t[5],
        'album_name': t[6],
        'album_image_url': t[7],
        'duration_ms': t[8],
        'played_at': t[9],
        'month': t[10],
        'week': t[11],
        'year': t[12]
    } for t in tracks]

def get_available_months(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        SELECT DISTINCT year, month FROM tracks 
        WHERE spotify_user_id = ? 
        ORDER BY year DESC, month DESC
    ''', (user_id,))
    months = c.fetchall()
    conn.close()
    return months

def get_user_stats(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Total tracks
    c.execute('SELECT COUNT(*) FROM tracks WHERE spotify_user_id = ?', (user_id,))
    total_tracks = c.fetchone()[0]
    
    # Unique tracks
    c.execute('SELECT COUNT(DISTINCT spotify_track_id) FROM tracks WHERE spotify_user_id = ?', (user_id,))
    unique_tracks = c.fetchone()[0]
    
    # Unique artists
    c.execute('SELECT COUNT(DISTINCT artist_id) FROM tracks WHERE spotify_user_id = ?', (user_id,))
    unique_artists = c.fetchone()[0]
    
    # Months active
    c.execute('SELECT COUNT(DISTINCT month) FROM tracks WHERE spotify_user_id = ?', (user_id,))
    months_active = c.fetchone()[0]
    
    # First and last track dates
    c.execute('SELECT MIN(played_at), MAX(played_at) FROM tracks WHERE spotify_user_id = ?', (user_id,))
    result = c.fetchone()
    first_date = result[0] if result else None
    last_date = result[1] if result else None
    
    conn.close()
    
    return {
        'total_tracks': total_tracks,
        'unique_tracks': unique_tracks,
        'unique_artists': unique_artists,
        'months_active': months_active,
        'first_date': first_date,
        'last_date': last_date
    }

# ============ Spotify API Helpers ============
class SpotifyAuth:
    def __init__(self):
        self.client_id = st.secrets.get("SPOTIPY_CLIENT_ID", "")
        self.client_secret = st.secrets.get("SPOTIPY_CLIENT_SECRET", "")
        self.redirect_uri = st.secrets.get("SPOTIPY_REDIRECT_URI", "http://localhost:8501")
        
    def get_auth_url(self):
        scope = 'user-read-recently-played user-top-read'
        
        # Generate a random state for security
        state = secrets.token_urlsafe(32)
        st.session_state['oauth_state'] = state
        
        auth_url = (
            f"https://accounts.spotify.com/authorize"
            f"?client_id={self.client_id}"
            f"&response_type=code"
            f"&redirect_uri={self.redirect_uri}"
            f"&scope={scope}"
            f"&state={state}"
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
        
        try:
            response = requests.post(url, headers=headers, data=data, timeout=10)
            if response.status_code == 200:
                token_info = response.json()
                # Calculate expiration time
                expires_at = (datetime.now() + timedelta(seconds=token_info['expires_in'])).isoformat()
                token_info['expires_at'] = expires_at
                return token_info
            else:
                st.error(f"Spotify API error: {response.status_code}")
                if response.status_code == 400:
                    st.error("Invalid authorization code. Please try again.")
                return None
        except requests.exceptions.RequestException as e:
            st.error(f"Network error: {str(e)}")
            return None

class SpotifyAPI:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://api.spotify.com/v1"
        self.headers = {"Authorization": f"Bearer {access_token}"}
    
    def get_user_profile(self):
        try:
            response = requests.get(f"{self.base_url}/me", headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                st.error("Access token expired. Please login again.")
                return None
            else:
                st.error(f"Failed to get user profile: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            st.error(f"Network error: {str(e)}")
            return None
    
    def get_recently_played(self, limit=50, after=None):
        params = {"limit": limit}
        if after:
            params["after"] = after
        
        try:
            response = requests.get(f"{self.base_url}/me/player/recently-played", 
                                   headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except requests.exceptions.RequestException:
            return None
    
    def get_all_recently_played(self, limit=500):
        all_tracks = []
        after = None
        
        while len(all_tracks) < limit:
            data = self.get_recently_played(limit=50, after=after)
            if not data or not data.get('items'):
                break
            
            items = data['items']
            all_tracks.extend(items)
            
            if len(items) < 50:
                break
            
            # Get timestamp of last track for pagination
            if items:
                after = items[-1]['played_at']
            
            time.sleep(0.1)  # Rate limiting
        
        return all_tracks[:limit]

# ============ Data Processing Functions ============
def process_tracks(tracks, user_id):
    """Process raw Spotify tracks into our format"""
    processed = []
    
    for item in tracks:
        try:
            track = item['track']
            played_at = datetime.fromisoformat(item['played_at'].replace('Z', '+00:00'))
            
            # Calculate month and week
            month_str = played_at.strftime('%Y-%m')
            week = get_week_of_month(played_at)
            
            processed.append({
                'track_id': track['id'],
                'track_name': track['name'],
                'artist_name': track['artists'][0]['name'],
                'artist_id': track['artists'][0]['id'],
                'album_name': track['album']['name'],
                'album_image_url': track['album']['images'][0]['url'] if track['album']['images'] else None,
                'duration_ms': track['duration_ms'],
                'played_at': played_at.isoformat(),
                'month': month_str,
                'week': week,
                'year': played_at.year
            })
        except Exception as e:
            continue
    
    return processed

def get_week_of_month(date):
    """Calculate which week of the month a date falls into"""
    first_day = date.replace(day=1)
    day_of_month = date.day
    adjusted_dom = day_of_month + first_day.weekday()
    return (adjusted_dom - 1) // 7 + 1

def aggregate_tracks(tracks):
    """Aggregate track data for summaries"""
    if not tracks:
        return None
    
    total_plays = len(tracks)
    
    # Count tracks
    track_counts = {}
    for track in tracks:
        key = f"{track['spotify_track_id']}_{track['track_name']}_{track['artist_name']}"
        if key in track_counts:
            track_counts[key]['plays'] += 1
        else:
            track_counts[key] = {
                'name': track['track_name'],
                'artist': track['artist_name'],
                'track_id': track['spotify_track_id'],
                'plays': 1
            }
    
    top_tracks = sorted(track_counts.values(), key=lambda x: x['plays'], reverse=True)[:10]
    
    # Count artists
    artist_counts = {}
    for track in tracks:
        if track['artist_name'] in artist_counts:
            artist_counts[track['artist_name']]['plays'] += 1
        else:
            artist_counts[track['artist_name']] = {
                'name': track['artist_name'],
                'artist_id': track['artist_id'],
                'plays': 1
            }
    
    top_artists = sorted(artist_counts.values(), key=lambda x: x['plays'], reverse=True)[:10]
    
    # Unique counts
    unique_tracks = len(set(t['spotify_track_id'] for t in tracks))
    unique_artists = len(set(t['artist_id'] for t in tracks))
    
    return {
        'total_plays': total_plays,
        'unique_tracks': unique_tracks,
        'unique_artists': unique_artists,
        'top_tracks': top_tracks,
        'top_artists': top_artists
    }

# ============ Authentication Handler ============
def handle_oauth_callback():
    """Handle OAuth callback from URL parameters"""
    query_params = st.query_params
    
    if "code" in query_params:
        code = query_params["code"]
        
        # Check for state parameter
        received_state = query_params.get("state", [None])[0] if isinstance(query_params.get("state"), list) else query_params.get("state")
        stored_state = st.session_state.get('oauth_state')
        
        # Verify state to prevent CSRF (but make it optional for simplicity)
        if stored_state and received_state and received_state != stored_state:
            st.error("Security state mismatch. Please try again.")
            st.query_params.clear()
            return False
        
        # Clear query params to prevent reprocessing
        st.query_params.clear()
        
        # Get token
        auth = SpotifyAuth()
        with st.spinner("Authenticating with Spotify..."):
            token_info = auth.get_token(code)
            
            if token_info:
                # Get user profile
                api = SpotifyAPI(token_info['access_token'])
                profile = api.get_user_profile()
                
                if profile:
                    user_data = {
                        'spotify_id': profile['id'],
                        'display_name': profile.get('display_name', 'Unknown'),
                        'email': profile.get('email'),
                        'access_token': token_info['access_token'],
                        'refresh_token': token_info.get('refresh_token', ''),
                        'token_expires_at': token_info['expires_at']
                    }
                    
                    user_id = save_user(user_data)
                    st.session_state['user_id'] = user_id
                    st.session_state['user'] = user_data
                    st.session_state['authenticated'] = True
                    
                    st.success(f"✅ Successfully logged in as {user_data['display_name']}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to get user profile from Spotify")
            else:
                st.error("Failed to get access token from Spotify")
        
        return True
    return False

# ============ Streamlit Pages ============
def login_page():
    st.markdown('<div class="main-header"><h1>🎵 Resonate</h1></div>', unsafe_allow_html=True)
    
    # Check for OAuth callback
    if handle_oauth_callback():
        return
    
    # Main login UI
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h2>Track your Spotify listening habits</h2>
            <p style="margin: 2rem 0; font-size: 1.1rem;">
                Get monthly and weekly insights into your music taste, 
                just like Spotify Wrapped but more frequently!
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Feature cards
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("""
            <div class="stat-card">
                <h3>📊 Monthly</h3>
                <p>Monthly summaries of your top tracks and artists</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="stat-card">
                <h3>📅 Weekly</h3>
                <p>Weekly breakdowns of your listening habits</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col_b:
            st.markdown("""
            <div class="stat-card">
                <h3>🎨 Custom</h3>
                <p>Create custom reports for any date range</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div class="stat-card">
                <h3>📈 Trends</h3>
                <p>Track how your music taste evolves over time</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Authentication options
        tab1, tab2 = st.tabs(["🔗 Connect with Spotify", "🔑 Manual Code Entry"])
        
        with tab1:
            auth = SpotifyAuth()
            auth_url = auth.get_auth_url()
            
            st.markdown(f"""
            <div style="text-align: center; margin: 2rem 0;">
                <a href="{auth_url}" target="_blank" class="auth-button">
                    Connect with Spotify
                </a>
                <p style="margin-top: 1rem; color: #666;">
                    You'll be redirected to Spotify to authorize the app
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        with tab2:
            st.markdown("""
            <div class="info-box">
                <strong>📝 Manual Code Entry</strong><br>
                If the automatic redirect doesn't work, you can use this method:
                <ol style="margin-top: 0.5rem;">
                    <li>Click the "Connect with Spotify" button above</li>
                    <li>Authorize the app on Spotify</li>
                    <li>You'll be redirected to a page that might show an error</li>
                    <li>Copy the entire URL from your browser's address bar</li>
                    <li>Paste it below and click Submit</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
            
            callback_url = st.text_area("Paste the callback URL here:", height=100)
            
            if st.button("Submit Authorization", type="primary"):
                if callback_url and "code=" in callback_url:
                    try:
                        # Parse the URL for the code parameter
                        parsed = urllib.parse.urlparse(callback_url)
                        params = urllib.parse.parse_qs(parsed.query)
                        
                        if "code" in params:
                            code = params["code"][0]
                            
                            # Get token
                            auth = SpotifyAuth()
                            with st.spinner("Authenticating..."):
                                token_info = auth.get_token(code)
                                
                                if token_info:
                                    api = SpotifyAPI(token_info['access_token'])
                                    profile = api.get_user_profile()
                                    
                                    if profile:
                                        user_data = {
                                            'spotify_id': profile['id'],
                                            'display_name': profile.get('display_name', 'Unknown'),
                                            'email': profile.get('email'),
                                            'access_token': token_info['access_token'],
                                            'refresh_token': token_info.get('refresh_token', ''),
                                            'token_expires_at': token_info['expires_at']
                                        }
                                        
                                        user_id = save_user(user_data)
                                        st.session_state['user_id'] = user_id
                                        st.session_state['user'] = user_data
                                        st.session_state['authenticated'] = True
                                        
                                        st.success(f"✅ Successfully logged in!")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("Failed to get user profile")
                                else:
                                    st.error("Failed to get access token")
                        else:
                            st.error("No authorization code found in URL")
                    except Exception as e:
                        st.error(f"Error parsing URL: {str(e)}")
                else:
                    st.error("Please paste a valid callback URL containing 'code='")

def dashboard_page():
    st.markdown('<div class="main-header"><h1>🎵 Resonate Dashboard</h1></div>', unsafe_allow_html=True)
    
    user_id = st.session_state['user_id']
    user = st.session_state['user']
    
    # Sidebar with user info
    with st.sidebar:
        st.markdown(f"### 👤 {user['display_name']}")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 📥 Fetch Tracks")
        
        fetch_option = st.radio(
            "Choose fetch option",
            ["Recent (500 tracks)", "Full History", "Custom Date Range"],
            label_visibility="collapsed"
        )
        
        if fetch_option == "Custom Date Range":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start", value=date.today() - timedelta(days=30))
            with col2:
                end_date = st.date_input("End", value=date.today())
            
            if st.button("Fetch Tracks", type="primary", use_container_width=True):
                with st.spinner("Fetching tracks..."):
                    tracks_fetched = fetch_tracks_by_date(user_id, start_date, end_date)
                    if tracks_fetched > 0:
                        st.success(f"✅ Fetched {tracks_fetched} tracks!")
                        time.sleep(1)
                        st.rerun()
        elif fetch_option == "Recent (500 tracks)":
            if st.button("Fetch Recent Tracks", type="primary", use_container_width=True):
                with st.spinner("Fetching recent tracks..."):
                    tracks_fetched = fetch_recent_tracks(user_id)
                    if tracks_fetched > 0:
                        st.success(f"✅ Fetched {tracks_fetched} tracks!")
                        time.sleep(1)
                        st.rerun()
        else:
            if st.button("Fetch Full History", type="primary", use_container_width=True):
                with st.spinner("Fetching full history..."):
                    tracks_fetched = fetch_full_history(user_id)
                    if tracks_fetched > 0:
                        st.success(f"✅ Fetched {tracks_fetched} tracks!")
                        time.sleep(1)
                        st.rerun()
        
        st.markdown("---")
        st.markdown("### 🎨 Quick Actions")
        if st.button("Generate Custom Report", use_container_width=True):
            st.session_state['page'] = 'custom_date_picker'
            st.rerun()
    
    # Main content
    stats = get_user_stats(user_id)
    
    # Quick stats row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{stats['total_tracks']}</h2>
            <p>Total Plays</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{stats['unique_tracks']}</h2>
            <p>Unique Tracks</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{stats['unique_artists']}</h2>
            <p>Unique Artists</p>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{stats['months_active']}</h2>
            <p>Months Active</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Date range covered
    if stats['first_date'] and stats['last_date']:
        try:
            first = datetime.fromisoformat(stats['first_date']).strftime('%b %d, %Y')
            last = datetime.fromisoformat(stats['last_date']).strftime('%b %d, %Y')
            st.info(f"📅 **Date Range Covered:** {first} - {last}")
        except:
            pass
    
    st.markdown("---")
    
    # Current month summary
    current_date = datetime.now()
    current_month = current_date.strftime('%Y-%m')
    current_tracks = get_user_tracks(user_id, month=current_month)
    
    if current_tracks:
        st.markdown(f"### Current Month Summary - {current_date.strftime('%B %Y')}")
        current_summary = aggregate_tracks(current_tracks)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Plays", current_summary['total_plays'])
        with col2:
            st.metric("Unique Tracks", current_summary['unique_tracks'])
        with col3:
            st.metric("Unique Artists", current_summary['unique_artists'])
        
        if st.button("View Full Monthly Wrapped", use_container_width=True):
            st.session_state['selected_month'] = current_month
            st.session_state['page'] = 'monthly'
            st.rerun()
    
    st.markdown("---")
    
    # Two-column layout for historical data
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📅 Previous Months")
        months = get_available_months(user_id)
        if months:
            for year, month in months:
                try:
                    month_name = datetime.strptime(month, '%Y-%m').strftime('%B %Y')
                    if st.button(f"📊 {month_name}", key=f"month_{month}", use_container_width=True):
                        st.session_state['selected_month'] = month
                        st.session_state['page'] = 'monthly'
                        st.rerun()
                except:
                    pass
        else:
            st.info("No historical data yet. Fetch some tracks to get started!")
    
    with col2:
        st.markdown("### 🎵 Quick Stats")
        
        # Most played track overall
        all_tracks = get_user_tracks(user_id)
        if all_tracks:
            summary = aggregate_tracks(all_tracks)
            if summary and summary['top_tracks']:
                top_track = summary['top_tracks'][0]
                st.markdown(f"""
                **Most Played Track:**  
                {top_track['name']} by {top_track['artist']}  
                *{top_track['plays']} plays*
                """)
            
            if summary and summary['top_artists']:
                top_artist = summary['top_artists'][0]
                st.markdown(f"""
                **Most Played Artist:**  
                {top_artist['name']}  
                *{top_artist['plays']} plays*
                """)

def monthly_wrapped_page():
    st.markdown('<div class="main-header"><h1>📊 Monthly Wrapped</h1></div>', unsafe_allow_html=True)
    
    user_id = st.session_state['user_id']
    month = st.session_state['selected_month']
    
    # Breadcrumb navigation
    col1, col2 = st.columns([1, 11])
    with col1:
        if st.button("← Back"):
            st.session_state['page'] = 'dashboard'
            st.rerun()
    
    # Parse month
    try:
        year, month_num = map(int, month.split('-'))
        month_name = datetime(year, month_num, 1).strftime('%B %Y')
    except:
        st.error("Invalid month format")
        return
    
    # Get monthly tracks
    tracks = get_user_tracks(user_id, month=month)
    
    if not tracks:
        st.warning(f"No data available for {month_name}")
        return
    
    # Aggregate monthly data
    summary = aggregate_tracks(tracks)
    
    st.markdown(f"## {month_name}")
    
    # Stats cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{summary['total_plays']}</h2>
            <p>Total Plays</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{summary['unique_tracks']}</h2>
            <p>Unique Tracks</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{summary['unique_artists']}</h2>
            <p>Unique Artists</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Top tracks and artists
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Top Tracks")
        for i, track in enumerate(summary['top_tracks'], 1):
            st.markdown(f"""
            <div class="track-item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{i}. {track['name']}</strong><br>
                        <small>{track['artist']}</small>
                    </div>
                    <span class="badge-success">{track['plays']} plays</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### Top Artists")
        for i, artist in enumerate(summary['top_artists'], 1):
            st.markdown(f"""
            <div class="artist-item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{i}. {artist['name']}</strong>
                    </div>
                    <span class="badge-success">{artist['plays']} plays</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Weekly breakdown
    st.markdown("### Weekly Breakdown")
    
    weeks = sorted(set(t['week'] for t in tracks))
    for week_num in weeks:
        week_tracks = [t for t in tracks if t['week'] == week_num]
        week_summary = aggregate_tracks(week_tracks)
        
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"**Week {week_num}**")
        with col2:
            st.markdown(f"🎵 {week_summary['total_plays']} plays")
        with col3:
            if st.button(f"View", key=f"week_{month}_{week_num}"):
                st.session_state['selected_month'] = month
                st.session_state['selected_week'] = week_num
                st.session_state['page'] = 'weekly'
                st.rerun()
        
        # Preview of top track
        if week_summary['top_tracks']:
            st.caption(f"Top: {week_summary['top_tracks'][0]['name']} - {week_summary['top_tracks'][0]['artist']}")
        st.markdown("---")

def weekly_wrapped_page():
    st.markdown('<div class="main-header"><h1>📊 Weekly Wrapped</h1></div>', unsafe_allow_html=True)
    
    user_id = st.session_state['user_id']
    month = st.session_state['selected_month']
    week = st.session_state['selected_week']
    
    # Breadcrumb navigation
    col1, col2 = st.columns([1, 11])
    with col1:
        if st.button("← Back to Month"):
            st.session_state['page'] = 'monthly'
            st.rerun()
    
    # Parse month
    try:
        year, month_num = map(int, month.split('-'))
        month_name = datetime(year, month_num, 1).strftime('%B %Y')
    except:
        st.error("Invalid month format")
        return
    
    st.markdown(f"## {month_name} - Week {week}")
    
    # Get weekly tracks
    tracks = get_user_tracks(user_id, month=month, week=week)
    
    if not tracks:
        st.warning(f"No data available for Week {week}")
        return
    
    # Aggregate weekly data
    summary = aggregate_tracks(tracks)
    
    # Stats cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{summary['total_plays']}</h2>
            <p>Total Plays</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{summary['unique_tracks']}</h2>
            <p>Unique Tracks</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{summary['unique_artists']}</h2>
            <p>Unique Artists</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Top tracks and artists
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"### Top Tracks - Week {week}")
        for i, track in enumerate(summary['top_tracks'], 1):
            st.markdown(f"""
            <div class="track-item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{i}. {track['name']}</strong><br>
                        <small>{track['artist']}</small>
                    </div>
                    <span class="badge-success">{track['plays']} plays</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"### Top Artists - Week {week}")
        for i, artist in enumerate(summary['top_artists'], 1):
            st.markdown(f"""
            <div class="artist-item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{i}. {artist['name']}</strong>
                    </div>
                    <span class="badge-success">{artist['plays']} plays</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

def custom_date_picker_page():
    st.markdown('<div class="main-header"><h1>🎨 Custom Wrapped</h1></div>', unsafe_allow_html=True)
    
    # Breadcrumb navigation
    col1, col2 = st.columns([1, 11])
    with col1:
        if st.button("← Back to Dashboard"):
            st.session_state['page'] = 'dashboard'
            st.rerun()
    
    st.markdown("### Select Date Range")
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", value=date.today())
    
    if start_date > end_date:
        st.error("Start date must be before end date")
        return
    
    if st.button("Generate Custom Wrapped", type="primary", use_container_width=True):
        st.session_state['custom_start'] = start_date.isoformat()
        st.session_state['custom_end'] = end_date.isoformat()
        st.session_state['page'] = 'custom'
        st.rerun()

def custom_wrapped_page():
    st.markdown('<div class="main-header"><h1>🎨 Custom Wrapped</h1></div>', unsafe_allow_html=True)
    
    user_id = st.session_state['user_id']
    
    # Breadcrumb navigation
    col1, col2 = st.columns([1, 11])
    with col1:
        if st.button("← Back to Dashboard"):
            st.session_state['page'] = 'dashboard'
            st.rerun()
    
    # Get custom date range
    start_date = st.session_state['custom_start']
    end_date = st.session_state['custom_end']
    
    st.markdown(f"## {start_date} to {end_date}")
    
    # Get tracks in date range
    start_datetime = datetime.fromisoformat(start_date)
    end_datetime = datetime.fromisoformat(end_date) + timedelta(days=1)
    
    tracks = get_user_tracks(
        user_id, 
        start_date=start_datetime.isoformat(), 
        end_date=end_datetime.isoformat()
    )
    
    if not tracks:
        st.warning("No tracks found in this date range")
        if st.button("Fetch Tracks for this Range"):
            st.session_state['fetch_start'] = start_date
            st.session_state['fetch_end'] = end_date
            st.session_state['page'] = 'dashboard'
            st.rerun()
        return
    
    # Aggregate data
    summary = aggregate_tracks(tracks)
    
    # Stats cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{summary['total_plays']}</h2>
            <p>Total Plays</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{summary['unique_tracks']}</h2>
            <p>Unique Tracks</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <h2>{summary['unique_artists']}</h2>
            <p>Unique Artists</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Top tracks and artists
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Top Tracks")
        for i, track in enumerate(summary['top_tracks'], 1):
            st.markdown(f"""
            <div class="track-item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{i}. {track['name']}</strong><br>
                        <small>{track['artist']}</small>
                    </div>
                    <span class="badge-success">{track['plays']} plays</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### Top Artists")
        for i, artist in enumerate(summary['top_artists'], 1):
            st.markdown(f"""
            <div class="artist-item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{i}. {artist['name']}</strong>
                    </div>
                    <span class="badge-success">{artist['plays']} plays</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ============ Fetch Functions ============
def fetch_recent_tracks(user_id):
    user = get_user(user_id)
    if not user:
        st.error("User not found")
        return 0
    
    api = SpotifyAPI(user['access_token'])
    tracks = api.get_all_recently_played(limit=500)
    
    if tracks:
        processed = process_tracks(tracks, user_id)
        created = save_tracks(user_id, processed)
        return created
    return 0

def fetch_full_history(user_id):
    user = get_user(user_id)
    if not user:
        st.error("User not found")
        return 0
    
    api = SpotifyAPI(user['access_token'])
    all_tracks = []
    
    # Fetch multiple pages
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(10):  # 10 pages max
        status_text.text(f"Fetching page {i+1}/10...")
        tracks = api.get_all_recently_played(limit=50)
        if tracks:
            all_tracks.extend(tracks)
        progress_bar.progress((i + 1) / 10)
        time.sleep(0.5)  # Rate limiting
    
    status_text.empty()
    progress_bar.empty()
    
    if all_tracks:
        # Remove duplicates
        seen = set()
        unique_tracks = []
        for track in all_tracks:
            if track['played_at'] not in seen:
                seen.add(track['played_at'])
                unique_tracks.append(track)
        
        processed = process_tracks(unique_tracks, user_id)
        created = save_tracks(user_id, processed)
        return created
    return 0

def fetch_tracks_by_date(user_id, start_date, end_date):
    user = get_user(user_id)
    if not user:
        st.error("User not found")
        return 0
    
    api = SpotifyAPI(user['access_token'])
    
    # Fetch recent tracks (Spotify API limitation)
    tracks = api.get_all_recently_played(limit=500)
    
    # Filter by date range
    filtered = []
    for track in tracks:
        try:
            played_at = datetime.fromisoformat(track['played_at'].replace('Z', '+00:00'))
            if start_date <= played_at.date() <= end_date:
                filtered.append(track)
        except:
            continue
    
    if filtered:
        processed = process_tracks(filtered, user_id)
        created = save_tracks(user_id, processed)
        return created
    return 0

# ============ Main App ============
def main():
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state['page'] = 'login'
    
    # Check authentication
    if 'user_id' not in st.session_state:
        login_page()
    else:
        # Route to appropriate page
        if st.session_state['page'] == 'dashboard':
            dashboard_page()
        elif st.session_state['page'] == 'monthly':
            monthly_wrapped_page()
        elif st.session_state['page'] == 'weekly':
            weekly_wrapped_page()
        elif st.session_state['page'] == 'custom_date_picker':
            custom_date_picker_page()
        elif st.session_state['page'] == 'custom':
            custom_wrapped_page()
        else:
            dashboard_page()

if __name__ == "__main__":
    main()