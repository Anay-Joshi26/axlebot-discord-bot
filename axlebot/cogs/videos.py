import discord
from discord.ext import commands
from core.commands_handler import audio_command_check, in_voice_channel, cooldown_time
from music.song_request_handler import determine_query_type
from models.song import Song, LyricsStatus
import asyncio
from utils.message_crafter import *
from core.server_manager import ServerManager
from models.client import Client
from music.songs_queue import SongQueue
from discord.ext.commands import BucketType, CommandOnCooldown


class VideoDownloadCog(commands.Cog):
    """
    This cog is responsible for handling video download commands. This bot allows users to download videos from YouTube (within constraints).
    """
    def __init__(self, bot, server_manager):
        self.bot = bot
        self.server_manager : ServerManager = server_manager