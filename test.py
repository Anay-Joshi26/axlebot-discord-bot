import asyncio
from concurrent.futures import ThreadPoolExecutor
from axlebot.models.song import Song

def extract_info(url):
    return Song.get_audio_url(url)[-10:]

async def fetch_multiple_urls(urls):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(3) as executor:
        futures = [loop.run_in_executor(executor, extract_info, url) for url in urls]
        results = await asyncio.gather(*futures)
    return results

async def main():
    yt_urls = [
        "https://youtu.be/-JNeBKlG0cI",
        "https://youtu.be/mVEItYOsXjM",
        "https://youtu.be/0JoMqP5UwQ8",
        "https://youtu.be/-JNeBKlG0cI",
        "https://youtu.be/mVEItYOsXjM",
        "https://youtu.be/0JoMqP5UwQ8",
        "https://youtu.be/-JNeBKlG0cI",
        "https://youtu.be/mVEItYOsXjM",
        "https://youtu.be/0JoMqP5UwQ8",
        "https://youtu.be/-JNeBKlG0cI",
        "https://youtu.be/mVEItYOsXjM",
        "https://youtu.be/0JoMqP5UwQ8"
    ]
    results = await fetch_multiple_urls(yt_urls)
    print(results)

if __name__ == '__main__':
    asyncio.run(main())
