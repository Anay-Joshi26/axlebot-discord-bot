import asyncio
import requests
import urllib.parse
from enum import Enum, auto
import aiohttp
import discord
from yt_dlp import YoutubeDL
#from pytube import YouTube, Playlist, Search
from youtubesearchpython.__future__ import Search, Playlist, Video, VideosSearch
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv, find_dotenv
from typing import List
from datetime import datetime, timedelta
import time
import re
from async_lru import alru_cache
from functools import lru_cache
from uuid import uuid1
from utils import time_string_to_seconds
from core.api.wrapper import *
from core.api.lyrics import LyricsStatus
#from music.song_request_handler import extract_title_and_artist

load_dotenv(find_dotenv())


client_id = os.getenv("SPOTIFY_CLIENT_ID") 
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")  

# Create an instance of the Spotipy client
client_credentials_manager = SpotifyClientCredentials(
    client_id=client_id, client_secret=client_secret
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

# yt_dl_options = {
#     "format": "bestaudio/best",
#     "postprocessors": [
#         {
#             "key": "FFmpegExtractAudio",
#             "preferredcodec": "mp4",
#             "preferredquality": "320",
#         }
#     ],
#     "extractaudio": True,
#     "audioformat": "mp4",
#     "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
#     "restrictfilenames": True,
#     "noplaylist": False,
#     "nocheckcertificate": True,
#     "ignoreerrors": False,
#     "logtostderr": False,
#     "quiet": True,
#     "no_warnings": True,
#     "default_search": "auto",
#     "source_address": "0.0.0.0",
# }
# yt_dl = YoutubeDL(yt_dl_options)
# ffmpeg_options = {
#     "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
#     "options": "-vn", 
# }

PROXY = "" if os.getenv("PROXY") == "None" else os.getenv("PROXY")

yt_dl_options = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
    # Add these critical headers:
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://www.youtube.com/",
        "Origin": "https://www.youtube.com",
        "DNT": "1"
    }
}

ffmpeg_options = {
    "before_options": (
        "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 "
    ),
    "options": "-vn -headers 'Referer: https://www.youtube.com/\r\nOrigin: https://www.youtube.com\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'"
}

yt_dl = YoutubeDL(yt_dl_options)


class Song:
    def __init__(self, duration, artist, yt_url, player, name, thumbnail_url, audio_url, song_type = None, 
                 is_spot=False, is_yt=True, is_playlist = False, belongs_to = None, all_untried_song_streams: List[str] = None):
        self.yt_url = yt_url
        self.name = name
        self.artist = artist
        self._player = player

        if (is_spot and is_yt) or (not is_spot and not is_yt):
            raise ValueError("Song can either be Spotify OR YouTube (exclusive), not both.")
        if song_type is not None:
            self.type = song_type
        else:
            if is_yt:
                self.type = "yt"
            elif is_spot:
                self.type = "spot"
            else:
                self.type = "yt" 
        self.thumbnail_url = thumbnail_url if thumbnail_url else "https://images-wixmp-ed30a86b8c4ca887773594c2.wixmp.com/f/eb777e7a-7d3c-487e-865a-fc83920564a1/d7kpm65-437b2b46-06cd-4a86-9041-cc8c3737c6f0.jpg/v1/fill/w_800,h_800,q_75,strp/no_album_art__no_cover___placeholder_picture_by_cmdrobot_d7kpm65-fullview.jpg?token=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1cm46YXBwOjdlMGQxODg5ODIyNjQzNzNhNWYwZDQxNWVhMGQyNmUwIiwiaXNzIjoidXJuOmFwcDo3ZTBkMTg4OTgyMjY0MzczYTVmMGQ0MTVlYTBkMjZlMCIsIm9iaiI6W1t7ImhlaWdodCI6Ijw9ODAwIiwicGF0aCI6IlwvZlwvZWI3NzdlN2EtN2QzYy00ODdlLTg2NWEtZmM4MzkyMDU2NGExXC9kN2twbTY1LTQzN2IyYjQ2LTA2Y2QtNGE4Ni05MDQxLWNjOGMzNzM3YzZmMC5qcGciLCJ3aWR0aCI6Ijw9ODAwIn1dXSwiYXVkIjpbInVybjpzZXJ2aWNlOmltYWdlLm9wZXJhdGlvbnMiXX0.8yjX5CrFjxVH06LB59TpJLu6doZb0wz8fGQq4tM64mg"
        self.duration = duration
        self._audio_url = audio_url
        self.lyrics = None
        self._lyrics_status = LyricsStatus.NOT_STARTED
        self.progress_message : discord.Message = None
        self.seconds_played = 0
        self._play_task = None
        self.is_playlist = is_playlist
        self.song_colour = None # probably for spotify
        self.belongs_to = belongs_to # belonging to a playlist
        self.is_looping = False
        self.is_first_in_queue = False  # Indicates if the song is currently active in the queue
        self.all_untried_song_streams = [] if all_untried_song_streams is None else all_untried_song_streams # list of all song urls incase a url is invalid, we can try the next one

    @property
    async def player(self) -> discord.FFmpegPCMAudio:
        audio_url = await self.audio_url
        if audio_url is None:
            return None
        return discord.FFmpegOpusAudio(audio_url, **ffmpeg_options)  
    
    @property
    async def audio_url(self) -> str | None:
        if self._audio_url is None:
            self._audio_url = await Song.get_audio_url(self.yt_url)
        elif Song.has_audio_url_expired(self._audio_url, self.duration):
            self._audio_url = await Song.get_audio_url(self.yt_url)

        if PROXY:
            self._audio_url = PROXY + urllib.parse.quote(self._audio_url)

        print(f"Audio URL for {self.name} ({self.artist}): {self._audio_url[:50]}...")
        if not await Song.is_url_valid(self._audio_url):
            while self.all_untried_song_streams:
                next_url = self.all_untried_song_streams.pop(0)
                next_url = PROXY + urllib.parse.quote(next_url) if PROXY else next_url
                print(f"Trying next audio URL...")
                if not Song.has_audio_url_expired(next_url, self.duration) and await Song.is_url_valid(next_url):
                    self._audio_url = next_url
                    print(f"Valid audio URL found: {self._audio_url[:50]}...")
                    return self._audio_url
            return None

        return self._audio_url
    
    @property
    def is_playing(self) -> bool:
        """
        Returns True if the song is currently playing, False otherwise.
        """
        return not(self._play_task is None)

    @classmethod
    async def CreateSong_old(cls, youtube_query):
        print("searching song")
        yt_url, name, duration = await Song.search_youtube_video(youtube_query)
        print("song search finished, got url, getting info")
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(
            None, lambda: yt_dl.extract_info(yt_url, download=False)
        )
        print("got info")
        artist = data.get("artist") or data.get("uploader") or "Unknown Artist"
        thumbnail_url = data["thumbnail"]
        audio_url = data["url"]
        player = None
        print("SONG CREATED")
        # Create the song instance
        song = cls(duration, artist, yt_url, player, name, thumbnail_url, audio_url)
        
        # Start fetching lyrics concurrently
        

        return song
    
    @classmethod
    async def CreateSong(cls, youtube_query):
        print("searching song")
        #yt_url, name, duration = await Song.search_youtube_video(youtube_query)
        #print("song search finished, got url, getting info")
        data = await Song.get_youtube_video_info(youtube_query)
        if data is None:
            print(f"Failed to fetch song info for query: {youtube_query}")
            return None
        artist = data.get("artist") or data.get("uploader") or data.get("channel") or "Unknown Artist"
        thumbnail_url = data["thumbnail"]
        audio_url = data["url"]
        duration = data["duration"]
        yt_url = data["webpage_url"]
        name = data["title"]
        player = None
        print("SONG CREATED")
        # Create the song instance
        song = cls(duration, artist, yt_url, player, name, thumbnail_url, audio_url, all_untried_song_streams=data.get("audio_urls")[1:])
        return song
    
    @lru_cache(maxsize=64)
    def _cached_spotify_track(url: str):
        return sp.track(url)
    
    @classmethod
    async def SongFromSpotifyURL(cls, spotify_track_url):
        track_info = cls._cached_spotify_track(spotify_track_url)
        if track_info is None:
            print(f"Failed to fetch track info for URL: {spotify_track_url}")
            return None
        name, artist, thumbnail_url = (
            track_info["name"],
            track_info["artists"][0]["name"],
            track_info["album"]["images"][0]["url"]
            or track_info["artist"]["images"][0]["url"],
        )
        song = await cls.SpotifySong(name, artist, thumbnail_url)

        return song

    @classmethod
    async def SpotifyPlaylistSongList(cls, spotify_playlist_url, max_concurrent_song_loadings: int = 5):
        all_tracks_info = await cls.get_spotify_info(spotify_playlist_url)

        semaphore = asyncio.Semaphore(max_concurrent_song_loadings)

        unique_playlist_id = uuid1().int>>64

        async def process_track(track) -> Song:
            async with semaphore:
                try:
                    song = await Song.SpotifySong(track[0], track[1], track[2])
                    if song:
                        song.is_playlist = True
                        song.belongs_to = unique_playlist_id

                    await asyncio.sleep(0.1)

                    return song
                except Exception as e:
                    print(f"Error processing URL {track}: {e}")
                    return None
                
        tasks = [process_track(track) for track in all_tracks_info]

        for next_loaded_song in asyncio.as_completed(tasks):
            song = await next_loaded_song
            if song:
                yield song

    @staticmethod
    def has_audio_url_expired(audio_url, duration) -> bool:
        # Try query param first
        parsed = urllib.parse.urlparse(audio_url)
        query_params = urllib.parse.parse_qs(parsed.query)
        expire_value = query_params.get('expire', [None])[0]

        if expire_value is None:
            # Try to extract from path: e.g., /expire/1750009524/
            match = re.search(r'/expire/(\d{10})', parsed.path)
            if match:
                expire_value = match.group(1)

        if expire_value is None:
            # If still not found, assume expired for safety
            print("AUDIO URL EXPIRED (no expire param)")
            return True

        try:
            if time.time() + duration + 3 * 60 * 60 > float(expire_value):
                print("AUDIO URL EXPIRED")
                return True
        except ValueError:
            print("AUDIO URL EXPIRED (invalid expire value)")
            return True

        return False
    
    @classmethod
    async def SpotifySong(cls, name, artist, thumbnail_url):
        song: Song = await cls.CreateSong(f"{name} by {artist} audio")
        song.thumbnail_url = thumbnail_url
        return song
        # yt_url, _ , duration = await Song.search_youtube_video(f"{name} by {artist} audio")
        # loop = asyncio.get_running_loop()
        # data = await loop.run_in_executor(
        #     None, lambda: yt_dl.extract_info(yt_url, download=False)
        # )
        # audio_url = data["url"]
        # player = None
        # song = cls(duration, artist, yt_url, player, name, thumbnail_url, audio_url, is_spot = True, is_yt = False)
        # return song
    
    async def copy(self):
        return Song(self.duration, self.artist, self.yt_url, await self.player, self.name, self.thumbnail_url, await self.audio_url, song_type=self.type, is_playlist = self.is_playlist)
    
    @classmethod
    async def SongFromYouTubeURL(cls, yt_url):
        # name, duration = await Song.search_youtube_video_by_url(yt_url)
        # if name is None or duration is None:
        #     print(f"Failed to fetch song info for URL: {yt_url}")
        #     return None
        # loop = asyncio.get_running_loop()
        # data = await loop.run_in_executor(
        #     None, lambda: yt_dl.extract_info(yt_url, download=False)
        # )
        # artist = data.get("artist") or data.get("uploader") or "Unknown Artist"
        # thumbnail_url = data["thumbnail"]
        # audio_url = data["url"]
        # player = None
        # song = cls(duration, artist, yt_url, player, name, thumbnail_url, audio_url)
        # return song
        data = await Song.get_youtube_video_info(yt_url, is_yt_url=True)

        if data is None:
            print(f"Failed to fetch song info for query: {yt_url}")
            return None
        artist = data.get("artist") or data.get("uploader") or data.get("channel") or "Unknown Artist"
        thumbnail_url = data["thumbnail"]
        audio_url = data["url"]
        duration = data["duration"]
        yt_url = data["webpage_url"]
        name = data["title"]
        player = None
        print("SONG CREATED")
        # Create the song instance
        song = cls(duration, artist, yt_url, player, name, thumbnail_url, audio_url, all_untried_song_streams=data.get("audio_urls")[1:])
        return song


    def get_fresh_player(self):
        return discord.FFmpegPCMAudio(self.audio_url, **ffmpeg_options)
    
    def get_lyrics(self):
        if self._lyrics_status == LyricsStatus.FETCHED:
            return self.lyrics, LyricsStatus.FETCHED
        
        return None, self._lyrics_status
    
    async def fetch_lyrics(self, URL = None, tries = 1):

        self._lyrics_status = LyricsStatus.FETCHING
        data = await get_lyrics(self.name, self.artist)
        self._lyrics_status = LyricsStatus[data['status']]
        self.lyrics = data.get('lyrics', None)
        return data['lyrics']

        # words_to_ignore = ["(offical video)", "(offical audio)", "(lyrics)", "(offical music video)", "[official music video]", "official", "audio", "video", "lyrics", "music video", \
        #                    "(video)", "(audio)", "(lyric video)", "(lyric)", "(music video)", "(official lyric video)", "(official lyric)", "()", "~", "( )", "( Music )", \
        #                     "visualiser", "visualizer", "(visualiser)", "(visualizer)", "[]", "[ ]", f"{self.artist}", " - ", "ft.", "feat.", "-", "- ", " -"]
        # name_to_use = self.name

        # for word in words_to_ignore*2: # to make sure we remove all instances we do it twice
        #     name_to_use = re.sub(re.escape(word), "", name_to_use, flags=re.IGNORECASE).strip()
        #     if "ft." in name_to_use:
        #         name_to_use = name_to_use[:name_to_use.index("ft.")]
        #     elif "feat." in name_to_use:
        #         name_to_use = name_to_use[:name_to_use.index("feat.")]

        # #extract_title_and_artist
        

        # print(f"Fetching lyrics for {name_to_use} by {self.artist}")
        
        # if URL is None:
        #     URL = f"https://api.lyrics.ovh/v1/{urllib.parse.quote(self.artist)}/{urllib.parse.quote(name_to_use)}"
            

        # self._lyrics_status = LyricsStatus.FETCHING
        # self.lyrics = None

        # try:
        #     async with aiohttp.ClientSession() as session:
        #         async with session.get(URL) as response:
        #             content_type = response.headers.get("Content-Type", "")

        #             if response.status == 200:
        #                 # Expected: valid lyrics data
        #                 data = await response.json()
        #                 res_lyrics = data.get('lyrics')
        #                 if res_lyrics:
        #                     self.lyrics = res_lyrics.replace('\n\n', '\n')
        #                     self._lyrics_status = LyricsStatus.FETCHED
        #                 else:
        #                     self._lyrics_status = LyricsStatus.NO_LYRICS_FOUND

        #             elif response.status == 404 and "application/json" in content_type:
        #                 # 404 but still a valid JSON with an error message
        #                 data = await response.json()
        #                 if data.get("error") == "No lyrics found":
        #                     self._lyrics_status = LyricsStatus.NO_LYRICS_FOUND
        #                 else:
        #                     self._lyrics_status = LyricsStatus.ERROR

        #             else:
        #                 # Unexpected response or non-JSON 404
        #                 self._lyrics_status = LyricsStatus.ERROR

        #             print(f"Lyrics status for {name_to_use} by {self.artist}: {self._lyrics_status.name}")

        # except Exception as e:
        #     print("Error fetching lyrics:", e)
        #     self._lyrics_status = LyricsStatus.ERROR
        #     self.lyrics = None

            # if self.artist and tries == 1:
            #     await self.fetch_lyrics(
            #         f"https://lyrist.vercel.app/api/{urllib.parse.quote(name_to_use)}", tries + 1
            #     )


        

    @classmethod
    async def YouTubePlaylistSongList(cls, yt_playlist_link, max_concurrent_song_loadings: int = 5):
        yt_playlist_urls = await Song.get_youtube_playlist_info(yt_playlist_link)

        semaphore = asyncio.Semaphore(max_concurrent_song_loadings)

        async def process_url(url):
            async with semaphore:
                try:
                    song = await Song.SongFromYouTubeURL(url)
                    if song:
                        song.is_playlist = True
                    await asyncio.sleep(0.1)
                    return song
                except Exception as e:
                    print(f"Error processing URL {url}: {e}")
                    return None

        tasks = [process_url(url) for url in yt_playlist_urls]

        for next_loaded_song in asyncio.as_completed(tasks):
            song = await next_loaded_song
            if song:
                yield song
    @classmethod
    @alru_cache(maxsize=64, ttl=86400)
    async def get_spotify_info(cls, spotify_url):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, cls.sync_get_spotify_info, spotify_url)

    @staticmethod
    @lru_cache(maxsize=64)
    def sync_get_spotify_info(query):
        list_type = None
        if "open.spotify.com/album/" in query:
            list_type = "album"
        elif "open.spotify.com/playlist/" in query:
            list_type = "playlist"
        else:
            raise ValueError("Invalid Spotify URL. Must be an album or playlist.")

        if list_type == 'playlist':
            playlist_tracks = []
            limit = 100
            offset = 0

            while True:
                try:
                    results = sp.playlist_tracks(query, limit=limit, offset=offset)
                except spotipy.exceptions.SpotifyException as e:
                    raise ValueError("Invalid Spotify URL. Must be a valid album or playlist.")
                items = results["items"]
                print(limit, offset, len(items))
                playlist_tracks.extend(items)
                if len(items) < limit:
                    break
                offset += limit

            print(f"Total tracks fetched: {len(playlist_tracks)}")
            track_info = []

            for track in playlist_tracks:
                track_data = track.get("track", {})
                name = track_data.get("name")

                if not name:
                    continue  # Skip if track name is None or missing

                artists = track_data.get("artists", [])
                artist_name = artists[0]["name"] if artists else "Artist Unknown"

                album = track_data.get("album", {})
                album_images = album.get("images", [])
                if album_images:
                    image_url = album_images[0].get("url")
                else:
                    artist_images = track_data.get("artist", {}).get("images", [])
                    image_url = artist_images[0].get("url") if artist_images else None

                track_info.append((name, artist_name, image_url))


            print(f"Total track info fetched: {len(track_info)}")
            return track_info
        elif list_type == 'album':
            try:
                album = sp.album(query)
            except spotipy.exceptions.SpotifyException as e:
                raise ValueError("Invalid Spotify URL. Must be a valid album or playlist.")
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
    
    @staticmethod
    async def get_youtube_playlist_info(playlist_url: str) -> list:
        playlist = Playlist(playlist_url)
        
        while playlist.hasMoreVideos:
            await playlist.getNextVideos()
        
        return [f"https://www.youtube.com/watch?v={video['id']}" for video in playlist.videos]
    
    @staticmethod
    #@alru_cache(maxsize=128, ttl=86400)
    async def get_youtube_video_info(query: str, is_yt_url = False) -> dict:
        # loop = asyncio.get_running_loop()
        # data = await loop.run_in_executor(
        #     None, lambda: yt_dl.extract_info(f"{query if is_yt_url else f'ytsearch1{query}'}", download=False)
        # )
        # if not data or "entries" not in data or len(data["entries"]) == 0:
        #     print(f"No results found for query: {query}")
        #     return None
        # data = data["entries"][0]
        # return data
        data = await get_youtube_info(query, is_yt_url=is_yt_url)
        return data


    
    @staticmethod
    @alru_cache(maxsize=128, ttl=86400)
    async def search_youtube_video(query: str):
        videos_search = VideosSearch(query, limit=1)
        results = await videos_search.next()
        
        if results['result']:
            first_result = results['result'][0]
            video_url = first_result['link']
            video_title = first_result['title']

            if 'secondsText' in first_result['duration']:
                video_length = int(first_result['duration']['secondsText'])
            else:
                video_length = time_string_to_seconds(first_result['duration'])
            
            return video_url, video_title, video_length
        
        return None, None, None
    
    @staticmethod
    @alru_cache(maxsize=128, ttl=86400)
    async def search_youtube_video_by_url(url):
        try:
            video = await Video.getInfo(url)
        except TypeError as _:
            print(f"Error fetching video info for URL {url}")
            return None, None
        
        title = video['title']

        if 'secondsText' in video['duration']:
            video_length = int(video['duration']['secondsText'])
        else:
            video_length = time_string_to_seconds(video['duration'])

        return title, video_length
    
    async def _increment_seconds(self):
        """Private method to increment seconds in the background."""

        while self.seconds_played <= self.duration:
            await asyncio.sleep(1)  # Wait for 1 second
            self.seconds_played += 1
    
    def play(self):
        if self._play_task is not None:
            return

        asyncio.create_task(self.fetch_lyrics())
        self._play_task = asyncio.create_task(self._increment_seconds())

    def stop(self):
        if self._play_task is not None:
            self._play_task.cancel()
            self._play_task = None

    @staticmethod
    async def get_audio_url(yt_url: str) -> str:
        print("GETTING NEW URL")
        try:
            # loop = asyncio.get_running_loop()
            # data = await loop.run_in_executor(
            #     None, lambda: yt_dl.extract_info(yt_url, download=False)
            # )
            # #data = yt_dl.extract_info(yt_url, download=False)
            # audio_url = data["url"]
            audio_urls = await get_youtube_audio_url(yt_url)
            print("GOT len(audio_urls)", len(audio_urls))
            if not audio_urls or len(audio_urls) == 0:
                print(f"No audio URLs found for YouTube URL: {yt_url}")
                return None
            audio_url = audio_urls[0]

        except Exception as e:
            print(e)
            audio_url = None
        print("NEW URL")
        print(audio_url[:50], "...")
        return audio_url

    @staticmethod
    async def is_url_valid(url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url) as resp:
                    print(f"URL check returned status {resp.status}")
                    return resp.status == 200
        except Exception as e:
            print(f"URL check failed with exception: {e}")
            return False
    
    async def refresh_audio_url_and_player(self):
        self.audio_url = await self.get_audio_url(self.yt_url)
        self.player = self.get_fresh_player()

    def to_dict(self):
        return {
            "yt_url": self.yt_url,
            "name": self.name,
            "artist": self.artist,
            "duration": self.duration,
            "thumbnail_url": self.thumbnail_url,
            "type": self.type,
            "is_playlist": self.is_playlist
        }
    
    @staticmethod
    async def from_dict(data: dict):
        try:
            return Song(
                data["duration"],
                data["artist"],
                data["yt_url"],
                None,
                data["name"],
                data["thumbnail_url"],
                None,
                song_type=data["type"],
                is_playlist = data["is_playlist"]
            )
        except Exception as e:
            print(e)
            return None




