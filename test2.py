import aiohttp
from PIL import Image
import io
import asyncio
from youtubesearchpython.__future__ import Search, Playlist, Video, VideosSearch

async def extract_embed_color(thumbnail_url):
    print(f"Extracting color from thumbnail URL: {thumbnail_url}")

    async with aiohttp.ClientSession() as session:
        async with session.get(thumbnail_url) as response:
            response.raise_for_status()
            image_data = await response.read()

    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    image = image.resize((100, 100))

    left, top = 25, 25
    right, bottom = 75, 75

    cropped_image = image.crop((left, top, right, bottom))
    print(f"Cropped image size: {cropped_image.size}")
    print(f"Cropped image mode: {cropped_image.mode}")

    average_color = cropped_image.resize((1, 1)).getpixel((0, 0))
    print(f"Average color: {average_color}")

    hex_color = (average_color[0] << 16) + (average_color[1] << 8) + average_color[2]

    return hex_color

async def search_youtube_video_by_url(url):
    video = await Video.getInfo(url)
    title = video['title']

    if 'secondsText' in video['duration']:
        video_length = int(video['duration']['secondsText'])
    # else:
    #     video_length = Song._time_string_to_seconds(video['duration'])

    return title, video_length

async def run():
    # thumbnail_url = "https://i.scdn.co/image/ab67616d0000b273806c160566580d6335d1f16c"
    # color = await extract_embed_color(thumbnail_url)
    # print(f"Extracted color: {color:#06x}")

    url = 'https://www.youtube.com/watch?v=XXYuWEuKI&pp=ygUWc2F2ZSB5b3VyIHRlYXJzIHdlZWtuZA%3D%3D'
    title, video_length = await search_youtube_video_by_url(url)
    print(f"Title: {title}, Video Length: {video_length} seconds")

if __name__ == "__main__":
    asyncio.run(run())


