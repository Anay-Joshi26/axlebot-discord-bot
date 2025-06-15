import aiohttp
import asyncio
import os
from dotenv import load_dotenv, find_dotenv


load_dotenv(find_dotenv())


async def fetch_data(url: str, params: dict | None = None, timeout: int = 5):
    """
    Wrapper for making GET requests to the provided URL with optional query params.

    :param url: The base URL to fetch data from.
    :param params: Dictionary of query parameters to include in the URL.
    :param timeout: The timeout for the request in seconds.
    :return: A tuple of (status_code, json_data) if successful, or (None, None) on errors.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, timeout=timeout) as response:
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
            return status, None


BASE_URL = f"http://localhost:{os.getenv('FASTAPI_PORT')}"

async def get_youtube_info(query: str) -> dict | None:
    url = f"{BASE_URL}/youtube_info"
    params = {"query": query}
    status, data = await fetch_data(url, params=params)
    if status != 200 or data is None:
        print(f"Failed to get youtube info for query: {query}")
        return None
    return data

async def get_youtube_audio_url(video_url: str) -> str | None:
    url = f"{BASE_URL}/youtube_audio_url"
    params = {"video_url": video_url}
    status, data = await fetch_data(url, params=params)
    if status != 200 or data is None or "audio_url" not in data:
        print(f"Failed to get youtube audio url for video: {video_url}")
        return None
    return data["audio_url"]

async def get_lyrics(name: str, artist: str) -> dict | None:
    url = f"{BASE_URL}/lyrics"
    params = {"name": name, "artist": artist}
    status, data = await fetch_data(url, params=params)
    if status != 200 or data is None:
        print(f"Failed to get lyrics for {name} by {artist}")
        return None
    return data

