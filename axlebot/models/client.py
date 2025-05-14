from music.songs_queue import SongQueue
import time
from typing import Tuple, Union
from models.playlist import Playlist
#from core.firebase import FirebaseClient
from core.extensions.firebase import fbc
import asyncio
import discord

class Client:
    def __init__(self, server_id):
        self.queue : SongQueue = SongQueue(server_id=server_id)
        self.server_id = server_id
        self.voice_client : discord.VoiceClient = None
        self.last_message_time = None
        self.acceptable_delay = 5
        self.time_to_wait_precision = 2
        self.commands_list_aliases = {
            "play": ["p", "play"],
            "queue": ["q", "queue"],
            "lyrics": ["l", "lyrics"],
            "skip": ["skip"],
            "resume": ["res", "resume"],
            "search": ["search", "s"],
            "pause": ["pause"],
            "delete": ["del", "delete"],
            "stop": ["stop"],
            "help": ["help"],
            "repeat": ["rep", "repeat"],
            "playnext": ["pn", "playnext", "playn", "pnext"],
            "shuffle": ["shuffle"],
            "yt_skip": ["skip yt"],
            "spot_skip": ["skip spot"]
        }
        self.max_concurrent_song_loadings = 2 # will increase to 5 if paid for premium
        self.playlists : list[Playlist] = []
        self.last_added_playlist: Union[Playlist, None] = None
        self.is_premium : bool | None = None # check this, coz its funky

    @staticmethod
    async def from_guild_id(guild_id):
        """
        Async method to create and initialize the client from guild_id.
        """
        data = await fbc.get_client_dict(guild_id)
        return await Client.from_dict(data, guild_id)
    
    def is_premium(self) -> bool:
        """
        Returns if the client is premium
        """
        if self.is_premium is not None: return self.is_premium

    async def _init_client_fields(self, server_id):
        """
        Initialises the client fields by fetching the guild from the database, creating a guild object in the database if it doesn't exist
        """
        data = await fbc.get_client_dict(server_id) 
        print(data, server_id) 
        await Client.from_dict(data, server_id)

        # list_of_playlists : list[Playlist] = [Playlist.from_dict(playlist_dict, server_id) for playlist_dict in data["playlists"]]
        # self.server_id = data["guild_id"]
        # self.max_concurrent_song_loadings = data["max_concurrent_song_loadings"]
        # self.acceptable_delay = data["acceptable_delay"]
        # self.playlists = list_of_playlists
        # self.last_added_playlist = max(list_of_playlists, key=lambda pl: pl.created_at)
    
    async def add_playlist(self, playlist : Playlist):
        """
        Adds a playlist to the client's list of playlists, within bounds of the max number of playlists allowed
        """
        if len(self.playlists) >= 10:
            raise ValueError("You have reached the maximum number of playlists allowed. Please delete one to create another.")
        
        for p in self.playlists:
            if p.name == playlist.name:
                raise ValueError("A playlist with that name already exists. Please choose another name.")
        
        self.playlists.append(playlist)
        self.last_added_playlist = playlist

        await fbc.set_data_attribute_for_client(self.server_id, "playlists", [playlist.to_dict() for playlist in self.playlists])

    async def update_playlist_changes_db(self):
        """
        Updates a playlist in the client's list of playlists
        """
        await fbc.set_data_attribute_for_client(self.server_id, "playlists", [playlist.to_dict() for playlist in self.playlists])

    def remove_playlist_index(self, index : int):
        """
        Removes a playlist from the client's list of playlists
        """
        return self.playlists.pop(index)
    
    def remove_playlist_by_playlist(self, playlist : Playlist):
        """
        Removes a playlist from the client's list of playlists by its name
        """
        self.playlists.remove(playlist)
        return None
    
    def get_playlist_by_name(self, name : str) -> Union[Playlist, None]:
        """
        Returns a playlist by its name
        """
        for playlist in self.playlists:
            if playlist.name == name:
                return playlist
        
        return None
    
    def __repr__(self):
        """
        Returns a string representation of the client object
        """
        return f"Client(server_id = {self.server_id}, is_premium = {self.is_premium})"
    
    def to_dict(self):
        """
        Converts the client object to a dictionary
        """
        return {
            "guild_id": self.server_id,
            "max_concurrent_song_loadings": self.max_concurrent_song_loadings,
            "acceptable_delay": self.acceptable_delay,
            "playlists": [playlist.to_dict() for playlist in self.playlists],
            "is_premium": self.is_premium
        }
    
    @staticmethod
    async def from_dict(data: dict, server_id: int | None = None):
        """
        Creates a client object from data dictionary
        This client is a client which has just began using the bot and has an empty queue
        """
        if server_id is None:
            server_id = data["guild_id"]

        client = Client(server_id)
        # list_of_playlists = await asyncio.gather(
        #     *[Playlist.from_dict(playlist_dict, server_id) for playlist_dict in data["playlists"]],
        #     return_exceptions=True
        # )
        list_of_playlists = [await Playlist.from_dict(playlist_dict, server_id) for playlist_dict in data["playlists"]]
        client.max_concurrent_song_loadings = data["max_concurrent_song_loadings"]
        client.acceptable_delay = data["acceptable_delay"]
        client.playlists = list_of_playlists
        client.is_premium = data["is_premium"]
        if len(list_of_playlists) > 0:
            client.last_added_playlist = max(list_of_playlists, key=lambda pl: pl.created_at)
            
        return client
    





        


    
