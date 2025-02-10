import asyncio

import uvloop

# Set uvloop as the event loop policy
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

import discord
import os
from yt_dlp import YoutubeDL
from pytube import YouTube, Playlist, Search
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import gc
import requests
import time
from PIL import Image
import requests
import io
import random
from dotenv import load_dotenv, find_dotenv
from music.utils.message_crafter import *

load_dotenv(find_dotenv())

client_id = os.getenv("SPOTIFY_CLIENT_ID") 
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")  

# Create an instance of the Spotipy client
client_credentials_manager = SpotifyClientCredentials(
    client_id=client_id, client_secret=client_secret
)

sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

commands_list_aliases = {
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

import discord
from discord.ext import commands
from models.client import Client
from typing import Dict
from core.extensions.server_manager import server_manager
from core.extensions.firebase import fbc
from cogs.music import MusicCog
from cogs.playlist import PlaylistCog
from core.commands_handler import RateLimitCheckFailure, NotInVoiceChannelCheckFailure

intents = discord.Intents.default()

intents.voice_states = True
intents.message_content = True
intents.messages = True
intents.guilds = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

bot = commands.Bot(command_prefix='-', intents=intents, help_command = None)

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    
    await bot.add_cog(MusicCog(bot, server_manager))
    await bot.add_cog(PlaylistCog(bot, server_manager))

    print("All cogs loaded")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Slow down there! Wait {round(error.retry_after, 2)} seconds before sending another message")

    if isinstance(error, RateLimitCheckFailure):
        await ctx.send(f"Slow down there! Wait {ctx.kwargs['waiting_time']} seconds before sending another message")

    if isinstance(error, NotInVoiceChannelCheckFailure):
        await ctx.send("You must be in a voice channel to use this command")

@bot.event
async def on_guild_join(guild: discord.Guild):
    """
    When the bot joins a new guild, this function is called
    This will create a new guild entry in the database and populate it with the default settings.
    """

    default_data = {
                "guild_id": guild.id,
                "max_concurrent_song_loadings": 2,
                "playlists": [],
                "acceptable_delay": 5
            }
    fbc.set_client(guild.id, default_data)

class HelpOptions(discord.ui.Select):
    def __init__(self):
        options=[
            discord.SelectOption(label="General"),
            discord.SelectOption(label="Playing Music",emoji="🎵"),
            discord.SelectOption(label="Music Playback Controls",emoji="⏯", description="To pause, resume, skip, delete, etc."),
            discord.SelectOption(label="Custom Playlist Commands",emoji="🎶"),
            ]
        
        super().__init__(placeholder="Select an option",max_values=1,min_values=1,options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Playing Music":
            await interaction.response.edit_message(embed = craft_playing_music_help_command())
        elif self.values[0] == "Music Playback Controls":
            await interaction.response.edit_message(embed = craft_music_playback_controls_help_command())
        elif self.values[0] == "Custom Playlist Commands":
            await interaction.response.edit_message(embed = craft_custom_playlist_help_command())
        elif self.values[0] == "General":
            await interaction.response.edit_message(embed = craft_default_help_command())

class HelpView(discord.ui.View):
    def __init__(self, *, timeout = None):
        super().__init__(timeout=timeout)
        self.add_item(HelpOptions())


@bot.command()
@commands.dynamic_cooldown(lambda x: commands.Cooldown(1,1), type = commands.BucketType.user)
async def help(ctx):
    await ctx.send(embed = craft_default_help_command(), view = HelpView())
    
    
bot.run(os.getenv("SECRET_KEY"))