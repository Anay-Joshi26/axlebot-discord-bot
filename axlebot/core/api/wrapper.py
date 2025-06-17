import aiohttp
import asyncio
import os
from dotenv import load_dotenv, find_dotenv
from typing import Union, List


load_dotenv(find_dotenv())


async def fetch_data(url: str, params: dict | None = None, timeout: int = 20):
    """
    Wrapper for making GET requests to the provided URL with optional query params.

    :param url: The base URL to fetch data from.
    :param params: Dictionary of query parameters to include in the URL.
    :param timeout: The timeout for the request in seconds.
    :return: A tuple of (status_code, json_data) if successful, or (None, None) on errors.
    """
    timeout = aiohttp.ClientTimeout(total=timeout) # total time budget
    async with aiohttp.ClientSession(timeout=timeout) as session:  
        try:
            async with session.get(url, params=params, headers = {"Accept": "application/json"}) as response:
                status = response.status
                json_data = await response.json()
                return status, json_data
        except aiohttp.ClientError as e:
            print(f"Request failed: {e}")
            return None, None
        except asyncio.TimeoutError:
            print("Request timed out")
            return None, None
        except aiohttp.ContentTypeError:
            print("Response is not valid JSON")
            return None, None

https = True if os.getenv('FASTAPI_HTTPS') == 'true' else False
if https:
    BASE_URL = f"{os.getenv('FASTAPI_HOST')}/api"
else:
    BASE_URL = f"{os.getenv('FASTAPI_HOST')}:{os.getenv('FASTAPI_PORT')}/api"

print(f"Using API base URL: {BASE_URL}")

async def get_youtube_info(query: str, is_yt_url = False) -> dict | None:
    url = f"{BASE_URL}/youtube_info"
    params = {"query": query, "is_yt_url": "true" if is_yt_url else "false"}
    status, data = await fetch_data(url, params=params)
    if status != 200 or data is None:
        print(f"Failed to get youtube info for query: {query}")
        return None
    return data

async def get_youtube_audio_url(video_url: str) -> List[str]:
    url = f"{BASE_URL}/youtube_audio_url"
    params = {"video_url": video_url}
    status, data = await fetch_data(url, params=params)
    if status != 200 or data is None or "audio_urls" not in data:
        print(f"Failed to get youtube audio url for video: {video_url}")
        return None
    return data["audio_urls"]

async def get_lyrics(name: str, artist: str) -> dict | None:
    url = f"{BASE_URL}/lyrics"
    params = {"name": name, "artist": artist}
    status, data = await fetch_data(url, params=params)
    if status != 200 or data is None:
        print(f"Failed to get lyrics for {name} by {artist}")
        return None
    return data
