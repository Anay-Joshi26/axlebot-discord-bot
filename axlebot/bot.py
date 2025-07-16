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
from utils.message_crafter import *

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
#from models.client import Client
from typing import Dict
from core.extensions.server_manager import server_manager
from core.extensions.firebase import fbc
from cogs.music import MusicCog
from cogs.playlist import PlaylistCog
from cogs.admin import AdminCog
from core.commands_handler import NotInVoiceChannelCheckFailure, has_manage_guild, NoPermissionsCheckFailure
from core.extensions import cache_manager
import lavalink
import core.extensions


# intents = discord.Intents.default()

# intents.voice_states = True
# intents.message_content = True
# intents.messages = True
# intents.guilds = True

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# bot: commands.Bot = commands.Bot(command_prefix='-', intents=intents, help_command = None)
from core.extensions import bot

#lavalink_client = lavalink.Client(bot.user.id)

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    

    await bot.add_cog(MusicCog(bot, server_manager))
    await bot.add_cog(PlaylistCog(bot, server_manager))
    await bot.add_cog(AdminCog(bot, server_manager))
    cache_manager.start()  # Start the cache manager
    print("Cache manager started")

    core.extensions.lavalink_client = lavalink.Client(bot.user.id)
    core.extensions.lavalink_client.add_node('localhost', 2333, 'HEYthisIsAReallyHardPAss0rdToGu3ss', 'au', 'axlebot-lavalink')
    # core.extensions.lavalink_client.add_node(
    #     'lavahatry4.techbyte.host',  # Host
    #     3000,                         # Port
    #     'NAIGLAVA-dash.techbyte.host',  # Password (yes, it's a URL)
    #     'au',                        # Region (Australia or whatever's closest)
    #     'axlebot-lavalink'            # Node name (can be anything you want)
    # )

    bot.lavalink = core.extensions.lavalink_client

    print("All cogs loaded")

@bot.event
async def on_guild_join(guild: discord.Guild):
    """
    When the bot joins a new guild, this function is called
    This will create a new guild entry in the database and populate it with the default settings.
    """
    print(f"Joined a new guild: {guild.name} (ID: {guild.id})")

    client, is_new = await server_manager.get_client(guild.id, wait_msg=False, return_newly_created=True)

    if is_new:
        music_channel_id = None
        for channel in guild.text_channels:
            if channel.name.lower() == "music":
                music_channel_id = channel.id
                break  # stop after first match
        if music_channel_id is not None:
            try:
                await client.server_config.add_permitted_channel(music_channel_id)
            except ValueError as e:
                print(f"Error adding music channel: {e}")

    # Optional: send a message to the system channel or first text channel
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        await guild.system_channel.send(f"{'Glad to be back' if not is_new else 'Thank you for adding me to the server'}!\n{'To help you get started see the help command below' if is_new else 'As a returning user, below is a refresher on the help command'}")
        await guild.system_channel.send(embed=craft_default_help_command(), view=HelpView())
    else:
        # Fallback: try first available channel with send permissions
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await guild.system_channel.send(f"{'Glad to be back' if not is_new else 'Thank you for adding me to the server'}!\n{'To help you get started see the help command below' if is_new else 'As a returning user, below is a refresher on the help command'}")
                await guild.system_channel.send(embed=craft_default_help_command(), view=HelpView())
                break
        
@bot.event
async def on_guild_channel_delete(channel):
    if isinstance(channel, discord.TextChannel):
        admin_cog: AdminCog = bot.get_cog("AdminCog")
        if not admin_cog:
            return
        client = await server_manager.get_client(channel.guild.id)
        if not client:
            return
        await admin_cog.change_use_channel(client, channel.id, "remove")

@bot.event
async def on_guild_role_delete(role):
    if isinstance(role, discord.Role):
        admin_cog: AdminCog = bot.get_cog("AdminCog")
        if not admin_cog:
            return
        client = await server_manager.get_client(role.guild.id)
        if not client:
            return
        await admin_cog.change_use_role(client, role.id, "remove")

@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Slow down there! Wait {round(error.retry_after, 2)} seconds before sending another message.", 
                       delete_after=6,
                       silent = True)
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid argument provided.", 
                       delete_after=6,
                       silent = True)
    elif isinstance(error, (NotInVoiceChannelCheckFailure, NoPermissionsCheckFailure)):
        await ctx.send(f"{error}", 
                       delete_after=7,
                       silent = True)
    elif isinstance(error, commands.CommandNotFound):
        await ctx.message.add_reaction("❓", ) # question mark
        await asyncio.sleep(15)
        await ctx.message.remove_reaction("❓", ctx.me)  # Remove the reaction after a short delay
    else:
        print(f"An error occurred: {error}")

# class NextPageButton(discord.ui.Button):
#     def __init__(self):
#         super().__init__(label="Next Page", style=discord.ButtonStyle.primary)

#     async def callback(self, interaction: discord.Interaction):
#         view = self.view
#         view.current_page = 2
#         view.clear_nav_buttons()
#         view.add_nav_button(PreviousPageButton())
#         await interaction.response.edit_message(embed=craft_custom_playlist_help_command_page_2(), view=view)

# class PreviousPageButton(discord.ui.Button):
#     def __init__(self):
#         super().__init__(label="Previous Page", style=discord.ButtonStyle.secondary)

#     async def callback(self, interaction: discord.Interaction):
#         view = self.view
#         view.current_page = 1
#         view.clear_nav_buttons()
#         view.add_nav_button(NextPageButton())
#         await interaction.response.edit_message(embed=craft_custom_playlist_help_command(), view=view)

# class HelpOptions(discord.ui.Select):
#     def __init__(self):
#         options=[
#             discord.SelectOption(label="General"),
#             discord.SelectOption(label="Playing Music",emoji="🎵"),
#             discord.SelectOption(label="Music Playback Controls",emoji="⏯", description="To pause, resume, skip, delete, etc."),
#             discord.SelectOption(label="Custom Playlist Commands",emoji="🎶"),
#             ]
        
#         super().__init__(placeholder="Select an option",max_values=1,min_values=1,options=options)

#     async def callback(self, interaction: discord.Interaction):
#         view = self.view
#         # Clear any existing navigation buttons
#         view.clear_nav_buttons()
        
#         if self.values[0] == "Playing Music":
#             await interaction.response.edit_message(embed=craft_playing_music_help_command(), view=view)
#         elif self.values[0] == "Music Playback Controls":
#             await interaction.response.edit_message(embed=craft_music_playback_controls_help_command(), view=view)
#         elif self.values[0] == "Custom Playlist Commands":
#             # Reset to page 1 and add Next Page button
#             view.current_page = 1
#             view.current_section = "Custom Playlist Commands"
#             view.add_nav_button(NextPageButton())
#             await interaction.response.edit_message(embed=craft_custom_playlist_help_command(), view=view)
#         elif self.values[0] == "General":
#             await interaction.response.edit_message(embed=craft_default_help_command(), view=view)

# class HelpView(discord.ui.View):
#     def __init__(self, *, timeout=None):
#         super().__init__(timeout=timeout)
#         self.current_section = "General"
#         self.current_page = 1
#         self.select = HelpOptions()
#         self.add_item(self.select)
    
#     def clear_nav_buttons(self):
#         # Remove all items except the select dropdown
#         self.clear_items()
#         self.add_item(self.select)
    
#     def add_nav_button(self, button):
#         self.add_item(button)

class NextPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Next Page", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        view.current_page = 2
        view.clear_nav_buttons()
        view.add_nav_button(PreviousPageButton())

        if view.current_section == "Custom Playlist Commands":
            await interaction.response.edit_message(
                embed=craft_custom_playlist_help_command_page_2(), view=view
            )
        elif view.current_section == "Music Playback Controls":
            await interaction.response.edit_message(
                embed=craft_music_playback_controls_help_command_page_2(), view=view
            )

class PreviousPageButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Previous Page", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        view.current_page = 1
        view.clear_nav_buttons()
        view.add_nav_button(NextPageButton())

        if view.current_section == "Custom Playlist Commands":
            await interaction.response.edit_message(
                embed=craft_custom_playlist_help_command(), view=view
            )
        elif view.current_section == "Music Playback Controls":
            await interaction.response.edit_message(
                embed=craft_music_playback_controls_help_command(), view=view
            )

class HelpOptions(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="General"),
            discord.SelectOption(label="Playing Music", emoji="🎵"),
            discord.SelectOption(label="Music Playback Controls", emoji="⏯", description="To pause, resume, skip, delete, etc."),
            discord.SelectOption(label="Music Filters", emoji="🔧", description="To apply various audio filters like bassboosting, speeding up etc"),
            discord.SelectOption(label="Custom Playlist Commands", emoji="🎶"),
        ]

        super().__init__(placeholder="Select an option", max_values=1, min_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        view.clear_nav_buttons()

        selected = self.values[0]
        view.current_section = selected
        view.current_page = 1

        if selected == "General":
            await interaction.response.edit_message(embed=craft_default_help_command(), view=view)

        elif selected == "Playing Music":
            await interaction.response.edit_message(embed=craft_playing_music_help_command(), view=view)

        elif selected == "Music Playback Controls":
            view.add_nav_button(NextPageButton())
            await interaction.response.edit_message(embed=craft_music_playback_controls_help_command(), view=view)

        elif selected == "Music Filters":
            await interaction.response.edit_message(embed=craft_music_filters_help_command(), view=view)

        elif selected == "Custom Playlist Commands":
            view.add_nav_button(NextPageButton())
            await interaction.response.edit_message(embed=craft_custom_playlist_help_command(), view=view)

class HelpView(discord.ui.View):
    def __init__(self, *, timeout=None):
        super().__init__(timeout=timeout)
        self.current_section = "General"
        self.current_page = 1
        self.select = HelpOptions()
        self.add_item(self.select)

    def clear_nav_buttons(self):
        self.clear_items()
        self.add_item(self.select)

    def add_nav_button(self, button):
        self.add_item(button)


@bot.command()
@commands.dynamic_cooldown(lambda x: commands.Cooldown(1,1), type=commands.BucketType.user)
async def help(ctx: commands.Context, *args):
    """
    Displays the help command with options to navigate through different sections.
    If no arguments are provided, it shows the default help command.

    if `-help admin` is provided, it will show the admin help command.
    """
    if not args:
        await ctx.send(embed=craft_default_help_command(), view=HelpView())
    elif args[0].lower() == "admin":
        if has_manage_guild(ctx):
            await ctx.author.send(embed=craft_admin_help_command())
            await ctx.message.add_reaction("✅")
            await asyncio.sleep(10)
            await ctx.message.remove_reaction("✅", ctx.me)
        else:
            await ctx.message.add_reaction("❌")
            await asyncio.sleep(10)
            await ctx.message.remove_reaction("❌", ctx.me)
    
    
bot.run(os.getenv("SECRET_KEY"))