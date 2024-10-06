import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, jsonify, session, redirect, url_for
import pandas as pd
from flask_cors import CORS
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Set the secret key

# Configure CORS with support for credentials
CORS(app, supports_credentials=True)

# Spotify Configuration
CLIENT_ID = '32ccc9ec381e496f972bf5e369506ea4'
CLIENT_SECRET = 'c615cb440af14c4e8a577919371b3490'
REDIRECT_URI = 'http://localhost:5000/callback'
SCOPE = 'user-library-read user-top-read playlist-modify-private playlist-modify-public'

# Route for login and OAuth
@app.route('/login')
def login():
    sp_oauth = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                            redirect_uri=REDIRECT_URI, scope=SCOPE)
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

# Callback route to handle the redirect from Spotify with the authorization code
@app.route('/callback')
def callback():
    sp_oauth = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                            redirect_uri=REDIRECT_URI, scope=SCOPE)
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('index'))

# Function to retrieve Spotify client with the stored token
def get_spotify_client():
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('login'))
    
    sp = spotipy.Spotify(auth=token_info['access_token'])
    return sp

# Homepage route after login
@app.route('/')
def index():
    return 'Logged in successfully! You can now create playlists.'

# Route to create a playlist based on mood
@app.route("/create-playlist", methods=["POST"])
def create_playlist():
    try:
        # Retrieve JSON data from frontend
        data = request.json
        mood = data.get("mood")
        playlist_name = data.get("playlist_name", "My Mood Playlist")

        # Get Spotify client, redirect if not authenticated
        sp = get_spotify_client()
        if isinstance(sp, redirect):
            return sp  # Redirect to login if user is not authenticated

        # Fetch user's top artists
        top_artists = sp.current_user_top_artists(limit=10)
        artist_ids = [artist['id'] for artist in top_artists['items']]
        track_data = []

        # Fetch songs from user's top artists
        for artist_id in artist_ids:
            artist_top_tracks = sp.artist_top_tracks(artist_id)['tracks']
            for track in artist_top_tracks:
                track_id = track['id']
                track_name = track['name']
                features = sp.audio_features(track_id)[0]
                track_data.append({
                    'track_name': track_name,
                    'artist_name': track['artists'][0]['name'],
                    'tempo': features['tempo'],
                    'energy': features['energy'],
                    'valence': features['valence'],
                    'danceability': features['danceability'],
                    'acousticness': features['acousticness']
                })

        # Convert track data to a DataFrame for easier filtering
        df = pd.DataFrame(track_data)

        # Function to filter songs based on mood
        def filter_songs_by_mood(mood):
            if mood == 'happy':
                return df[(df['valence'] > 0.5) & (df['energy'] > 0.5)]
            elif mood == 'calm':
                return df[(df['energy'] < 0.5) & (df['valence'] > 0.5)]
            elif mood == 'sad':
                return df[df['valence'] < 0.5]
            elif mood == 'energetic':
                return df[df['energy'] > 0.7]
            else:
                return df

        # Filter tracks based on the selected mood
        filtered_songs = filter_songs_by_mood(mood).head(20)  # Limit to 20 songs

        # Create a playlist for the user
        try:
            user_id = sp.current_user()['id']
            playlist = sp.user_playlist_create(user_id, playlist_name, public=False)
            playlist_id = playlist['id']
        except Exception as e:
            print(f"Error creating playlist: {e}")
            return jsonify({"error": "Failed to create playlist"}), 500

        # Add tracks to the playlist
        track_ids = []
        for index, row in filtered_songs.iterrows():
            search_result = sp.search(q=f"track:{row['track_name']} artist:{row['artist_name']}", type='track')
            if search_result['tracks']['items']:
                track_ids.append(search_result['tracks']['items'][0]['id'])

        sp.playlist_add_items(playlist_id, track_ids)

        # Return the playlist link
        return jsonify({"playlistLink": playlist['external_urls']['spotify']})

    except spotipy.exceptions.SpotifyException as e:
        print(f"Spotify API error: {e}")
        return jsonify({"error": "Spotify API error"}), 500
    except Exception as e:
        print(f"General error: {e}")
        return jsonify({"error": "Something went wrong!"}), 500

if __name__ == "__main__":
    app.run(debug=True)
