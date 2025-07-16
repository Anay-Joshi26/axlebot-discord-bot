import asyncio
import requests
import urllib.parse
import aiohttp
import discord
from PIL import Image
import io
from yt_dlp import YoutubeDL
#from pytube import YouTube, Playlist, Search
from youtubesearchpython.__future__ import Search, Playlist, Video, VideosSearch
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import os
from dotenv import load_dotenv, find_dotenv
from typing import List
import time
import re
from async_lru import alru_cache
from functools import lru_cache
from uuid import uuid1
from utils import time_string_to_seconds, generate_random_string, clean_song_name
#from utils.message_crafter import extract_embed_color
from core.api.wrapper import *
from core.api.lyrics import LyricsStatus
import lavalink
import core.extensions
#from music.song_request_handler import extract_title_and_artist

load_dotenv(find_dotenv())


client_id = os.getenv("SPOTIFY_CLIENT_ID") 
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")  

# Create an instance of the Spotipy client
client_credentials_manager = SpotifyClientCredentials(
    client_id=client_id, client_secret=client_secret
)

sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

sp_oauth = SpotifyOAuth(
    client_id = os.getenv("REC_SPOTIFY_CLIENT_ID"),
    client_secret = os.getenv("REC_SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("REC_SPOTIFY_REDIRECT_URI"),
    scope=None,
    cache_path=os.getenv("REC_CACHE_PATH"),
    state = generate_random_string()
)


sp_rec = spotipy.Spotify(auth_manager=sp_oauth)

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
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5" ,
    "options": "-vn -headers 'Referer: https://www.youtube.com/\r\nOrigin: https://www.youtube.com\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'"
}

yt_dl = YoutubeDL(yt_dl_options)


class Song:
    def __init__(self, duration, artist, yt_url, player, name, thumbnail_url, audio_url, song_type = None, 
                 is_spot=False, is_yt=True, is_playlist = False, belongs_to = None, all_untried_song_streams: List[str] = None,
                 lavalink_track_id: str = None, auto_play = False, lyrics: str = None):
        self.yt_url = yt_url # could be soundcloud or youtube url
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
        self.lyrics = lyrics
        self._lyrics_status = LyricsStatus.NOT_STARTED
        self.progress_message : discord.Message = None
        self.seconds_played = 0
        self._play_task = None
        self.is_playlist = is_playlist
        self.song_colour = None # probably for spotify
        self.belongs_to = belongs_to # belonging to a playlist
        self.is_looping = False
        self.is_first_in_queue = False  # Indicates if the song is currently active in the queue
        self.all_untried_song_streams = all_untried_song_streams # list of all song urls incase a url is invalid, we can try the next one
        self.lavalink_track_id = lavalink_track_id 
        self.auto_play = auto_play  # Indicates if this song was added automatically (e.g., from a recommendation or autoplay feature)
        self.increment_seconds_time_delay = 1 # seconds
        self._embed_color_future = None
        self._start_color_fetch()
        #self.track = lavalink_track  # For Lavalink 4.x, this is the track object

    @staticmethod
    async def get_dominant_colour(thumbnail_url: str = None) -> discord.Color:
        if thumbnail_url is None:
            return discord.Color.default()

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

        average_color = cropped_image.resize((1, 1)).getpixel((0, 0))

        hex_color = (average_color[0] << 16) + (average_color[1] << 8) + average_color[2]

        return hex_color

    def _start_color_fetch(self):
        # Start background color fetch as soon as the song is created
        if self.thumbnail_url:
            self._embed_color_future = asyncio.create_task(
                Song.get_dominant_colour(self.thumbnail_url)
            )

    async def get_embed_color(self):
        if self._embed_color_future:
            return await self._embed_color_future
        return discord.Color.default()

    @property
    async def player(self) -> lavalink.AudioTrack | None:
        """
        Returns the player for the song, fetching it if not already set.
        """
        if self._player is None:

            if self.lavalink_track_id:
                return await core.extensions.lavalink_client.decode_track(self.lavalink_track_id)

            if self.yt_url:
                search_query = self.yt_url
                # Check if it's a YouTube or SoundCloud URL
                if "youtube.com" in search_query or "youtu.be" in search_query:
                    is_yt = True
                    is_sc = False
                elif "soundcloud.com" in search_query:
                    is_yt = False
                    is_sc = True
                else:
                    is_yt = False
                    is_sc = False
            else:
                search_query = self.name
                is_yt = False
                is_sc = False

            if search_query is None:
                print("No search query provided for song player retrieval.")
                return None
            
            if is_yt:
                # YouTube URL, try YouTube search first
                search_result = await core.extensions.lavalink_client.get_tracks(f"ytsearch:{search_query}")
                if not search_result or not search_result['tracks']:
                    print(f"Failed to fetch song info for YouTube search query: {search_query}, trying SoundCloud search")
                    # Fall back to SoundCloud search using song name
                    search_result = await core.extensions.lavalink_client.get_tracks(f"scsearch:{self.name}")

            elif is_sc:
                # SoundCloud URL, try SoundCloud search first
                search_result = await core.extensions.lavalink_client.get_tracks(f"scsearch:{search_query}")
                if not search_result or not search_result['tracks']:
                    print(f"Failed to fetch song info for SoundCloud search query: {search_query}, trying YouTube search")
                    # Fall back to YouTube search using song name
                    search_result = await core.extensions.lavalink_client.get_tracks(f"ytsearch:{self.name}")

            else:
                # No URL, just search by name (default behavior)
                search_result = await core.extensions.lavalink_client.get_tracks(f"ytsearch:{search_query}")
                if not search_result or not search_result['tracks']:
                    print(f"Failed to fetch song info for search query: {search_query}, trying SoundCloud search")
                    # Fall back to SoundCloud search using song name
                    search_result = await core.extensions.lavalink_client.get_tracks(f"scsearch:{self.name}")

            if not search_result or not search_result['tracks']:
                print(f"Failed to fetch song info for query: {search_query}")
                return None

            # Use the first track
            track = search_result['tracks'][0]
            self._player = track
            self.duration = int(track.duration / 1000)  # Convert milliseconds to seconds
            return track

        return self._player

    
    # async def get_player(self) -> lavalink.AudioTrack | None:
    #     """
    #     Returns the player for the song, fetching it if not already set.
    #     """
    #     if self._player is None:

    #         search_result = await core.extensions.lavalink_client.get_tracks(f"scsearch:{self.name}")

    #         if not search_result or not search_result['tracks']:
    #             print(f"Failed to fetch song info for query: {self.name}")
    #             return None

    #         # Use the first track
    #         track = search_result['tracks'][0]
    #         self._player = track
    #         return track
    #     return self._player
    
    # @property
    # async def audio_url(self) -> str | None:
    #     if self._audio_url is None:
    #         all_streams = await Song.get_audio_url(self.yt_url, return_all = True)
    #         if len(all_streams) > 0:
    #             self._audio_url, *self.all_untried_song_streams = all_streams
    #         else:
    #             return None
    #     elif Song.has_audio_url_expired(self._audio_url, self.duration):
    #         all_streams = await Song.get_audio_url(self.yt_url, return_all = True)
    #         if len(all_streams) > 0:
    #             self._audio_url, *self.all_untried_song_streams = all_streams
    #         else:
    #             return None  

    #     if PROXY:
    #         self._audio_url = PROXY + urllib.parse.quote(self._audio_url)

    #     print(f"Audio URL for {self.name} ({self.artist}): {self._audio_url[:50]}...")
    #     if not await Song.is_url_valid(self._audio_url):
    #         print("other audio urls len", len(self.all_untried_song_streams))
    #         while self.all_untried_song_streams:
    #             next_url = self.all_untried_song_streams.pop(0)
    #             next_url = PROXY + urllib.parse.quote(next_url) if PROXY else next_url
    #             print(f"Trying next audio URL...")
    #             if not Song.has_audio_url_expired(next_url, self.duration) and await Song.is_url_valid(next_url):
    #                 self._audio_url = next_url
    #                 print(f"Valid audio URL found: {self._audio_url[:50]}...")
    #                 return self._audio_url
    #         return None

    #     return self._audio_url
    
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
    async def CreateSong_old_new(cls, youtube_query):
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
    
    @classmethod
    async def CreateSong(cls, query: str):
        print(f"Searching song... query = {query}")

        # Search via Lavalink node
        #search_result = await player.node.get_tracks(f"scsearch:{query}")
        search_result = await core.extensions.lavalink_client.get_tracks(f"ytsearch:{query}")

        if not search_result or not search_result['tracks']:
            print(f"Failed to fetch song info for query: {query}, trying SoundCloud search")

            search_result = await core.extensions.lavalink_client.get_tracks(f"scsearch:{query}")

            if not search_result or not search_result['tracks']:
                print(f"Failed to fetch song info for query: {query} from SoundCloud as well")
                return None


        # Use the first track
        track = search_result['tracks'][0]
        info = track['info'].raw.get('info', {})

        name = info.get('title', 'Unknown Title')

        print(info['title'])
        artist = (
            info.get('author') or
            info.get('artist') or
            info.get('uploader') or
            info.get('channel') or
            "Unknown Artist"
        )
        duration = int(info.get('length', 0)/1000)
        yt_url = info.get('uri') or info.get('url')  # For Lavalink 4.x, 'uri' is standard
        thumbnail_url = info.get('artworkUrl')

        print("SONG CREATED")

        return cls(
            duration=duration,
            artist=artist,
            yt_url=yt_url,
            player=track,
            name=name,
            thumbnail_url=thumbnail_url,
            audio_url=None,
            all_untried_song_streams=None,
            lavalink_track_id=track.track
        )
    
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
        print(f"Creating Spotify song: {name} by {artist}")
        song = await cls.SpotifySong(name, artist, thumbnail_url)

        return song

    @classmethod
    async def SpotifyPlaylistSongList(cls, spotify_playlist_url, max_concurrent_song_loadings: int = 5, stop_event=None):
        all_tracks_info = await cls.get_spotify_info(spotify_playlist_url)

        BATCH_SIZE = max_concurrent_song_loadings
        RATE = 3
        DELAY_PER_BATCH = BATCH_SIZE * RATE

        semaphore = asyncio.Semaphore(BATCH_SIZE)
        unique_playlist_id = uuid1().int >> 64

        async def process_track(track, sleep_time=0) -> Song:
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

            async with semaphore:
                try:
                    song = await Song.SpotifySong(track[0], track[1], track[2])
                    if song:
                        song.is_playlist = True
                        song.belongs_to = unique_playlist_id
                    return song
                except Exception as e:
                    print(f"Error processing URL {track}: {e}")
                    return None

        # Create tasks with staggered start times based on batch
        tasks = [
            asyncio.create_task(
                process_track(track, sleep_time=(i // BATCH_SIZE) * DELAY_PER_BATCH)
            )
            for i, track in enumerate(all_tracks_info)
        ]

        try:
            while tasks:
                done, pending = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )

                if isinstance(stop_event, asyncio.Event) and stop_event.is_set():
                    print("[GENERATOR] Stop event triggered. Cancelling all tasks.")
                    for task in pending:
                        task.cancel()
                    await asyncio.gather(*pending, return_exceptions=True)
                    break

                for finished in done:
                    try:
                        song = await finished
                        if song:
                            yield song
                    except asyncio.CancelledError:
                        print("[GENERATOR] Task was cancelled.")
                    except Exception as e:
                        print(f"[GENERATOR] Task raised error: {e}")
                    tasks.remove(finished)

        except asyncio.CancelledError:
            print("[GENERATOR] Function was externally cancelled.")
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise



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
        song.type = "spot"; song.is_spot = True; song.is_yt = False
        song.name = name ; song.artist = artist
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
        return Song(self.duration, self.artist, self.yt_url, await self.player, self.name, self.thumbnail_url, self._audio_url, song_type=self.type, is_playlist = self.is_playlist)
    
    @classmethod
    async def SongFromYouTubeURL(cls, yt_url):
        return await cls.CreateSong(yt_url)


    async def get_fresh_player(self, additional_before_options : str = None, additional_options: str = None):
        """
        Returns a fresh FFmpegPCMAudio player for the song.
        """
        new_ffmpeg_options = ffmpeg_options.copy()
        if additional_before_options:
            new_ffmpeg_options["before_options"] += f" {additional_before_options}"
        if additional_options:
            new_ffmpeg_options["options"] += f" {additional_options}"
        return discord.FFmpegOpusAudio(await self.audio_url, **new_ffmpeg_options)
    
    def get_lyrics(self):
        if self._lyrics_status == LyricsStatus.FETCHED:
            return self.lyrics, LyricsStatus.FETCHED
        
        return None, self._lyrics_status
    
    async def fetch_lyrics(self, URL = None, tries = 1):

        self._lyrics_status = LyricsStatus.FETCHING
        data = await get_lyrics(self.name, self.artist)
        if data is None:
            self._lyrics_status = LyricsStatus.NO_LYRICS_FOUND
            return None
        self._lyrics_status = LyricsStatus[data['status']]
        self.lyrics = data.get('lyrics', None)
        return data['lyrics']

    @staticmethod
    def _self_weighted_mean(values):
        return sum(x**2 for x in values) / sum(values)
    
    @staticmethod
    async def get_song_recommendations(seed_songs: list, limit = 3, set_auto_play = True,
                                       sort_by_popularity = True) -> List["Song"]:
        """
        Fetches song recommendations based on the current song.

        Args:
            seed_songs (list): A list of Song objects to use as seeds for recommendations.
            limit (int): The maximum number of recommendations to return.
            set_auto_play (bool): Whether to set the auto_play attribute for the returned songs.
            sort_by_popularity (bool): Whether to sort the recommendations by popularity (descending order).
        
        Returns:
            List[Song]: A list of recommended Song objects.
        """
        if not seed_songs:
            return []
        
        seed_tracks = []
        average_popularity = 0
        popularities = []
        for song in seed_songs:
            search_term = clean_song_name(song.name, song.artist)
            query = f'{search_term.lower()}'
            if song.type == "spot" or song.artist.lower() in song.name.lower():
                query += f' {song.artist}'
                #pass
            query = query.strip()
            #print(f"Searching for seed track: {query}")
            result = sp_rec.search(q=query, type="track", limit=1)['tracks']['items']
            #print(result)

            if result:
                track_id = result[0]['id']
                seed_tracks.append(track_id)
                print(f"SEED TRACK:  {query} -> {result[0]['name']} | {track_id}")
            else:
                print(f"No result for SF: {query}")
            average_popularity += result[0]['popularity']
            popularities.append(result[0]['popularity'])
        
        #average_popularity /= len(seed_tracks)
        #print(f"Average popularity of seed tracks: {average_popularity}")
        average_popularity = Song._self_weighted_mean(popularities)
        print(f"Self weighted popularity of seed tracks: {average_popularity}")
        if average_popularity < 45:
            average_popularity = min(80, average_popularity * 2)  # safeguard against too low popularity
        #print(f"LIMIT: {limit}")

        try:
            results = sp_rec.recommendations(seed_tracks=seed_tracks, limit=limit, min_popularity=int(max(average_popularity*0.90, 30)))
            tracks = results['tracks']#sorted(results['tracks'], key=lambda x: x['popularity'], reverse=True) if sort_by_popularity else results['tracks']
            recommendations = []
            for track in tracks[:limit]:
                name = track['name']
                print(f"Recommending track: {name} | {track['id']}")
                artist = track['artists'][0]['name']
                thumbnail_url = track['album']['images'][0]['url'] if track['album']['images'] else None
                song = await Song.SpotifySong(name, artist, thumbnail_url)
                if set_auto_play:
                    song.auto_play = True
                recommendations.append(song)
            #print(f"Total recommendations fetched: {len(recommendations)}")
            return recommendations
        except Exception as e:
            print(f"Error fetching recommendations: {e}")
            return []
        

    @classmethod
    async def YouTubePlaylistSongList(cls, yt_playlist_link, max_concurrent_song_loadings: int = 5, stop_event=None):
        yt_playlist_urls = await Song.get_youtube_playlist_info(yt_playlist_link)

        BATCH_SIZE = max_concurrent_song_loadings
        RATE = 3 # proportional to batch size, what multiplier to use for sleep time
        # e.g if BATCH_SIZE = 5 and RATE = 2, then sleep time for each batch is 10 seconds
        # so for 10 songs, it will take 20 seconds to process all of them
        # if BATCH_SIZE = 10 and RATE = 5, then sleep time for each batch is 50 seconds
        # so for 10 songs, it will take 50 seconds to process all of them
        DELAY_PER_BATCH = BATCH_SIZE * RATE

        semaphore = asyncio.Semaphore(BATCH_SIZE)

        async def process_url(url, sleep_time = 0) -> Song:
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

            async with semaphore:
                try:
                    song = await Song.SongFromYouTubeURL(url)
                    if song:
                        song.is_playlist = True

                    return song
                except Exception as e:
                    print(f"Error processing URL {url}: {e}")
                    return None

        # Create tasks with staggered start times based on batch
        tasks = [
            asyncio.create_task(
                process_url(track, sleep_time=(i // BATCH_SIZE) * DELAY_PER_BATCH)
            )
            for i, track in enumerate(yt_playlist_urls)
        ]

        try:
            while tasks:
                done, pending = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )

                if isinstance(stop_event, asyncio.Event) and stop_event.is_set():
                    print("[GENERATOR] Stop event triggered. Cancelling all tasks.")
                    for task in pending:
                        task.cancel()
                    await asyncio.gather(*pending, return_exceptions=True)
                    break

                for finished in done:
                    try:
                        song = await finished
                        if song:
                            yield song
                    except asyncio.CancelledError:
                        print("[GENERATOR] Task was cancelled.")
                    except Exception as e:
                        print(f"[GENERATOR] Task raised error: {e}")
                    tasks.remove(finished)

        except asyncio.CancelledError:
            print("[GENERATOR] Function was externally cancelled.")
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
            
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
        # playlist = Playlist(playlist_url)
        
        # while playlist.hasMoreVideos:
        #     await playlist.getNextVideos()
        
        # return [f"https://www.youtube.com/watch?v={video['id']}" for video in playlist.videos]
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'playlistend': None,  # Limit number of videos
            'skip_download': True
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            try:
                playlist_info = await asyncio.get_running_loop().run_in_executor(
                    None, lambda: ydl.extract_info(playlist_url, download=False)
                )

                return [entry['url'] for entry in playlist_info['entries'] if entry]
            except Exception as e:
                print(f"Error extracting playlist: {e}")
                return []
    
    @staticmethod
    #@alru_cache(maxsize=128, ttl=86400)
    async def get_youtube_video_info(query: str, is_yt_url = False) -> dict:
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
            await asyncio.sleep(self.increment_seconds_time_delay)
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
    async def get_audio_url(yt_url: str, return_all = False) -> str:
        print("GETTING NEW URL")
        try:
            # loop = asyncio.get_running_loop()
            # data = await loop.run_in_executor(
            #     None, lambda: yt_dl.extract_info(yt_url, download=False)
            # )
            # #data = yt_dl.extract_info(yt_url, download=False)
            # audio_url = data["url"]
            audio_urls = await get_youtube_audio_url(yt_url)
            if audio_urls is None:
                print(f"Failed to fetch audio URLs for YouTube URL: {yt_url}")
                return None
            print("GOT len(audio_urls)", len(audio_urls))
            if not audio_urls or len(audio_urls) == 0:
                print(f"No audio URLs found for YouTube URL: {yt_url}")
                return None
            if return_all:
                print("Returning all audio URLs")
                return audio_urls
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
            "is_playlist": self.is_playlist,
            "lavalink_track_id": self.lavalink_track_id
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
                is_playlist = data.get("is_playlist"),
                lavalink_track_id=data.get("lavalink_track_id", None),
            )
        except Exception as e:
            print("what the", e)
            return None




