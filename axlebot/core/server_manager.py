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

    async def get_client(self, guild_id: int, ctx: commands.Context = None) -> Client:
        # Start a task to fetch the client
        fetch_task = asyncio.create_task(self.clients.get(str(guild_id)))

        await asyncio.sleep(0.1)

        fetch_msg = None
        if not fetch_task.done() and ctx:
            fetch_msg = await ctx.send("Please wait, I am fetching your server information...")

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

        print("Client found in cache")
        return client

    
    
    def remove_client(self, guild_id):
        pass
