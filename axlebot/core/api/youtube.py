import asyncio
import yt_dlp

yt_dl = yt_dlp.YoutubeDL({
    "quiet": True,
    "format": "bestaudio/best",
    "no_warnings": True,
    "skip_download": True,
})

async def get_youtube_video_info(query: str, is_yt_url = False) -> dict | None:
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(
            None, lambda: yt_dl.extract_info(f"{query if is_yt_url else f'ytsearch1:{query}'}", download=False)
    )
    if not is_yt_url and (not data or "entries" not in data or len(data["entries"]) == 0):
        return {"error": f"No results found for query: {query}"}
    if data is None:
        print(f"Failed to fetch song info for query: {query}")
        return {"error": f"Failed to fetch song info for query: {query}"}

    return data["entries"][0] if not is_yt_url else data

async def get_audio_url(video_url: str) -> dict:
    loop = asyncio.get_running_loop()
    info = await loop.run_in_executor(
        None, lambda: yt_dl.extract_info(video_url, download=False)
    )
    return {"audio_url": info.get("url")}
