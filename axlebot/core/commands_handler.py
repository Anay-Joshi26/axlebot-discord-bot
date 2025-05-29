from core.extensions.server_manager import server_manager
from discord.ext import commands
from discord import app_commands
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


def rate_limit(ctx):

    # ENABLED FOR NOW
    # if ctx.author.id == 253477867717918721:
    #     return True # if its me, then low it always
    return True
    
    # server_id = ctx.guild.id
    # if server_id not in server_manager.active_clients: return True

    # client = await server_manager.get_client(server_id, ctx)
    # ok, waiting_time = client.poke()
    # ctx.kwargs['waiting_time'] = waiting_time
    # if not ok:
    #     raise RateLimitCheckFailure("Sent too many messages")
    # print("Passed the rate limit", client.last_message_time)
    
    # return True
    
async def in_voice_channel(ctx):
    if ctx.author.voice is None:
        raise NotInVoiceChannelCheckFailure("You must be in a voice channel to use this command")
    
    return True

async def permissions(ctx):
    """
    Check if the user has the required permissions to execute the command.

    Returns True if the user has the required permissions, otherwise False.
    """

    # client = await server_manager.get_client(ctx.guild.id)



    # if ctx.author.guild_permissions.administrator:
    #     return True
    
    # raise NoPermissionsCheckFailure("You do not have the required permissions to use this command.")
    return True

def cooldown_time(ctx):

    client = server_manager.active_clients.get(ctx.guild.id)

    print("Checking cooldown time for client", client)

    if client is None or not client.is_premium:
        print("Not active client or not premium default cooldown")
        return commands.Cooldown(1, 5)
    
    print("Active client and premium cooldown")
    return commands.Cooldown(1, 1)

