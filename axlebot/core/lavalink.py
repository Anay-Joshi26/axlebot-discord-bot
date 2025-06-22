import re

import discord
import lavalink
from discord.ext import commands
from lavalink.events import TrackStartEvent, QueueEndEvent, TrackEndEvent, TrackExceptionEvent, TrackStuckEvent
from lavalink.errors import ClientError
from lavalink.filters import LowPass
from lavalink.server import LoadType
import asyncio
import core.extensions


url_rx = re.compile(r'https?://(?:www\.)?.+')


class LavalinkVoiceClient(discord.VoiceClient):
    """
    This is the preferred way to handle external voice sending
    This client will be created via a cls in the connect method of the channel
    see the following documentation:
    https://discordpy.readthedocs.io/en/latest/api.html#voiceprotocol
    """

    def __init__(self, bot: discord.Client, channel: discord.abc.Connectable):
        super().__init__(bot, channel)
        self.client = bot
        self.channel = channel
        self.guild_id = channel.guild.id
        self._destroyed = False
        self._lavalink = core.extensions.lavalink_client # shouldnt be needed
        self._after_callback = None
        self._current_track_id = None
        self._loop = asyncio.get_running_loop()
        self._lavalink.add_event_hooks(self)

    async def play(self, track, *, after=None):
        self._after_callback = after
        self._current_track_id = track.track
        await self.player.play(track)

    async def stop(self):
        print("Stopping the player")
        await self.player.stop()

    async def pause(self):
        await self.player.set_pause(True)

    async def resume(self):
        await self.player.set_pause(False)

    def is_connected(self):
        return self.channel is not None and self.channel.guild.voice_client is self
    
    def is_playing(self):
        return self.player.is_playing and not self.player.paused
    
    def is_paused(self):
        return self.player.paused

    @lavalink.listener(TrackEndEvent)
    async def on_track_end(self, event):
        print(f"Track ended: {event.track.title} in guild {self.guild_id}")
        if self._after_callback:
            try:
                self._after_callback(None)  # DO NOT await this
            except Exception as e:
                print(f"Error in after callback: {e}")
            self._after_callback = None

    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_SERVER_UPDATE',
            'd': data
        }
        await self._lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        channel_id = data['channel_id']

        if not channel_id:
            await self._destroy()
            return

        self.channel = self.client.get_channel(int(channel_id))

        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_STATE_UPDATE',
            'd': data
        }

        await self._lavalink.voice_update_handler(lavalink_data)

    async def _wait_for_lavalink_node(self, timeout=10, sleep_time=0.5) -> bool:
        """
        Wait until at least one Lavalink node is available or timeout expires.
        """
        total_wait = 0
        while total_wait < timeout:
            if self._lavalink.node_manager.available_nodes:
                return True
            await asyncio.sleep(sleep_time)
            total_wait += sleep_time
        return False

    async def connect(self, *, timeout: float, reconnect: bool, self_deaf: bool = False, self_mute: bool = False) -> None:
        """
        Connect the bot to the voice channel and create a player_manager
        if it doesn't exist yet.
        """
        if not await self._wait_for_lavalink_node():
            raise RuntimeError("No Lavalink nodes available. Please ensure the Lavalink server is running.")
        
        # ensure there is a player_manager when creating a new voice_client
        if not hasattr(self, 'player'):
            self.player = self._lavalink.player_manager.create(guild_id=self.channel.guild.id)

        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)
        print(f"Connected to voice channel {self.channel.name} in guild {self.channel.guild.name}")

    async def disconnect(self, *, force: bool = False) -> None:
        """
        Handles the disconnect.
        Cleans up running player and leaves the voice client.
        """
        player = self._lavalink.player_manager.get(self.channel.guild.id)

        # no need to disconnect if we are not connected
        if not force and not player.is_connected:
            return

        # None means disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # update the channel_id of the player to None
        # this must be done because the on_voice_state_update that would set channel_id
        # to None doesn't get dispatched after the disconnect
        player.channel_id = None
        await self._destroy()

    async def _destroy(self):
        self.cleanup()

        if self._destroyed:
            # Idempotency handling, if `disconnect()` is called, the changed voice state
            # could cause this to run a second time.
            return

        self._destroyed = True

        try:
            await self._lavalink.player_manager.destroy(self.guild_id)
        except ClientError:
            pass