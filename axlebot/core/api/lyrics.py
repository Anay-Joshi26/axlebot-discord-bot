import aiohttp
import re
import urllib.parse
from enum import Enum, auto

class LyricsStatus(Enum):
    NOT_STARTED = auto()
    FETCHING = auto()
    FETCHED = auto()
    NO_LYRICS_FOUND = auto()
    ERROR = auto()

def remove_extra_spaces(text: str) -> str:
    return re.sub(r'\s{2,}', ' ', text)

def clean_song_name(name: str, artist: str) -> str:
    ignore_words = [
        "(official video)", "(official audio)", "(lyrics)", "[official music video]",
        "official", "audio", "video", "lyrics", "music video", "(video)", "(audio)",
        "(lyric video)", "(lyric)", "(music video)", "(official lyric video)",
        "(official lyric)", "()", "~", "( )", "( Music )", "visualiser", "visualizer",
        "(visualiser)", "(visualizer)", "[]", "[ ]", artist, " - ", "ft.", "feat.", "-", "- ", " -",
        ".", "(", ")", "[", "]"
    ]

    for word in ignore_words * 2:
        name = re.sub(re.escape(word), "", name, flags=re.IGNORECASE).strip()

    for token in ["ft.", "feat."]:
        if token in name:
            name = name[:name.index(token)].strip()

    name = remove_extra_spaces(name)

    return name

async def fetch_lyrics(name: str, artist: str) -> dict:
    print(f"Fetching lyrics for: {name} by {artist}")
    clean_name = clean_song_name(name, artist)
    url = f"https://api.lyrics.ovh/v1/{urllib.parse.quote(artist)}/{urllib.parse.quote(clean_name)}"
    status = LyricsStatus.FETCHING
    lyrics = None

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if resp.status == 200:
                    data = await resp.json()
                    lyrics = data.get("lyrics")
                    status = LyricsStatus.FETCHED if lyrics else LyricsStatus.NO_LYRICS_FOUND
                elif resp.status == 404 and "application/json" in content_type:
                    data = await resp.json()
                    if data.get("error") == "No lyrics found":
                        status = LyricsStatus.NO_LYRICS_FOUND
                    else:
                        status = LyricsStatus.ERROR
                else:
                    status = LyricsStatus.ERROR
    except Exception as e:
        print("Error fetching lyrics:", e)
        status = LyricsStatus.ERROR

    return {
        "cleaned_name": clean_name,
        "status": status.value,
        "lyrics": lyrics
    }
