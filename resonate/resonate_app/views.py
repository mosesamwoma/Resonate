# resonate_app/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from .models import SpotifyUser, Track, MonthlySummary, WeeklySummary
from .utils.auth import SpotifyAuth
from .utils.spotify_api import SpotifyAPI
from .utils.aggregator import DataAggregator
from datetime import datetime, timedelta
import json

# In resonate_app/views.py, update the dashboard function:

def dashboard(request):
    """Main dashboard view"""
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('spotify_login')
    
    try:
        user = SpotifyUser.objects.get(id=user_id)
    except SpotifyUser.DoesNotExist:
        return redirect('spotify_login')
    
    # Get available months
    months = DataAggregator.get_available_months(user)
    
    # Get current month data if available
    current_date = timezone.now()
    current_month_data = MonthlySummary.objects.filter(
        spotify_user=user,
        month=current_date.strftime('%Y-%m')
    ).first()
    
    # Get date range for quick selection
    today = timezone.now().date()
    date_ranges = {
        'last_7_days': {
            'start': today - timedelta(days=7),
            'end': today,
            'label': 'Last 7 Days'
        },
        'last_30_days': {
            'start': today - timedelta(days=30),
            'end': today,
            'label': 'Last 30 Days'
        },
        'last_90_days': {
            'start': today - timedelta(days=90),
            'end': today,
            'label': 'Last 90 Days'
        },
        'last_year': {
            'start': today - timedelta(days=365),
            'end': today,
            'label': 'Last Year'
        }
    }
    
    # Calculate stats for the listening overview section
    total_tracks = user.tracks.count()
    unique_tracks = user.tracks.values('spotify_track_id').distinct().count()
    unique_artists = user.tracks.values('artist_id').distinct().count()
    months_active = user.tracks.values('month').distinct().count()
    
    context = {
        'user': user,
        'months': months,
        'current_month_data': current_month_data,
        'current_date': current_date,
        'date_ranges': date_ranges,
        # Add these new stats
        'total_tracks': total_tracks,
        'unique_tracks': unique_tracks,
        'unique_artists': unique_artists,
        'months_active': months_active,
    }
    
    return render(request, 'resonate_app/dashboard.html', context)

def spotify_login(request):
    """Initiate Spotify OAuth flow"""
    auth = SpotifyAuth()
    auth_url = auth.get_auth_url()
    return redirect(auth_url)

def spotify_callback(request):
    """Handle Spotify OAuth callback"""
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    if error:
        messages.error(request, f"Spotify login failed: {error}")
        return redirect('dashboard')
    
    if not code:
        messages.error(request, "No authorization code received")
        return redirect('dashboard')
    
    # Exchange code for token
    auth = SpotifyAuth()
    token_info = auth.get_token(code)
    
    if not token_info:
        messages.error(request, "Failed to get access token")
        return redirect('dashboard')
    
    # Get user profile
    api = SpotifyAPI(token_info['access_token'])
    profile = api.get_user_profile()
    
    if not profile:
        messages.error(request, "Failed to get user profile")
        return redirect('dashboard')
    
    # Create or update user
    user, created = SpotifyUser.objects.update_or_create(
        spotify_id=profile['id'],
        defaults={
            'display_name': profile.get('display_name', 'Unknown'),
            'email': profile.get('email'),
            'access_token': token_info['access_token'],
            'refresh_token': token_info.get('refresh_token', ''),
            'token_expires_at': token_info['expires_at']
        }
    )
    
    # Store user in session
    request.session['user_id'] = user.id
    
    messages.success(request, f"Successfully logged in as {user.display_name}")
    return redirect('dashboard')

def logout_view(request):
    """Logout user"""
    request.session.flush()
    messages.success(request, "Logged out successfully")
    return redirect('dashboard')

def monthly_wrapped(request, year, month):
    """View monthly wrapped data"""
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('spotify_login')
    
    try:
        user = SpotifyUser.objects.get(id=user_id)
    except SpotifyUser.DoesNotExist:
        return redirect('spotify_login')
    
    month_str = f"{year}-{month:02d}"
    
    # Get or generate monthly summary
    summary = MonthlySummary.objects.filter(
        spotify_user=user,
        month=month_str
    ).first()
    
    if not summary:
        summary = DataAggregator.aggregate_monthly(user, year, month)
    
    # Get weekly breakdowns for this month
    weeks = WeeklySummary.objects.filter(
        spotify_user=user,
        month=month_str
    ).order_by('week')
    
    context = {
        'user': user,
        'summary': summary,
        'weeks': weeks,
        'year': year,
        'month': month,
        'month_name': timezone.datetime(year, month, 1).strftime('%B')
    }
    
    return render(request, 'resonate_app/monthly_wrapped.html', context)

def weekly_wrapped(request, year, month, week):
    """View weekly wrapped data"""
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('spotify_login')
    
    try:
        user = SpotifyUser.objects.get(id=user_id)
    except SpotifyUser.DoesNotExist:
        return redirect('spotify_login')
    
    month_str = f"{year}-{month:02d}"
    
    # Get or generate weekly summary
    summary = WeeklySummary.objects.filter(
        spotify_user=user,
        month=month_str,
        week=week
    ).first()
    
    if not summary:
        summary = DataAggregator.aggregate_weekly(user, year, month, week)
    
    context = {
        'user': user,
        'summary': summary,
        'year': year,
        'month': month,
        'week': week,
        'month_name': timezone.datetime(year, month, 1).strftime('%B')
    }
    
    return render(request, 'resonate_app/weekly_wrapped.html', context)

def fetch_tracks_view(request):
    """Manual trigger to fetch tracks - now with more options"""
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('spotify_login')
    
    try:
        user = SpotifyUser.objects.get(id=user_id)
    except SpotifyUser.DoesNotExist:
        return redirect('spotify_login')
    
    # Check if token needs refresh
    if not user.is_token_valid():
        auth = SpotifyAuth()
        new_token = auth.refresh_token(user.refresh_token)
        
        if new_token:
            user.access_token = new_token['access_token']
            user.token_expires_at = new_token['expires_at']
            if 'refresh_token' in new_token:
                user.refresh_token = new_token['refresh_token']
            user.save()
        else:
            messages.error(request, "Failed to refresh token")
            return redirect('dashboard')
    
    # Get fetch type from request
    fetch_type = request.GET.get('type', 'recent')
    tracks_created = 0
    
    api = SpotifyAPI(user.access_token)
    
    if fetch_type == 'recent':
        # Fetch recent tracks (up to 500)
        recent_tracks = api.get_all_recently_played(limit=500)
        tracks_created = save_tracks(user, recent_tracks)
        messages.success(request, f"Fetched {tracks_created} new tracks from recent history!")
        
    elif fetch_type == 'date_range':
        # Fetch tracks for a specific date range
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date and end_date:
            start = timezone.make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
            end = timezone.make_aware(datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
            
            tracks = api.get_recently_played_date_range(start, end)
            tracks_created = save_tracks(user, tracks)
            messages.success(request, f"Fetched {tracks_created} tracks from {start_date} to {end_date}!")
    
    elif fetch_type == 'full_history':
        # Fetch as much history as possible (up to ~5000 tracks)
        all_tracks = []
        for i in range(10):  # 10 pages of 50 = 500 tracks max
            tracks = api.get_all_recently_played(limit=500, max_requests=10)
            all_tracks.extend(tracks)
        
        # Remove duplicates
        unique_tracks = {t['played_at']: t for t in all_tracks}.values()
        tracks_created = save_tracks(user, list(unique_tracks))
        messages.success(request, f"Fetched {tracks_created} tracks from your listening history!")
    
    # Update summaries for affected months
    update_affected_summaries(user)
    
    return redirect('dashboard')

def save_tracks(user, tracks):
    """Helper function to save tracks"""
    tracks_created = 0
    
    for item in tracks:
        track = item['track']
        played_at = datetime.strptime(item['played_at'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
        played_at = timezone.make_aware(played_at)
        
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
    
    return tracks_created

def update_affected_summaries(user):
    """Update summaries for months that have new data"""
    # Get all months with tracks
    months = Track.objects.filter(spotify_user=user).values_list('month', flat=True).distinct()
    
    for month_str in months:
        year, month = map(int, month_str.split('-'))
        DataAggregator.aggregate_monthly(user, year, month)
        
        # Update weekly summaries for this month
        weeks = Track.objects.filter(
            spotify_user=user, 
            month=month_str
        ).values_list('week', flat=True).distinct()
        
        for week in weeks:
            DataAggregator.aggregate_weekly(user, year, month, week)

def custom_date_range(request):
    """View for custom date range selection"""
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('spotify_login')
    
    try:
        user = SpotifyUser.objects.get(id=user_id)
    except SpotifyUser.DoesNotExist:
        return redirect('spotify_login')
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        # Redirect to fetch with date range
        return redirect(f"{reverse('fetch_tracks')}?type=date_range&start_date={start_date}&end_date={end_date}")
    
    context = {
        'user': user,
        'today': timezone.now().date().isoformat(),
    }
    
    return render(request, 'resonate_app/date_range.html', context)

def custom_wrapped(request):
    """Generate custom wrapped for any date range"""
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('spotify_login')
    
    try:
        user = SpotifyUser.objects.get(id=user_id)
    except SpotifyUser.DoesNotExist:
        return redirect('spotify_login')
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        
        # Make timezone aware
        start = timezone.make_aware(start)
        end = timezone.make_aware(end)
        
        # Get tracks in date range
        tracks = Track.objects.filter(
            spotify_user=user,
            played_at__gte=start,
            played_at__lt=end
        )
        
        if not tracks.exists():
            messages.warning(request, "No tracks found in this date range. Try fetching more tracks!")
            return redirect('dashboard')
        
        # Calculate stats
        total_plays = tracks.count()
        
        # Top tracks
        track_counts = {}
        for track in tracks:
            key = f"{track.spotify_track_id}_{track.track_name}_{track.artist_name}"
            if key in track_counts:
                track_counts[key]['plays'] += 1
            else:
                track_counts[key] = {
                    'name': track.track_name,
                    'artist': track.artist_name,
                    'plays': 1,
                    'track_id': track.spotify_track_id
                }
        
        top_tracks = sorted(track_counts.values(), key=lambda x: x['plays'], reverse=True)[:20]
        
        # Top artists
        artist_counts = {}
        for track in tracks:
            if track.artist_name in artist_counts:
                artist_counts[track.artist_name]['plays'] += 1
            else:
                artist_counts[track.artist_name] = {
                    'name': track.artist_name,
                    'plays': 1,
                    'artist_id': track.artist_id
                }
        
        top_artists = sorted(artist_counts.values(), key=lambda x: x['plays'], reverse=True)[:20]
        
        # Unique tracks and artists
        unique_tracks = tracks.values('spotify_track_id').distinct().count()
        unique_artists = tracks.values('artist_id').distinct().count()
        
        context = {
            'user': user,
            'start_date': start_date,
            'end_date': end_date,
            'total_plays': total_plays,
            'unique_tracks': unique_tracks,
            'unique_artists': unique_artists,
            'top_tracks': top_tracks,
            'top_artists': top_artists,
        }
        
        return render(request, 'resonate_app/custom_wrapped.html', context)
    
    context = {
        'user': user,
        'today': timezone.now().date().isoformat(),
    }
    
    return render(request, 'resonate_app/date_range.html', {'custom_wrapped': True, **context})