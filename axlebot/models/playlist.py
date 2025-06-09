from typing import List, Union
from models.song import Song
import discord
import asyncio

class Playlist:
    def __init__(self, name: str, guild_id: int):
        self.name = name 
        self.songs : List[Song] = []  
        self.total_duration = 0 
        self.guild_id = guild_id
        self.created_at : float = discord.utils.utcnow().timestamp()
        self.song_limit = 30

    def add_song(self, song : Song):
        
        if len(self.songs) >= self.song_limit:
            raise ValueError("You have reached the maximum number of songs allowed in a playlist. Please delete one to add another.")
        
        self.songs.append(song)
        self.total_duration += song.duration

    def remove_song(self, index : int) -> Song:
        self.total_duration -= self.songs[index].duration
        return self.songs.pop(index)
    
    def get_song(self, index: int | str, return_index = False) -> Union[Song, None, int]:
        if isinstance(index, int):
            if 0 <= index < len(self.songs):
                if return_index:
                    return index
                else:
                    return self.songs[index]
            return None
        elif isinstance(index, str):
            # Perform the same logic as get_song_from_name
            index_lower = index.lower()
            for i, song in enumerate(self.songs):
                if song.name.lower() == index_lower:
                    if return_index:
                        return i
                    else:
                        return song
            return None
        else:
            return None
        
    def to_dict(self):
        return {
            "name" : self.name,
            "songs" : [song.to_dict() for song in self.songs],
            "total_duration" : self.total_duration,
            "created_at" : self.created_at
        }
    

    @staticmethod
    async def from_dict(data: dict, guild_id: int):
        print("starting to create playlist")
        try:
            playlist = Playlist(data["name"], guild_id)
            playlist.songs = await asyncio.gather(
            *(Song.from_dict(song) for song in data["songs"]),
            return_exceptions=True
            )
            #playlist.songs = [await Song.from_dict(song) for song in data["songs"]]
            playlist.total_duration = data["total_duration"]
            playlist.created_at = data["created_at"]
            print('pl created, exiting func')
        except Exception as e:
            print(e)
        return playlist