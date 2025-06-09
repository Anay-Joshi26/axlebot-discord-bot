from models.client import Client
from typing import Dict
import asyncio
import discord
import discord.ext.commands as commands
from core.caching.managed_cache import CacheManager
from core.caching.base_cache import BaseCache

class ServerManager:
    def __init__(self, cache_manager: CacheManager):
        # Active clients who have invoked client needing commands recently
        self.clients = cache_manager

    @property
    def active_clients(self) -> BaseCache:
        """
        Returns the active clients.
        """
        print("Active clients", self.clients.active_cache)
        return self.clients.active_cache

    async def get_client(self, guild_id: int, ctx: commands.Context = None, wait_msg = True, return_newly_created = False) -> Client:
        """
        Fetches the client for the given guild ID. If the client is not found in the cache, it creates a new one.
        :param guild_id: The ID of the guild to fetch the client for.
        :param ctx: The context of the command, used to send messages if needed.
        :param wait_msg: Whether to send a message indicating that the client is being fetched.
        :param return_newly_created: Whether to return a tuple of (client, is_new) or just the client. This is useful for determining if a new client was created.
        :return: The client for the given guild ID, or None if it could not be fetched or created.
        """

        # Start a task to fetch the client
        fetch_task = asyncio.create_task(self.clients.get(str(guild_id), return_newly_created=return_newly_created))

        await asyncio.sleep(0.0075)

        fetch_msg = None
        if not fetch_task.done() and ctx:
            if wait_msg:
                fetch_msg = await ctx.send("Please wait, I am fetching your server information...")

        is_new = False
        if return_newly_created:
            client, is_new = await fetch_task
        else:
            client: Client = await fetch_task

        if fetch_msg:
            await fetch_msg.delete()

        if ctx and ctx.voice_client is not None and ctx.voice_client.is_connected():
            print("Voice client is connected, setting voice client in the client object")
            client.voice_client = ctx.guild.voice_client

        if client is None:
            print("Client not found in cache, creating new client")
            if ctx:
                await ctx.send("An error occurred, I was not able to get your server information")
            return None

        if return_newly_created:
            return client, is_new
        
        return client
    
    
    def remove_client(self, guild_id):
        pass
