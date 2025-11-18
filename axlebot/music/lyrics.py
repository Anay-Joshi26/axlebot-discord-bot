import asyncio
import discord
from models.song import Song
from discord.ext.commands import Context
import time
import bisect

class LyricSession:
    """
    Manages a synchronised lyric display for the currently playing song.

    This class tracks playback progress, determines the active lyric line, and
    updates a Discord message to highlight the current line. The update loop waits
    until a configurable proportion of the time between lyric timestamps has passed,
    then performs once-per-second updates until the next lyric line is reached.
    """
    def __init__(self, client, ctx: Context, lyrics: list[tuple[str, float]], current_song: Song):
        self.client = client
        self.client.current_lyrics_session = self                
        self.ctx = ctx      
        self.update_task: asyncio.Task | None = None             
        self.lyrics = [('♪', 0)] + [(line, timestamp / 1000) for line, timestamp in lyrics]  # convert ms to s
        self.start_times = [t[1] for t in self.lyrics]
        self.current_song = current_song
        self.message: discord.Message | None = None
        self.current_index = 0 # current line the song is at
        self.running = False
        self.preemptive_early_update_time = 0.39  # seconds before line timestamp to update
        self.wait_to_update_proportion = 0.7
        self._last_call = 0   # seconds (monotonic)
        self.min_determine_current_line_interval = 0.04 # throttle calls to this function
        self.base_wait_time = 0.1  # seconds

    async def start(self):
        """Start a synced lyrics session."""
        if not self.lyrics:
            await self.ctx.send("No lyrics available.")
            return

        self.running = True

        # Send initial message
        embed = self._build_embed()
        try:
            self.message = await self.ctx.send(embed=embed)
        except discord.HTTPException:
            self.running = False
            self.client.current_lyrics_session = None
            return await self.ctx.send(embed = discord.Embed(
                title=f"[TOO LONG TO SEND] Lyrics - {self.current_song.name}",
                description="The lyrics for this song are too long to send via Discord",
                colour=0xff9e42,
            ))

        # Start update loop
        self.update_task = asyncio.create_task(self._update_loop())

    async def stop(self):
        """Stop the loop and clean up."""
        self.running = False
        if self.update_task is not None and not self.update_task.done():
            self.update_task.cancel()
            self.update_task = None
        if self.message is not None:
            await self.message.delete()
            self.message = None
        self.client.current_lyrics_session = None

        

    # async def _update_loop(self):
    #     """Main loop to update lyrics based on timing."""
    #     while self.running:
    #         new_idx = await self._determine_current_line(update = False)
    #         if new_idx != self.current_index:
    #             self.current_index = new_idx
    #             await self._push_update()
    #         await asyncio.sleep(self.base_wait_time)  # e.g., 0.05s

    async def _update_loop(self):
        """Main loop to update lyrics based on timing."""
        while self.running:
            new_idx = await self._determine_current_line(update=False)

            if new_idx != self.current_index:
                self.current_index = new_idx
                await self._push_update()

            # ------- OPTIMISED WAITING LOGIC -------
            # Get timestamp of next lyric (if any)
            if self.current_index + 1 < len(self.lyrics):
                _, next_time = self.lyrics[self.current_index + 1]
                current_time = self.current_song.seconds_played  
                
                time_until_next = max(0, next_time - current_time)

                # If next line is far away, wait proportionally longer
                if time_until_next > self.base_wait_time:
                    sleep_time = time_until_next * self.wait_to_update_proportion
                else:
                    sleep_time = self.base_wait_time
            else:
                # No next line, just chill
                sleep_time = self.base_wait_time

            await asyncio.sleep(sleep_time)

    async def _push_update(self):
        if not self.message:
            return
        
        embed = self._build_embed()
        try:
            await self.message.edit(embed=embed)
        except discord.HTTPException:
            await self.stop()


    def _build_embed(self):
        """Return an embed representing the current visible lyrics window."""
        title=f"Lyrics - {self.current_song.name}"
        lyrics_str = ""
        lyrics_str += "\n".join(self.lyrics[i][0] for i in range(self.current_index))
        if self.lyrics[self.current_index][0]:
            lyrics_str += f"\n**{self.lyrics[self.current_index][0]}** <<\n"
        else:
            lyrics_str += f"\n{self.lyrics[self.current_index][0]}\n"
        lyrics_str += "\n".join(self.lyrics[i][0] for i in range(self.current_index + 1, len(self.lyrics)))

        embed = discord.Embed(
            title=title,
            description=lyrics_str,
            colour=discord.Colour.blurple()
        )

        return embed

    # async def _determine_current_line(self, update: bool = True):
    #     """Update current line so that: start <= seconds_played < next_start"""
    #     if not self.current_song.is_playing:
    #         return self.current_index
    #     if self.min_determine_current_line_interval > 0:
    #         now = time.monotonic()
    #         elapsed = now - self._last_call
    #         wait_time = self.min_determine_current_line_interval - elapsed
    #         if wait_time > 0:
    #             await asyncio.sleep(wait_time)
    #         self._last_call = time.monotonic()

    #     seconds = self.current_song.seconds_played + self.preemptive_early_update_time

    #     # Find the first line where seconds < next_start
    #     for i in range(len(self.lyrics) - 1):
    #         if seconds < self.lyrics[i + 1][1]:
    #             if update:
    #                 self.current_index = i
    #             return i

    #     # Past last line
    #     if update:
    #         self.current_index = len(self.lyrics) - 1
    #     return len(self.lyrics) - 1

    async def _determine_current_line(self, update: bool = True):
        """Update current line so that: start <= seconds_played < next_start"""
        if not self.current_song.is_playing:
            return self.current_index

        # Throttle calls
        if self.min_determine_current_line_interval > 0:
            now = time.monotonic()
            elapsed = now - self._last_call
            wait_time = self.min_determine_current_line_interval - elapsed
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._last_call = time.monotonic()
        print("DETERMINE CURRENT LINE CALLED")

        seconds = self.current_song.seconds_played + self.preemptive_early_update_time

        # Find first index where start_time > seconds
        idx = bisect.bisect_right(self.start_times, seconds) - 1

        # Clamp (before first line)
        if idx < 0:
            idx = 0

        # Clamp (after last line)
        if idx >= len(self.lyrics):
            idx = len(self.lyrics) - 1

        if update:
            self.current_index = idx

        return idx

