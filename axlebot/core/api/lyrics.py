from syncedlyrics import search as synced_search
import aiohttp
import urllib
from enum import Enum, auto
import re
from utils import clean_song_name

class LyricsStatus(Enum):
    FETCHED = auto()
    NO_LYRICS_FOUND = auto()
    ERROR = auto()  
    NOT_STARTED = auto()
    FETCHING = auto()

def check_synced_lyrics_timing(lyrics: list[tuple[str, int]], duration: float, tolerance: float = 0.35) -> bool:
    """
    Checks if the last timestamp in synced lyrics is within tolerance of the song duration.

    Args:
        lyrics: List of tuples (line, timestamp_ms)
        duration: Song duration in seconds
        tolerance: Allowed proportion difference (default 0.3 = ±30%)

    Returns:
        True if the last line is within tolerance, False otherwise
    """
    if not lyrics:
        return False

    last_timestamp_ms = lyrics[-1][1]
    last_sec = last_timestamp_ms / 1000.0

    min_time = duration * (1 - tolerance)
    max_time = duration * (1 + tolerance)

    print(f"Checking synced lyrics timing: last line at {last_sec}s, song duration {duration}s, allowed range [{min_time}s, {max_time}s]")

    return min_time <= last_sec <= max_time

def merge_close_lines(parsed: list[tuple[str, int]], threshold_ms: int = 3000):
    """
    Merge consecutive LRC lines if they occur within `threshold_ms` of each other.
    Returns a new list of (merged_text, timestamp_ms).
    """
    if not parsed:
        return []

    merged = []
    current_text, current_ts = parsed[0]

    for next_text, next_ts in parsed[1:]:
        # If close enough, merge with a period
        if next_ts - current_ts <= threshold_ms:
            current_text = current_text.rstrip(".") + ". " + next_text
        else:
            merged.append((current_text, current_ts))
            current_text, current_ts = next_text, next_ts

    # Add last merged block
    merged.append((current_text, current_ts))
    return merged


def parse_lrc(lrc_text: str) -> list[tuple[str, int]]:
    pattern = re.compile(r"\[(\d+):(\d+\.\d+|\d+)\](.*)")
    parsed = []

    for line in lrc_text.splitlines():
        matches = re.finditer(pattern, line)
        for match in matches:
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            text = match.group(3).strip()

            # Escape * characters by prepending a backslash
            text = text.replace("*", r"\*")

            timestamp_ms = int((minutes * 60 + seconds) * 1000)
            parsed.append((text, timestamp_ms))

    parsed.sort(key=lambda x: x[1])
    return parsed



async def fetch_lyrics(name: str, artist: str, duration: int, timeout=5, retry=False) -> dict:
    print(f"Fetching lyrics for: {name} by {artist}")
    clean_name = clean_song_name(name, artist)

    # Try synced first
    query = f"{name}".strip()
    synced = True
    providers = ["Musixmatch", "Lrclib", "NetEase"] # in order to try
    for provider in providers:
        print(f"Trying provider: {provider}")
        try:
            print(f"Searching synced lyrics...")
            lrc = synced_search(query, save_path=None, synced_only=True, providers=[provider])
            if lrc is None:
                lrc = synced_search(query, save_path=None, plain_only=True, providers=[provider])
                synced = False
        except Exception as e:
            print("Error calling syncedlyrics:", e)
            lrc = None

        if lrc:
            print("✅ Synced lyrics found (LRC)")
            synced = parse_lrc(lrc)
            print(synced)
            if not check_synced_lyrics_timing(synced, duration):
                print("❌ Synced lyrics timing does not match song duration, trying next provider...")
                continue
            synced = merge_close_lines(synced)
            return {
                "name": name,
                "lyrics": synced,  # <-- NOW A LIST OF (line, timestamp_ms)
                "status": LyricsStatus.FETCHED.name,
                "synced": synced
            }

    print("❌ No synced lyrics found, falling back to plain lyrics...")

    # Fallback: plain lyrics API
    URL = f"https://api.lyrics.ovh/v1/{urllib.parse.quote(artist)}/{urllib.parse.quote(clean_name)}"
    lyrics = None

    try:
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.get(URL) as response:
                content_type = response.headers.get("Content-Type", "")

                if response.status == 200:
                    data = await response.json()
                    res_lyrics = data.get('lyrics')
                    if res_lyrics:
                        lyrics = res_lyrics.replace('\n\n', '\n')
                        status = LyricsStatus.FETCHED
                    else:
                        status = LyricsStatus.NO_LYRICS_FOUND

                elif response.status == 404 and "application/json" in content_type:
                    data = await response.json()
                    if data.get("error") == "No lyrics found":
                        if "-" in name and not retry:
                            new_artist = name.split("-")[0].strip()
                            return await fetch_lyrics(name, new_artist, timeout=5, retry=True)
                        status = LyricsStatus.NO_LYRICS_FOUND
                    else:
                        status = LyricsStatus.ERROR
                else:
                    status = LyricsStatus.ERROR

    except Exception as e:
        print("Error fetching fallback lyrics:", e)
        status = LyricsStatus.ERROR
        lyrics = None

    return {
        "name": clean_name,
        "lyrics": lyrics,  # this remains plain text when fallback occurs
        "status": status.name,
        "synced": False
    }
