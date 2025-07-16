import aiohttp
import re
import urllib.parse
from enum import Enum, auto
from utils import clean_song_name

class LyricsStatus(Enum):
    NOT_STARTED = auto()
    FETCHING = auto()
    FETCHED = auto()
    NO_LYRICS_FOUND = auto()
    ERROR = auto()

async def fetch_lyrics(name: str, artist: str, timeout = 5, retry=False) -> dict:
    print(f"Fetching lyrics for: {name} by {artist}")
    clean_name = clean_song_name(name, artist)
    lyrics = None

    print(f"Fetching lyrics for {clean_name} by {artist}")

    URL = f"https://api.lyrics.ovh/v1/{urllib.parse.quote(artist)}/{urllib.parse.quote(clean_name)}"
        
    print(f"Constructed URL: {URL}")
    try:
        timeout = aiohttp.ClientTimeout(total=timeout)  # total time budget
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(URL) as response:
                content_type = response.headers.get("Content-Type", "")

                if response.status == 200:
                    # Expected: valid lyrics data
                    data = await response.json()
                    res_lyrics = data.get('lyrics')
                    if res_lyrics:
                        lyrics = res_lyrics.replace('\n\n', '\n')
                        status = LyricsStatus.FETCHED
                    else:
                        status = LyricsStatus.NO_LYRICS_FOUND

                elif response.status == 404 and "application/json" in content_type:
                    # 404 but still a valid JSON with an error message
                    data = await response.json()
                    if data.get("error") == "No lyrics found":
                        if "-" in name and (retry == False):
                            print("RETRYING with modified artist name")
                            new_artist = name.split("-")[0].strip()
                            return await fetch_lyrics(name, new_artist, timeout=5, retry=True)
                        status = LyricsStatus.NO_LYRICS_FOUND

                    else:
                        status = LyricsStatus.ERROR

                else:
                    # Unexpected response or non-JSON 404
                    status = LyricsStatus.ERROR

                print(f"Lyrics status for {clean_name} by {artist}: {status.name}")

    except Exception as e:
        print("Error fetching lyrics:", e)
        status = LyricsStatus.ERROR
        lyrics = None

    return {
        "name": clean_name,
        "lyrics": lyrics,
        "status": status.name
    }
