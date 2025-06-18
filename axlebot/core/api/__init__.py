from fastapi import FastAPI, Query, Response, Request
from .routes import router
import aiohttp
from fastapi.responses import StreamingResponse

app = FastAPI(title="Music Bot API")
app.include_router(router, prefix = "/api")

@app.api_route("/proxy_audio", methods=["GET", "HEAD"], description="Proxy audio from a given URL")
async def get_proxy_audio(request: Request, url: str = Query(..., description="The full audio URL (e.g., YouTube stream URL)")):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        )
    }

    print(f"Proxying audio from URL: {url}")

    if request.method == "HEAD":
        # Proxy HEAD request: fetch headers only, no body
        async with aiohttp.ClientSession(timeout=None) as session:
            async with session.head(url, headers=headers) as resp:
                if resp.status != 200:
                    return {"error": f"Failed HEAD request. Status code: {resp.status}"}

                # Return empty response but with headers
                response_to_return = Response()
                response_to_return.status_code = 200
                return response_to_return

    try:
        async def audio_stream():
            async with aiohttp.ClientSession(timeout=None) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        raise Exception(f"Failed to fetch audio. Status code: {resp.status}")
                    async for chunk in resp.content.iter_chunked(8192):
                        yield chunk

        # Optionally pre-fetch headers before streaming
        async with aiohttp.ClientSession(timeout=None) as session:
            async with session.head(url, headers=headers) as head_resp:
                content_type = head_resp.headers.get("Content-Type", "audio/webm")
                #content_length = head_resp.headers.get("Content-Length")

        return StreamingResponse(
            audio_stream(),
            media_type=content_type
        )

    except Exception as e:
        print(f"Error while proxying audio: {e}")
        return {"error": str(e)}
 