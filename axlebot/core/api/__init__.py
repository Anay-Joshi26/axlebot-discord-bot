from fastapi import FastAPI
from .routes import router

app = FastAPI(title="Music Bot API")
app.include_router(router, prefix = "/api")