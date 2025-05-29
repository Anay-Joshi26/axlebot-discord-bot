import aiohttp
from PIL import Image
import io
import asyncio
from youtubesearchpython.__future__ import Search, Playlist, Video, VideosSearch
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from pprint import pprint
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())


client_id = os.getenv("SPOTIFY_CLIENT_ID") 
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")  

# Create an instance of the Spotipy client
client_credentials_manager = SpotifyClientCredentials(
    client_id=client_id, client_secret=client_secret
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

async def extract_embed_color(thumbnail_url):
    print(f"Extracting color from thumbnail URL: {thumbnail_url}")

    async with aiohttp.ClientSession() as session:
        async with session.get(thumbnail_url) as response:
            response.raise_for_status()
            image_data = await response.read()

    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    image = image.resize((100, 100))

    left, top = 25, 25
    right, bottom = 75, 75

    cropped_image = image.crop((left, top, right, bottom))
    print(f"Cropped image size: {cropped_image.size}")
    print(f"Cropped image mode: {cropped_image.mode}")

    average_color = cropped_image.resize((1, 1)).getpixel((0, 0))
    print(f"Average color: {average_color}")

    hex_color = (average_color[0] << 16) + (average_color[1] << 8) + average_color[2]

    return hex_color

async def search_youtube_video_by_url(url):
    video = await Video.getInfo(url)
    title = video['title']

    if 'secondsText' in video['duration']:
        video_length = int(video['duration']['secondsText'])
    # else:
    #     video_length = Song._time_string_to_seconds(video['duration'])

    return title, video_length

def get_spotify_info(query):
    list_type = None
    if "open.spotify.com/album/" in query:
        list_type = "album"
    elif "open.spotify.com/playlist/" in query:
        list_type = "playlist"
    else:
        raise ValueError("Invalid Spotify URL. Must be an album or playlist.")

    if list_type == 'playlist':
        playlist_tracks = sp.playlist_tracks(query)
        track_info = [
            (
                track["track"]["name"],
                track["track"]["artists"][0]["name"],
                track["track"]["album"]["images"][0]["url"]
                or track["track"]["artist"]["images"][0]["url"],
            )
            for track in playlist_tracks["items"]
        ]
        print(track_info)
        return track_info
    elif list_type == 'album':
        album = sp.album(query)
        album_thumbnail = album['images'][0]['url']

        tracks = album['tracks']['items']

        track_info = []
        for track in tracks:
            track_name = track['name']
            artist_name = track['artists'][0]['name']
            track_info.append((
                track_name,
                artist_name,
                album_thumbnail
            ))
        return track_info
    
    return None

async def run():
    # thumbnail_url = "https://i.scdn.co/image/ab67616d0000b273806c160566580d6335d1f16c"
    # color = await extract_embed_color(thumbnail_url)
    # print(f"Extracted color: {color:#06x}")

    # url = 'https://www.youtube.com/watch?v=XXYuWEuKI&pp=ygUWc2F2ZSB5b3VyIHRlYXJzIHdlZWtuZA%3D%3D'
    # title, video_length = await search_youtube_video_by_url(url)
    # print(f"Title: {title}, Video Length: {video_length} seconds")

    #url = 'https://open.spotify.com/album/3Gt7rOjcZQoHCfnKl5AkK7'
    url = 'https://open.spotify.com/playlist/5yY9EbSoqW4MeThXYUwYo9'

    track_info = get_spotify_info(url)
    print("Track Info:", track_info)

if __name__ == "__main__":
    asyncio.run(run())


