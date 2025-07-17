from core.extensions.server_manager import server_manager
import discord
from discord.ext import commands
#from discord import app_commands
import asyncio

class RateLimitCheckFailure(commands.CheckFailure):
    pass

class NotInVoiceChannelCheckFailure(commands.CheckFailure):
    pass

class NoPermissionsCheckFailure(commands.CheckFailure):
    pass

def audio_command_check(ctx):
    in_voice_channel(ctx)
    return True

def has_manage_guild(ctx: commands.Context):
    if not ctx.author.guild_permissions.manage_guild:
        #raise NoPermissionsCheckFailure("You do not have the required permissions to use this command.")
        return False
    return True

    
async def in_voice_channel(ctx):
    user_vc = ctx.author.voice
    bot_vc = ctx.voice_client

    if user_vc is None:
        raise NotInVoiceChannelCheckFailure("You must be in a voice channel to use this command.")

    if bot_vc and user_vc.channel != bot_vc.channel:
        raise NotInVoiceChannelCheckFailure("You must be in the same voice channel as the bot to use this command.")

    return True


async def in_voice_channel_interaction(interaction: discord.Interaction):
    user = interaction.user
    if isinstance(user, discord.Member) and user.voice is None:
        raise NotInVoiceChannelCheckFailure("You must be in a voice channel to use this command")
    return True

async def fetch_client(ctx):
    """
    Fetch the client for the given context and will store it.
    The function only needs to be called at the start to fetch the client to store in memory
    """
    await server_manager.get_client(ctx.guild.id, ctx)
    return True

async def bot_use_permissions(ctx: commands.Context, client = None):
    """
    Check if the user has the required permissions to execute playback commands.
    This is a more specific check than the general permissions check.
    """
    if client is None:
        client = await server_manager.get_client(ctx.guild.id, ctx)

    config = client.server_config

    print([(ctx.author.name ,role.name, role.id) for role in ctx.author.roles], config.permitted_roles_of_use)
    
    if config.permitted_channels_of_use is None or len(config.permitted_channels_of_use) == 0:
        raise NoPermissionsCheckFailure("No channels are configured to use this command.")
    
    if ctx.channel.id not in config.permitted_channels_of_use:
        raise NoPermissionsCheckFailure("You cannot use this command in this channel.")
    
    if config.permitted_roles_of_use is None or len(config.permitted_roles_of_use) == 0:
        if has_manage_guild(ctx):
            return True
        raise NoPermissionsCheckFailure("No roles are configured to use this command.")
    
    if has_manage_guild(ctx):
        return True
        
    user_role_ids = {role.id for role in ctx.author.roles}

    print("User roles:", user_role_ids)

    print(config.permitted_roles_of_use.isdisjoint(user_role_ids))

    if config.permitted_roles_of_use.isdisjoint(user_role_ids):
        raise NoPermissionsCheckFailure("You do not have the required role to use this command.")
    
    return True

def cooldown_time(ctx):
    if ctx.author.id == 253477867717918721: # my ID
        #print("I get special treatment :)")
        return commands.Cooldown(2, 1)

    client = server_manager.active_clients.get(ctx.guild.id)

    if client is None or not client.is_premium:
        return commands.Cooldown(1, 4) # one message every 4 seconds
    
    print("Active client and premium cooldown")
    return commands.Cooldown(1, 1)

