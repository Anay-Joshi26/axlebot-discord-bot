from models.song import Song
from collections import deque
from typing import List, Union
import random
import asyncio
from utils.message_crafter import craft_queue
import discord


class SongQueue:
    def __init__(self, client):
        self.client = client
        self.queue : List[Song] = []
        #self.queue : asyncio.Queue[Song] = asyncio.Queue()
        self.lock = asyncio.Lock()
        self.loop_current = False
        self.NUM_OF_AUTOPLAY_SONGS_TO_HOLD = 5
        self.auto_play_queue : List[Song] = []
        self.last_seed_songs : set[str] = set()  # To keep track of the last seed songs used for recommendations
        self._auto_play_update_task = None

    async def append(self, song: Song, index=None, update_auto_play=True) -> None:
        """
        Appends a song to the queue at the end or at a specific index
        """
        async with self.lock:
            if index is not None:
                self.queue.insert(index, song)
            else:
                self.queue.append(song)

            if self.client.server_config.auto_play and update_auto_play:
                # Cancel existing debounce task if running
                if self._auto_play_update_task and not self._auto_play_update_task.done():
                    self._auto_play_update_task.cancel()

                # Start new debounce task
                self._auto_play_update_task = asyncio.create_task(self._debounced_update_auto_play())

        self.update_live_queue_message()

    async def _debounced_update_auto_play(self, timeout=8):
        try:
            await asyncio.sleep(timeout)  # Debounce delay
            await self.update_auto_play_songs()
        except asyncio.CancelledError:
            pass  # Ignore if cancelled

    def update_live_queue_message(self):
        """
        Updates the live queue message with the current queue.
        This is useful for live updates to the queue.
        """
        if hasattr(self.client, 'live_queue_message'):
            async def updater():
                try:
                    current_page = 0
                    if hasattr(self.client, "live_queue_current_page") and self.client.live_queue_current_page:
                        current_page = self.client.live_queue_current_page    

                    embeds, view = craft_queue(self.client, num=None, live=True, starting_page=current_page)
                    await self.client.live_queue_message.edit(
                        embed=embeds[view.current_page], view=view
                    )
                except discord.NotFound:
                    print("Live queue message no longer exists. Removing reference.")
                    delattr(self.client, 'live_queue_message')
                except Exception as e:
                    print(f"Error updating live queue message: {e}")

            asyncio.create_task(updater())
            
    async def update_auto_play_songs(self, num_of_seed_tracks : int = 5, manual_seed_tracks: List[Song] = None, delay_execution=None) -> None:
        """
        Updates the auto play songs in the queue based on the current queue.
        Spotify only supports up to 5 seed tracks, so we will use that as the default.
        """
        async with self.lock:
            if delay_execution is not None and isinstance(delay_execution, (int, float)) and delay_execution > 0:
                await asyncio.sleep(delay_execution)
            seed_songs = self.queue[:num_of_seed_tracks] + self.auto_play_queue[:num_of_seed_tracks - len(self.queue[:num_of_seed_tracks])]
            seed_songs_set = set(song.lavalink_track_id for song in seed_songs)
            if seed_songs_set == self.last_seed_songs:
                print("No change in seed songs, skipping auto play update.")
                if not manual_seed_tracks: return
            
            print(f"Updating auto play songs with seed songs: {seed_songs_set}")
            
            self.last_seed_songs = seed_songs_set
            num_to_add = self.NUM_OF_AUTOPLAY_SONGS_TO_HOLD - len(self.auto_play_queue)
            if manual_seed_tracks is not None:
                seed_songs = manual_seed_tracks
            recommendations = await Song.get_song_recommendations(seed_songs, limit=self.NUM_OF_AUTOPLAY_SONGS_TO_HOLD if num_to_add == 0 else num_to_add, set_auto_play=True)
            
            if num_to_add == 0:
                self.auto_play_queue = recommendations
            else:
                for song in recommendations[:num_to_add]:
                    self.auto_play_queue.append(song)
            
            self.update_live_queue_message()

    @property
    def current_song(self) -> Union[Song, None]:
        if len(self.queue) == 0:
            return None
        
        return self.queue[0]
    
    async def pop(self, index=0) -> Song:
        """
        Pops a song from the queue at the specified index (default is 0)
        """
        async with self.lock:
            popped = self.queue.pop(index)
            self.update_live_queue_message()
            return popped

    
    def loop(self) -> None:
        """
        Loops the current song, via a toggle

        Returns the loop status
        """
        if len(self.queue) == 0:
            raise Exception("No song playing")

        self.loop_current = not self.loop_current

        self.current_song.is_looping = self.loop_current

        self.update_live_queue_message()
        return self.loop_current

    async def repeat(self, num=1) -> None:
        """
        Repeats the current song a specified number of times (default is 1)
        """
        if num < 1 or num > 20:
            raise ValueError("Number of repeats must be between 1 and 20")
        async with self.lock:
            current_song = await self.queue[0].copy()
            for _ in range(num):
                self.queue.insert(1, current_song)

        self.update_live_queue_message()

    
    async def move(self, song_in_question: int, move_to: int) -> None:
        """
        Moves a song in the queue to a different position
        """
        async with self.lock:
            if song_in_question == 1:
                raise ValueError("You can't move the current song")
            
            if song_in_question < 2 or song_in_question >= len(self.queue) + 1:
                raise ValueError("You did not select a valid song from the queue")

            if move_to == 1:
                raise ValueError("You can't move a song to the current song")
            
            if move_to < 2 or move_to >= len(self.queue) + 1:
                raise ValueError("You did not select a valid position to move the song to")

            self.queue.insert(move_to-1, self.queue.pop(song_in_question-1))

        self.update_live_queue_message()

    async def shuffle(self) -> None:
        """
        Shuffles the queue (except the currently playing song)
        """
        #self.queue = self.queue[0]  + random.shuffle(self.queue[1:])
        async with self.lock:
            subqueue = self.queue[1:]
            random.shuffle(subqueue)
            self.queue = [self.queue[0]] + subqueue

        self.update_live_queue_message()

    async def next(self) -> Song:
        """
        Returns the next song in the queue
        """
        if len(self.queue) == 0 and not self.client.server_config.auto_play:
            self.update_live_queue_message()
            return None
        
        if self.current_song is None:
            return None
        
        self.current_song.stop()
        self.current_song.is_first_in_queue = False
        
        if self.loop_current:
            await self.repeat()
            await self.pop()

            next_song = self.queue[0]

            # if next_song._audio_url is not None and Song.has_audio_url_expired(next_song._audio_url, next_song.duration):
            #     await next_song.refresh_audio_url_and_player()

            next_song.is_looping = self.loop_current # True
            next_song.is_first_in_queue = True
            self.update_live_queue_message()
            return next_song

        popped = await self.pop()
        
        if len(self.queue) == 0:
            if not self.client.server_config.auto_play:
                self.update_live_queue_message()
                return None

            if len(self.auto_play_queue) == 0:
                print("No songs in auto play queue, updating auto play songs")
                await self.update_auto_play_songs(manual_seed_tracks=[popped])
            next_song = self.auto_play_queue.pop(0)
            self.queue.append(next_song)
            next_song.is_first_in_queue = True
            # Cancel any previous debounced update
            if self._auto_play_update_task and not self._auto_play_update_task.done():
                self._auto_play_update_task.cancel()

            # Start new debounce task
            self._auto_play_update_task = asyncio.create_task(self._debounced_update_auto_play())

            self.update_live_queue_message()
            return next_song
            
        
        next_song = self.queue[0]
        
        # if Song.has_audio_url_expired(await next_song.audio_url, next_song.duration):
        #     await next_song.refresh_audio_url_and_player()

        next_song.is_first_in_queue = True
        self.update_live_queue_message()
        return next_song
    
    async def clear(self) -> None:
        async with self.lock:
            self.queue.clear()
        self.update_live_queue_message()

    def __len__(self) -> int:
        """
        Dunder method to return the length of the queue
        """
        return len(self.queue)  
    
    def __getitem__(self, index) -> Song:
        """
        Dunder method to get the item at the index
        """
        return self.queue[index]
    

