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
        print("Getting client for guild", guild_id)
        client = await self.clients.get(str(guild_id))
        #
        client = await Client.from_dict(client)

        print(client)

        if not client:
            # if ctx:
            #     msg = await ctx.send("*Please wait while we fetch your server data...*")

            # client = await Client.from_guild_id(guild_id)
            # await self.cache.set(str(guild_id), client)

            # if ctx:
            #     await msg.delete()
            pass

        return client
    
    
    def remove_client(self, guild_id):
        pass
