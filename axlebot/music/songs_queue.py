from models.song import Song
from collections import deque
from typing import List, Union
import random


class SongQueue:
    def __init__(self, server_id : int):
        self.server_id = server_id
        self.queue : List[Song] = []
        self.loop_current = False


    def append(self, song : Song, index = None) -> None:
        if index is not None:
            self.queue.insert(index, song)
            return
        
        self.queue.append(song)

    @property
    def current_song(self) -> Union[Song, None]:
        if len(self.queue) == 0:
            return None
        
        return self.queue[0]
    
    def pop(self, index=0) -> Song:      
        return self.queue.pop(index)
    
    def loop(self) -> None:
        """
        Loops the current song, via a toggle

        Returns the loop status
        """
        if len(self.queue) == 0:
            raise Exception("No song playing")

        self.loop_current = not self.loop_current

        return self.loop_current

    async def repeat(self, num = 1) -> None:
        """
        Repeats the current song 'num' times
        """
        if num < 1 or num > 10:
            raise ValueError("Number of repeats must be between 1 and 10")

        current_song = await self.queue[0].copy()
        for _ in range(num):
            self.queue.insert(1, current_song)
    
    def shuffle(self) -> None:
        """
        Shuffles the queue (except the currently playing song)
        """
        self.queue = self.queue[0]  + random.shuffle(self.queue[1:])

    async def next(self) -> Song:
        """
        Returns the next song in the queue
        """
        if len(self.queue) == 0:
            return None
        
        self.current_song.stop()
        
        if self.loop_current:
            await self.repeat()
            self.pop()

            next_song = self.queue[0]

            if Song.has_audio_url_expired(await next_song.audio_url, next_song.duration):
                await next_song.refresh_audio_url_and_player()

            return next_song

        self.pop()
        
        if len(self.queue) == 0:
            return None
        
        next_song = self.queue[0]
        
        if Song.has_audio_url_expired(await next_song.audio_url, next_song.duration):
            await next_song.refresh_audio_url_and_player()
        
        return next_song
    
    def clear(self) -> None:
        """
        Clears the queue
        """
        self.queue = []
    
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
    

