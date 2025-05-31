import discord
from discord.ext import commands
from core.commands_handler import rate_limit, audio_command_check, in_voice_channel, cooldown_time
from music.song_request_handler import determine_query_type
from models.song import Song, LyricsStatus
import asyncio
from utils.message_crafter import *
from utils import *
from core.server_manager import ServerManager
from models.client import Client
from music.songs_queue import SongQueue
from discord.ext.commands import BucketType, CommandOnCooldown


class AdminCog(commands.Cog):
    """
    This cog is responsible for handling administrative commands. Such as setting configs etc
    """
    def __init__(self, bot, server_manager):
        self.bot = bot
        self.server_manager : ServerManager = server_manager

    @commands.command(aliases = [])
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def set_music_playback_role(self, ctx, *args):
        """
        Sets the roles that can use the bot for music playback and related commands.
        """
        if not args:
            await ctx.send("Please provide a role name or ID.")
            return
        
        role_name = ' '.join(args)

        try:
            discord_id, tag_type = parse_tag(role_name, "role")
        except ValueError as e:
            await ctx.send(str(e))
            return

        client: Client = await self.server_manager.get_client(ctx.guild.id)

        role: discord.Role = ctx.guild.get_role(discord_id)

        if role is None:
            await ctx.send(f"'{role_name}' role not found in this server.")
            return
        
        if role.id in client.permitted_roles_of_use:
            pass
        else:
            client.permitted_roles_of_use.add(role.id)
            await client.update_changes_by_attribute("permitted_roles_of_use", list(client.permitted_roles_of_use))
        

    @commands.command(aliases = [])
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def set_use_channel(self, ctx: commands.Context, *args):
        """
        Sets the channel where the bot will listen to commands
        """
        if not args:
            await ctx.send("Please provide a channel name or ID.")
            return
        
        channel_name = ' '.join(args)

        try:
            discord_id, tag_type = parse_tag(channel_name, "channel")
        except ValueError as e:
            await ctx.send(str(e))
            return

        client: Client = await self.server_manager.get_client(ctx.guild.id)

        channel: discord.abc.GuildChannel = ctx.guild.get_channel(discord_id)

        if channel is None and not isinstance(channel, discord.TextChannel):
            await ctx.send(f"'{channel.name}' text channel not found in in this server.")
            return
        
        if channel.name in client.permitted_channels_of_use:
            pass
        else:
            client.permitted_channels_of_use.add(channel.id)
            await client.update_changes_by_attribute("permitted_channels_of_use", list(client.permitted_channels_of_use))

        print(f"Setting use channel for {ctx.guild.name} to {args}")

    @commands.command(aliases = [])
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    async def delete_message_after_play(self, ctx: commands.Context, *args):
        """
        Deletes the message after playing if the setting is enabled.
        """
        if not args:
            await ctx.send("Please provide 'true' or 'false'.")
            return
        
        value: str = args[0].lower()

        if value not in ["true", "false"]:
            await ctx.send("Please provide 'true' or 'false'.")
            return
        
        client: Client = await self.server_manager.get_client(ctx.guild.id)

        await client.server_config.set_delete_message_after_play(value == "true")

        await ctx.send(f"Delete message after play set to `{value.capitalize()}`.")
        

        
