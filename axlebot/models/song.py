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

load_dotenv(find_dotenv())


client_id = os.getenv("SPOTIFY_CLIENT_ID") 
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")  

# Create an instance of the Spotipy client
client_credentials_manager = SpotifyClientCredentials(
    client_id=client_id, client_secret=client_secret
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

yt_dl_options = {
    "format": "bestaudio/best",
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp4",
            "preferredquality": "320",
        }
    ],
    "extractaudio": True,
    "audioformat": "mp4",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": False,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
}
yt_dl = YoutubeDL(yt_dl_options)
ffmpeg_options = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -bufsize 2000k -probesize 100M -b:a 128k", 
}

class LyricsStatus(Enum):
    NOT_STARTED = auto()
    FETCHING = auto()
    FETCHED = auto()
    NO_LYRICS_FOUND = auto()
    ERROR = auto()


class Song:
    def __init__(self, duration, artist, yt_url, player, name, thumbnail_url, audio_url, song_type = None, is_spot=False, is_yt=True, is_playlist = False):
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
        self.thumbnail_url = thumbnail_url
        self.duration = duration
        self._audio_url = audio_url
        self.lyrics = None
        self._lyrics_status = LyricsStatus.NOT_STARTED
        self.progress_message : discord.Message = None
        self.seconds_played = 0
        self._play_task = None
        self.is_playlist = is_playlist
        self.song_colour = None # probably for spotify

    @property
    async def player(self) -> discord.FFmpegPCMAudio:
        audio_url = await self.audio_url
        return discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)  
    
    @property
    async def audio_url(self) -> str:
        if self._audio_url is None:
            self._audio_url = await Song.get_audio_url(self.yt_url)
            return self._audio_url
        elif Song.has_audio_url_expired(self._audio_url, self.duration):
            self._audio_url = await Song.get_audio_url(self.yt_url)
            return self._audio_url

        return self._audio_url

    def _time_string_to_seconds(time_str: str) -> int:
        # Try parsing the time string in either MM:SS or HH:MM:SS format
        if len(time_str.split(":")) == 2:  # MM:SS format
            time_obj = datetime.strptime(time_str, "%M:%S")
            return time_obj.minute * 60 + time_obj.second
        elif len(time_str.split(":")) == 3:  # HH:MM:SS format
            time_obj = datetime.strptime(time_str, "%H:%M:%S")
            return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
        else:
            raise ValueError("Time format not recognized. Use MM:SS or HH:MM:SS")

    @classmethod
    async def CreateSong(cls, youtube_query):
        yt_url, name, duration = await Song.search_youtube_video(youtube_query)
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: yt_dl.extract_info(yt_url, download=False)
        )
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
    async def SongFromSpotifyURL(cls, spotify_track_url):
        track_info = sp.track(spotify_track_url)
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
        all_tracks_info = cls.get_spotify_info(spotify_playlist_url)

        semaphore = asyncio.Semaphore(max_concurrent_song_loadings)

        async def process_track(track) -> Song:
            async with semaphore:
                try:
                    song = await Song.SpotifySong(track[0], track[1], track[2])
                    if song:
                        song.is_playlist = True

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
        expire_value = urllib.parse.parse_qs(urllib.parse.urlparse(audio_url).query).get('expire', [None])[0]
        if expire_value is None or time.time() + duration + 60 > float(expire_value):
            print("AUDIO URL EXPIRED")
            return True

        return False
    
    @classmethod
    async def SpotifySong(cls, name, artist, thumbnail_url):
        yt_url, _ , duration = await Song.search_youtube_video(f"{name} by {artist} audio")
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: yt_dl.extract_info(yt_url, download=False)
        )
        audio_url = data["url"]
        player = None
        song = cls(duration, artist, yt_url, player, name, thumbnail_url, audio_url, is_spot = True, is_yt = False)
        return song
    
    async def copy(self):
        return Song(self.duration, self.artist, self.yt_url, await self.player, self.name, self.thumbnail_url, await self.audio_url, song_type=self.type, is_playlist = self.is_playlist)
    
    @classmethod
    async def SongFromYouTubeURL(cls, yt_url):
        name, duration = await Song.search_youtube_video_by_url(yt_url)
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: yt_dl.extract_info(yt_url, download=False)
        )
        artist = data.get("artist") or data.get("uploader") or "Unknown Artist"
        thumbnail_url = data["thumbnail"]
        audio_url = data["url"]
        player = None
        song = cls(duration, artist, yt_url, player, name, thumbnail_url, audio_url)
        return song

    def get_fresh_player(self):
        return discord.FFmpegPCMAudio(self.audio_url, **ffmpeg_options)
    
    def get_lyrics(self):
        if self._lyrics_status == LyricsStatus.FETCHED:
            return self.lyrics, LyricsStatus.FETCHED
        
        return None, self._lyrics_status
    
    async def fetch_lyrics(self, URL = None, tries = 1):

        words_to_ignore = ["(offical video)", "(offical audio)", "(lyrics)", "(offical music video)", "official", "audio", "video", "lyrics", "music video", \
                           "(video)", "(audio)", "(lyric video)", "(lyric)", "(music video)", "(official lyric video)", "(official lyric)", "()", "~", "( )", "( Music )", \
                            "visualiser", "visualizer", "[]", "[ ]"]
        name_to_use = self.name

        for word in words_to_ignore:
            name_to_use = re.sub(re.escape(word), "", name_to_use, flags=re.IGNORECASE)
        

        print(f"Fetching lyrics for {name_to_use} by {self.artist}")
        
        if URL is None:
            URL = (
                f"https://lyrist.vercel.app/api/{urllib.parse.quote(name_to_use)}/{urllib.parse.quote(self.artist)}"
                if self.artist
                else f"https://lyrist.vercel.app/api/{urllib.parse.quote(name_to_use)}"
            )

        self._lyrics_status = LyricsStatus.FETCHING
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(URL) as response:
                    response.raise_for_status()
                    data = await response.json()
                    res_lyrics = data.get('lyrics', None)
                    if res_lyrics is None:
                        self.lyrics = None
                        self._lyrics_status = LyricsStatus.NO_LYRICS_FOUND
                        if self.artist and tries == 1:
                            await self.fetch_lyrics(
                                f"https://lyrist.vercel.app/api/{urllib.parse.quote(name_to_use)}", tries + 1
                            )
                    else:
                        self.lyrics = res_lyrics
                        self._lyrics_status = LyricsStatus.FETCHED
        except Exception as e:
            print("Error fetching lyrics", e)
            self.lyrics = None
            self._lyrics_status = LyricsStatus.ERROR
            if self.artist and tries == 1:
                await self.fetch_lyrics(
                    f"https://lyrist.vercel.app/api/{urllib.parse.quote(name_to_use)}", tries + 1
                )


        

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

    @staticmethod
    def get_spotify_info(query):
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
        return track_info
    
    @staticmethod
    async def get_youtube_playlist_info(playlist_url: str) -> list:
        playlist = Playlist(playlist_url)
        
        while playlist.hasMoreVideos:
            await playlist.getNextVideos()
        
        return [f"https://www.youtube.com/watch?v={video['id']}" for video in playlist.videos]
    
    @staticmethod
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
                video_length = Song._time_string_to_seconds(first_result['duration'])
            
            return video_url, video_title, video_length
        
        return None, None, None
    
    @staticmethod
    async def search_youtube_video_by_url(url):
        video = await Video.getInfo(url)
        title = video['title']

        if 'secondsText' in video['duration']:
            video_length = int(video['duration']['secondsText'])
        else:
            video_length = Song._time_string_to_seconds(video['duration'])

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
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, lambda: yt_dl.extract_info(yt_url, download=False)
            )
            #data = yt_dl.extract_info(yt_url, download=False)
            audio_url = data["url"]
        except Exception as e:
            print(e)
            audio_url = None
        print("NEW URL")
        return audio_url
    
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




