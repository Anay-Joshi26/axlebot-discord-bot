from fastapi import APIRouter, Query
from .youtube import get_youtube_video_info, get_audio_url
from .lyrics import fetch_lyrics

router = APIRouter()

@router.get("/youtube_info")
async def youtube_info(query: str = Query(...), is_yt_url: bool = Query(False)):
    return await get_youtube_video_info(query, is_yt_url=is_yt_url)

@router.get("/youtube_audio_url")
async def youtube_audio_url(video_url: str = Query(...)):
    return await get_audio_url(video_url)

@router.get("/lyrics")
async def lyrics(name: str = Query(...), artist: str = Query(...)):
    return await fetch_lyrics(name, artist)
