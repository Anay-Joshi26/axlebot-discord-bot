import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

import random
import string

def generate_random_string(length=17):  # 0 to 16 inclusive = 17 characters
    charset = string.ascii_lowercase + string.digits
    return ''.join(random.choice(charset) for _ in range(length))


sp_oauth = SpotifyOAuth(
    client_id = 'ee20120b0624492e81d7d3b2839b5b64', #os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = '671f8a5f2a0d41fdb71f1b59e09e97a8', #os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri='https://mystictide.github.io/explore-spotify',
    scope="user-read-private user-top-read playlist-modify-private",
    cache_path=".spotify_token_cache",
    state = generate_random_string()
)

sp = spotipy.Spotify(auth_manager=sp_oauth)

track = sp.track("0VjIjW4GlUZAMYd2vXMi3b")
print(track["name"])

recs = sp.recommendations(seed_tracks=["0VjIjW4GlUZAMYd2vXMi3b"], limit=10)
print(recs["tracks"])

# auth_url = sp_oauth.get_authorize_url().replace("response_type=token", "response_type=code")
# print("Open this in a browser:\n", auth_url)

# # # from urllib.parse import urlparse, parse_qs

# response = input("Paste the full redirect URL here: ").strip()


# code = sp_oauth.parse_response_code(response)
# token_info = sp_oauth.get_access_token(code)
# access_token = token_info["access_token"]
# print("Access Token:", access_token)

# import spotipy
# from spotipy.oauth2 import SpotifyOAuth
# # Spotify API credentials
# CLIENT_ID = 'ee20120b0624492e81d7d3b2839b5b64'#os.getenv("SPOTIFY_CLIENT_ID")
# CLIENT_SECRET = '671f8a5f2a0d41fdb71f1b59e09e97a8'#os.getenv("SPOTIFY_CLIENT_SECRET")
# REDIRECT_URI = 'http://127.0.0.1:8888/callback'
# SCOPE = None
# # Initialize Spotify client
# sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
#     client_id=CLIENT_ID,
#     client_secret=CLIENT_SECRET,
#     redirect_uri=REDIRECT_URI,
#     scope=SCOPE
# ))
# def get_recommendations(seed_tracks, seed_genres, limit=20):
#     try:
#         recommendations = sp.recommendations(seed_tracks=seed_tracks, seed_genres=seed_genres, limit=limit)
#         return [track['id'] for track in recommendations['tracks']]
#     except spotipy.exceptions.SpotifyException as e:
#         print(f"Error fetching recommendations: {e}")
#         return []
# # Example usage
# track = sp.track("0VjIjW4GlUZAMYd2vXMi3b")
# print(track["name"])

# seed_tracks = ['0cGG2EouYCEEC3xfa0tDFV', '7lQ8MOhq6IN2w8EYcFNSUk']
# seed_genres = ['pop']
# print(get_recommendations(seed_tracks, seed_genres))
