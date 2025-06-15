import asyncio
import yt_dlp
from pprint import pprint

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

    def sorted_audio_formats(info_dict):
        formats = info_dict.get("formats", [])
        # Filter audio-only formats with a valid URL
        audio_formats = [
            f for f in formats
            if f.get("vcodec") == "none" and f.get("acodec") != "none" and f.get("url") and f.get("abr") is not None
        ]

        if not audio_formats:
            return [info_dict['url']] if "url" in info_dict else None
        # Sort by audio bitrate (abr), descending
        audio_formats.sort(key=lambda f: 0 if f.get("abr", 0) is None else f.get("abr", 0), reverse=True)
        audio_formats = [f.get("url") for f in audio_formats]
        return audio_formats if audio_formats else None

    best_audios = sorted_audio_formats(info)

    return {
        "audio_urls": best_audios if best_audios else None,
    }

