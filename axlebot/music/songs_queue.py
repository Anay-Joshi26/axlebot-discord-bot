from models.song import Song
from collections import deque
from typing import List, Union
import random
import asyncio


class SongQueue:
    def __init__(self, server_id : int):
        self.server_id = server_id
        self.queue : List[Song] = []
        #self.queue : asyncio.Queue[Song] = asyncio.Queue()
        self.lock = asyncio.Lock()
        self.loop_current = False


    async def append(self, song: Song, index=None) -> None:
        """
        Appends a song to the queue at the end or at a specific index
        """
        async with self.lock:
            if index is not None:
                self.queue.insert(index, song)
            else:
                self.queue.append(song)

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
            return self.queue.pop(index)

    
    def loop(self) -> None:
        """
        Loops the current song, via a toggle

        Returns the loop status
        """
        if len(self.queue) == 0:
            raise Exception("No song playing")

        self.loop_current = not self.loop_current

        self.current_song.is_looping = self.loop_current

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

    async def shuffle(self) -> None:
        """
        Shuffles the queue (except the currently playing song)
        """
        #self.queue = self.queue[0]  + random.shuffle(self.queue[1:])
        async with self.lock:
            subqueue = self.queue[1:]
            random.shuffle(subqueue)
            self.queue = [self.queue[0]] + subqueue

    async def next(self) -> Song:
        """
        Returns the next song in the queue
        """
        if len(self.queue) == 0:
            return None
        
        self.current_song.stop()
        self.current_song.is_first_in_queue = False
        
        if self.loop_current:
            await self.repeat()
            await self.pop()

            next_song = self.queue[0]

            if Song.has_audio_url_expired(await next_song.audio_url, next_song.duration):
                await next_song.refresh_audio_url_and_player()

            next_song.is_looping = self.loop_current # True
            next_song.is_first_in_queue = True
            return next_song

        await self.pop()
        
        if len(self.queue) == 0:
            return None
        
        next_song = self.queue[0]
        
        if Song.has_audio_url_expired(await next_song.audio_url, next_song.duration):
            await next_song.refresh_audio_url_and_player()

        next_song.is_first_in_queue = True
        return next_song
    
    async def clear(self) -> None:
        async with self.lock:
            self.queue.clear()

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
    

