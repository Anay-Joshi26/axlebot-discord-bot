from models.client import Client
from typing import Dict
import asyncio
import discord
import discord.ext.commands as commands

class ServerManager:
    def __init__(self):
        # Active clients who have invoked client needing commands recently
        self.active_clients: Dict[int, Client] = {}

    async def get_client(self, guild_id: int, ctx: commands.Context = None) -> Client:
        """
        Returns the client for the given guild id
        """
        # If the client had only just invoked a client needing command, then the client will be in the active clients list
        if guild_id not in self.active_clients:
            if ctx is not None:
                msg = await ctx.send("*Please wait while we fetch your server data...\nStaying inactive for a while will remove server data from quick access*")

            self.active_clients[guild_id] = await Client.from_guild_id(guild_id)

            print("Client put into active clients")

            if ctx is not None:
                await msg.delete()

        return self.active_clients[guild_id]
    
    
    def remove_client(self, guild_id):
        if guild_id in self.active_clients:
            del self.active_clients[guild_id]
