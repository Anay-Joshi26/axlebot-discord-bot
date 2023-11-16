import asyncio
import discord
from yt_dlp import YoutubeDL
from pytube import YouTube, Playlist, Search
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


client_id = "SPOTIFY_CLIENT_ID" 
client_secret = "SPOTIFY_CLIENT_SECRET"  

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
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }
    ],
    "extractaudio": True,
    "audioformat": "mp3",
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
    "options": "-vn -ar 48000 -ac 2 -bufsize 2000k -probesize 100M -b:a 128k",
}


class Song:
    def __init__(self, duration, artist, yt_url, player, name, thumbnail_url, audio_url, is_spot=False, is_yt=False):
        self.yt_url = yt_url
        self.name = name
        self.artist = artist
        self.player = player
        self.is_spot = is_spot
        self.thumbnail_url = thumbnail_url
        self.duration = duration
        self.audio_url = audio_url
        self.is_yt = is_yt

    @classmethod
    async def CreateSong(cls, youtube_query):
        yt_url, name, duration = cls.search_youtube_video(youtube_query)
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: yt_dl.extract_info(yt_url, download=False)
        )
        artist = data.get("artist") or data.get("uploader") or "Unknown Artist"
        thumbnail_url = data["thumbnail"]
        audio_url = data["url"]
        player = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        print("SONG CREATED")
        return cls(duration, artist, yt_url, player, name, thumbnail_url, audio_url)

    @classmethod
    async def SpotifyPlaylistSongList(cls, spotify_playlist_url):
        list_of_songs = []
        track_info = cls.get_spotify_info(spotify_playlist_url)
        for track in track_info:
            name, artist, thumbnail_url = track[0], track[1], track[2]
            yt_url, _ , duration = cls.search_youtube_video(f"{name} by {artist} audio")
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, lambda: yt_dl.extract_info(yt_url, download=False)
            )
            audio_url = data["url"]
            player = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
            list_of_songs.append(cls(duration, artist, yt_url, player, name, thumbnail_url, audio_url, is_spot = True))
        return list_of_songs
    
    @classmethod
    async def SpotifySong(cls, name, artist, thumbnail_url):
        yt_url, _ , duration = cls.search_youtube_video(f"{name} by {artist} audio")
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: yt_dl.extract_info(yt_url, download=False)
        )
        audio_url = data["url"]
        player = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        return cls(duration, artist, yt_url, player, name, thumbnail_url, audio_url, is_spot = True)

    @classmethod
    async def YouTubePlaylistSong(cls, yt_url):
        name, duration = cls.search_youtube_video_by_url(yt_url)
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: yt_dl.extract_info(yt_url, download=False)
        )
        artist = data.get("artist") or data.get("uploader") or "Unknown Artist"
        thumbnail_url = data["thumbnail"]
        audio_url = data["url"]
        player = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        return cls(duration, artist, yt_url, player, name, thumbnail_url, audio_url, is_yt = True)
    
    @classmethod
    async def SongFromYouTubeURL(cls, yt_url):
        name, duration = cls.search_youtube_video_by_url(yt_url)
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: yt_dl.extract_info(yt_url, download=False)
        )
        artist = data.get("artist") or data.get("uploader") or "Unknown Artist"
        thumbnail_url = data["thumbnail"]
        audio_url = data["url"]
        player = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        return cls(duration, artist, yt_url, player, name, thumbnail_url, audio_url)

    def get_fresh_player(self):
        return discord.FFmpegPCMAudio(self.audio_url, **ffmpeg_options)

    @classmethod
    async def YouTubePlaylistSongList(cls, yt_playlist_link):
        yt_playlist_urls = cls.get_youtube_playlist_info
        list_of_songs = []
        for yt_url in yt_playlist_urls:
            name, duration = cls.search_youtube_video_by_url(yt_url)
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None, lambda: yt_dl.extract_info(yt_url, download=False)
            )
            artist = data.get("artist") or data.get("uploader") or "Unknown Artist"
            thumbnail_url = data["thumbnail"]
            audio_url = data["url"]
            player = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
            list_of_songs.append(cls(duration, artist, yt_url, player, name, thumbnail_url, audio_url, is_yt = True))
        return list_of_songs

    @classmethod
    def get_spotify_info(self, query):
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
    
    @classmethod
    def get_youtube_playlist_info(self, query):
        p = Playlist(query)
        return [url for url in p.video_urls]
    
    @classmethod
    def search_youtube_video(self, query):
        search_results = Search(query)

        if len(search_results.results) > 0:
            video_url = (
                f"https://www.youtube.com/watch?v={search_results.results[0].video_id}"
            )
            return (video_url, search_results.results[0].title, search_results.results[0].length)

        return None,None,None
    
    @classmethod
    def search_youtube_video_by_url(self, url):
        video = YouTube(url)
        return video.title, video.length
    

    
    



    



    
    


    



