from music.songs_queue import SongQueue
import time
from typing import Tuple, Union
from models.playlist import Playlist
#from core.firebase import FirebaseClient
from core.extensions.firebase import fbc
import asyncio
import discord
from discord.ext import commands
from utils.message_crafter import craft_bot_music_stopped
from models.server_config import ServerConfig
from core.lavalink import LavalinkVoiceClient


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
        self.max_concurrent_song_loadings = 3 # will increase to 6 if paid for premium
        self.playlists : list[Playlist] = []
        self.last_added_playlist: Union[Playlist, None] = None
        self.is_premium : bool | None = None # check this, coz its funky
        self.exit_after_inactivity = 60 * 3 # 3 minutes
        self.stop_task = None # used to stop the client after a certain time of inactivity
        self.number_of_playlists_limit = 10
        self.client_lock = asyncio.Lock()  # Lock to prevent concurrent modifications to the client
        self.server_config: ServerConfig = ServerConfig(self)
        self.vc_stopped_due_to_seek = False
        #print("TEST TEST", core.extensions.lavalink_client.node_manager.available_nodes)
        #self.lavalink_player = core.extensions.lavalink_client.player_manager.get(server_id) or core.extensions.lavalink_client.player_manager.create(server_id)

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
    
    async def add_playlist(self, playlist : Playlist):
        """
        Adds a playlist to the client's list of playlists, within bounds of the max number of playlists allowed
        """
        if len(self.playlists) >= self.number_of_playlists_limit:
            raise ValueError("You have reached the maximum number of playlists allowed. Please delete one to create another.")
        
        for p in self.playlists:
            if p.name == playlist.name:
                raise ValueError("A playlist with that name already exists. Please choose another name.")
        
        self.playlists.append(playlist)
        self.last_added_playlist = playlist

        await self.update_playlist_changes_db()

        #await fbc.set_data_attribute_for_client(self.server_id, "playlists", [playlist.to_dict() for playlist in self.playlists])

    async def update_changes_by_attribute(self, attribute: str, value: any):
        """
        Updates a specific attribute of the client in the database
        """
        await fbc.set_data_attribute_for_client(self.server_id, attribute, value)

    async def update_entire_client(self):
        """
        Updates the entire client in the database
        """
        await fbc.set_data_for_client(self.server_id, self.to_dict())

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
    
    def interupt_inactivity_timer(self):
        """
        Interupts the inactivity timer if it is running
        """
        if self.stop_task is not None and not self.stop_task.done():
            self.stop_task.cancel()
            self.stop_task = None
    
    async def start_inactivity_timer(self, ctx: commands.Context, inactivity_time: int = None):
        """
        Starts a timer to stop the client after a certain time of inactivity
        """
        self.interupt_inactivity_timer()

        if inactivity_time is None:
            inactivity_time = self.exit_after_inactivity

        async def timer():
            try:
                await asyncio.sleep(inactivity_time)
                print(f"[INFO] Inactivity timer expired. Stopping client in guild {ctx.guild.id}")
                #await ctx.send("No activity for 2 minutes. Leaving the voice channel.", delete_after=20)
                await self.stop(ctx, send_embed=False)
            except asyncio.CancelledError:
                print(f"[INFO] Inactivity timer for guild {ctx.guild.id} cancelled.")
                return

        self.stop_task = asyncio.create_task(timer())
    
    async def stop(self, ctx: commands.Context, delete_after: int = 10, send_embed: bool = True):
        """
        This function stops the client from playing any music, clears the queue, and disconnects from the voice channel.
        """
        if send_embed:
            embed = craft_bot_music_stopped(delete_after=delete_after)
            await ctx.send(embed=embed, delete_after=delete_after)

        print(self.queue, self.voice_client, self.queue.current_song)

        if self.queue.current_song is not None:
            self.queue.current_song.stop()
        if self.voice_client is not None:
            self.voice_client.stop()
            await self.voice_client.disconnect(); self.voice_client = None
        await self.queue.clear()

        self.interupt_inactivity_timer()

    @staticmethod
    def get_base_client_dict(server_id: int) -> dict:
        """
        Returns a base client dictionary with default values for a new client.
        This is used to create a new client in the database.
        """
        return {
            "guild_id": server_id,
            "max_concurrent_song_loadings": 3,
            "acceptable_delay": 5,
            "playlists": [],
            "is_premium": False,
            "server_config": ServerConfig.get_default_config_dict()
        }

    def __dict__(self):
        """
        Converts the client object to a dictionary, exact same as to_dict()
        """
        return {
            "guild_id": self.server_id,
            "max_concurrent_song_loadings": self.max_concurrent_song_loadings,
            "acceptable_delay": self.acceptable_delay,
            "playlists": [playlist.to_dict() for playlist in self.playlists],
            "is_premium": self.is_premium,
            "server_config": self.server_config.to_dict()
        }
    
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
            "is_premium": self.is_premium,
            "server_config": self.server_config.to_dict()
        }
    
    @classmethod
    async def from_dict(cls, data: dict, server_id: int | None = None) -> "Client":
        """
        Creates a client object from data dictionary.
        This client is a client which has just begun using the bot and has an empty queue.
        """
        if server_id is None:
            server_id = data.get("guild_id")

        client = cls(server_id)

        playlists_data = data.get("playlists", [])
        list_of_playlists = [
            await Playlist.from_dict(playlist_dict, server_id)
            for playlist_dict in playlists_data
        ]

        client.max_concurrent_song_loadings = data.get("max_concurrent_song_loadings", 3)
        client.acceptable_delay = data.get("acceptable_delay", 5)
        client.playlists = list_of_playlists
        client.is_premium = data.get("is_premium", False)

        if list_of_playlists:
            client.last_added_playlist = max(list_of_playlists, key=lambda pl: pl.created_at)

        server_config_data = data.get("server_config", {})
        client.server_config = ServerConfig.from_dict(server_config_data, client)

        

        return client

    





        


    
