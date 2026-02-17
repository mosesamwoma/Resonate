from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from .models import SpotifyUser, Track, MonthlySummary, WeeklySummary
from .utils.auth import SpotifyAuth
from .utils.spotify_api import SpotifyAPI
from .utils.aggregator import DataAggregator
import json

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
    
    context = {
        'user': user,
        'months': months,
        'current_month_data': current_month_data,
        'current_date': current_date
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
    """Manual trigger to fetch tracks"""
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
    
    # Fetch recent tracks
    api = SpotifyAPI(user.access_token)
    recent_tracks = api.get_recently_played(limit=50)
    
    tracks_created = 0
    for item in recent_tracks:
        track = item['track']
        played_at = timezone.datetime.strptime(item['played_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
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
    
    # Update summaries
    current_date = timezone.now()
    DataAggregator.aggregate_monthly(user, current_date.year, current_date.month)
    DataAggregator.aggregate_weekly(user, current_date.year, current_date.month,
                                  DataAggregator.get_week_of_month(current_date))
    
    messages.success(request, f"Fetched {tracks_created} new tracks!")
    return redirect('dashboard')