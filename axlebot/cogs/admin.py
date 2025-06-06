import discord
from discord.ext import commands
from core.commands_handler import audio_command_check, in_voice_channel, cooldown_time, has_manage_guild
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

    async def _process_entities(self, ctx: commands.Context, args, client, entity_type, fetch_fn, allowed_list, change_fn, action):
        if not args:
            await ctx.send(f"Please provide valid {entity_type}(s).")
            return

        successful, failed = [], []

        for name in args:
            print(f"Processing {entity_type}: {name}")   
            discord_id, tag = discord_tag_to_id(name)
            if discord_id is None or tag != entity_type:
                if name == "@everyone" and entity_type == "role":
                    discord_id = ctx.guild.id # Role ID for @everyone is the guild ID itself
                else:
                    failed.append(name)
                    continue

            entity = fetch_fn(discord_id)
            if not entity:
                failed.append(name)
                continue

            is_already_present = discord_id in allowed_list
            should_update = (action == "add" and not is_already_present) or (action == "remove" and is_already_present)

            if should_update:
                await change_fn(client, discord_id, action)
                successful.append(entity.name)

        if successful:
            embed = craft_update_access_embed(entity_type, successful, action)
            await ctx.send(embed = embed) #, allowed_mentions = discord.AllowedMentions.none()
        if failed:
            embed = craft_update_access_embed(entity_type, failed, action, added=False)
            await ctx.send(embed = embed)


    @commands.command()
    @commands.dynamic_cooldown(cooldown_time, type=BucketType.user)
    @commands.check(has_manage_guild)
    async def add_use_role(self, ctx: commands.Context, *args):
        client = await self.server_manager.get_client(ctx.guild.id)
        await self._process_entities(
            ctx, args, client, "role",
            ctx.guild.get_role,
            client.server_config.permitted_roles_of_use,
            self.change_use_role,
            "add"
        )

    @commands.command()
    @commands.dynamic_cooldown(cooldown_time, type=BucketType.user)
    @commands.check(has_manage_guild)
    async def remove_use_role(self, ctx: commands.Context, *args):
        client = await self.server_manager.get_client(ctx.guild.id)
        await self._process_entities(
            ctx, args, client, "role",
            ctx.guild.get_role,
            client.server_config.permitted_roles_of_use,
            self.change_use_role,
            "remove"
        )

    @commands.command()
    @commands.dynamic_cooldown(cooldown_time, type=BucketType.user)
    @commands.check(has_manage_guild)
    async def add_use_channel(self, ctx: commands.Context, *args):
        client = await self.server_manager.get_client(ctx.guild.id)
        await self._process_entities(
            ctx, args, client, "channel",
            ctx.guild.get_channel,
            client.server_config.permitted_channels_of_use,
            self.change_use_channel,
            "add"
        )

    @commands.command()
    @commands.dynamic_cooldown(cooldown_time, type=BucketType.user)
    @commands.check(has_manage_guild)
    async def remove_use_channel(self, ctx: commands.Context, *args):
        client = await self.server_manager.get_client(ctx.guild.id)
        await self._process_entities(
            ctx, args, client, "channel",
            ctx.guild.get_channel,
            client.server_config.permitted_channels_of_use,
            self.change_use_channel,
            "remove"
        )


    async def change_use_channel(self, client: Client, channel_id, action: str):
        await getattr(client.server_config, f"{action}_permitted_channel")(channel_id)

    async def change_use_role(self, client: Client, role_id, action: str):
        await getattr(client.server_config, f"{action}_permitted_role")(role_id)

    @commands.command()
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    @commands.check(has_manage_guild)
    async def see_access_channels(self, ctx: commands.Context):
        client: Client = await self.server_manager.get_client(ctx.guild.id)
        channels = client.server_config.permitted_channels_of_use
        if not channels:
            await ctx.send(embed = craft_see_access_embed("channel", []))
            return
        channel_names = [ctx.guild.get_channel(channel_id).name for channel_id in channels if ctx.guild.get_channel(channel_id)]
        await ctx.send(embed = craft_see_access_embed("channel", channel_names))
        
    @commands.command()
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    @commands.check(has_manage_guild)
    async def see_access_roles(self, ctx: commands.Context):
        client: Client = await self.server_manager.get_client(ctx.guild.id)
        roles = client.server_config.permitted_roles_of_use
        if not roles:
            await ctx.send(embed = craft_see_access_embed("role", []))
            return
        role_names = [ctx.guild.get_role(role_id).name for role_id in roles if ctx.guild.get_role(role_id)]
        await ctx.send(embed = craft_see_access_embed("role", role_names))


    @commands.command(aliases = ['del_message_after_play', 'del_msg_after_play', 'dmap'])
    @commands.dynamic_cooldown(cooldown_time, type = BucketType.user)
    @commands.check(has_manage_guild)
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
        

        
