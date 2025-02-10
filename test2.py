import asyncio
from yt_dlp import YoutubeDL
import random
import time

yt_dl_options = {
    "format": "bestaudio/best",
    "quiet": True,
    "extractaudio": True,
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp4",
            "preferredquality": "320",
        }
    ]
}

ytdl = YoutubeDL(yt_dl_options)

async def get_audio_url_async(url, retries=3, timeout=10):
    """Fetches audio URL with retries and a timeout."""
    loop = asyncio.get_event_loop()
    for attempt in range(retries):
        try:
            # Running yt-dlp extract info inside the executor to avoid blocking event loop
            info = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False)),
                timeout=timeout
            )
            return info['url']
        
        except asyncio.TimeoutError:
            print(f"Timeout occurred while fetching {url}. Retrying...")
        except Exception as e:
            print(f"Error occurred for {url}: {e}")

        # Exponential backoff before retrying
        await asyncio.sleep(random.uniform(1, 2 ** attempt))  # Exponential backoff

    print(f"Failed to fetch {url} after {retries} attempts.")
    return None

async def get_multiple_audio_urls(urls):
    """Fetch multiple audio URLs concurrently."""
    tasks = [get_audio_url_async(url) for url in urls]

    try:
        # Use asyncio.gather with a timeout to wait for all tasks to finish
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                print(f"An error occurred: {result}")
            elif result is None:
                print("Some task failed or was cancelled.")
            else:
                print(f"Successfully fetched URL: {result[:50]}")
    except asyncio.TimeoutError:
        print("Timed out waiting for all tasks to complete.")
    except Exception as e:
        print(f"Unexpected error: {e}")

# urls = [
#     "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
#     "https://www.youtube.com/watch?v=3JZ_D3ELwOQ",
#     "https://www.youtube.com/watch?v=fJ9rUzIMcZQ",
#     "https://www.youtube.com/watch?v=2Vv-BfVoq4g",
#     "https://www.youtube.com/watch?v=kJQP7kiw5Fk",
#     "https://www.youtube.com/watch?v=RgKAFK5djSk",
#     "https://www.youtube.com/watch?v=YykjpeuMNEk",
#     "https://www.youtube.com/watch?v=tt2k8PGm-TI",
#     "https://www.youtube.com/watch?v=6Mgqbai3fKo",
#     "https://www.youtube.com/watch?v=UceaB4D0jpo",
#     "https://www.youtube.com/watch?v=LsoLEjrDogU",
#     "https://www.youtube.com/watch?v=PMivT7MJ41M",
#     "https://www.youtube.com/watch?v=SlPhMPnQ58k",
#     "https://www.youtube.com/watch?v=apJ1T_olYjQ",
#     "https://www.youtube.com/watch?v=hT_nvWreIhg",
#     "https://www.youtube.com/watch?v=OPf0YbXqDm0",
#     "https://www.youtube.com/watch?v=nfWlot6h_JM",
#     "https://www.youtube.com/watch?v=E07s5ZYygMg",
#     "https://www.youtube.com/watch?v=LpYgI1LLNVM",
#     "https://www.youtube.com/watch?v=KtlgYxa6BMU"
# ]

urls = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=3JZ_D3ELwOQ",
    "https://www.youtube.com/watch?v=LsoLEjrDogU",
    "https://www.youtube.com/watch?v=E07s5ZYygMg",
    "https://www.youtube.com/watch?v=KtlgYxa6BMU",
    "https://www.youtube.com/watch?v=PMivT7MJ41M",
    "https://www.youtube.com/watch?v=OPf0YbXqDm0",
    "https://www.youtube.com/watch?v=kJQP7kiw5Fk"
]


asyncio.run(get_multiple_audio_urls(urls))