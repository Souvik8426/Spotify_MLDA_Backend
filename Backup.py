import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd

# Spotify Authentication
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id="32ccc9ec381e496f972bf5e369506ea4",
                                               client_secret="c615cb440af14c4e8a577919371b3490",
                                               redirect_uri="http://localhost:8888/callback",
                                               scope="user-library-read user-top-read playlist-modify-private playlist-modify-public"))

# Fetch user's top artists
def get_top_artists():
    top_artists = sp.current_user_top_artists(limit=10)
    artist_names = [artist['name'] for artist in top_artists['items']]  # Fetch artist names
    artist_ids = [artist['id'] for artist in top_artists['items']]  # Fetch artist ids

    print("Top artists fetched:")
    for artist in artist_names:
        print(f"- {artist}")  # Print each artist's name cleanly
    return artist_ids

# Create a playlist for the user based on their mood and top artists
def create_playlist(mood="happy", playlist_name= input("Enter what name you want the playlist to be: ")):
    try:
        # Get the user's top artists
        artist_ids = get_top_artists()
        
        # Fetch songs by top artists
        track_data = []
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
        print(f"Track data collected: {df.shape[0]} tracks")

        # Filter songs based on mood
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

        # Filter tracks based on the selected mood and limit to 20 songs
        filtered_songs = filter_songs_by_mood(mood).head(20)
        print(f"Filtered songs: {filtered_songs.shape[0]} songs selected for the mood: {mood}")

        # Create a playlist for the user
        user_id = sp.current_user()['id']
        playlist = sp.user_playlist_create(user_id, playlist_name, public=False)
        playlist_id = playlist['id']
        print(f"Playlist created: {playlist_id}")

        # Add tracks to the playlist
        track_ids = []
        for index, row in filtered_songs.iterrows():
            search_result = sp.search(q=f"track:{row['track_name']} artist:{row['artist_name']}", type='track')
            if search_result['tracks']['items']:
                track_ids.append(search_result['tracks']['items'][0]['id'])

        sp.playlist_add_items(playlist_id, track_ids)

        # Return playlist link
        return playlist['external_urls']['spotify']

    except Exception as e:
        print(f"Error: {e}")

# Ask user for their mood preference
mood = input("Select a mood (happy, calm, sad, energetic): ").lower()

# Create the playlist based on mood
playlist_link = create_playlist(mood=mood)
print(f"Your playlist is ready: {playlist_link}")