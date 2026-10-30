from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from . import models  # noqa: F401  (registers tables)
from .api import boards, versions
from .gateway import ws
from .db import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Shared Whiteboard", lifespan=lifespan)
app.include_router(boards.router)
app.include_router(ws.router)


CLIENT_PAGE = Path(__file__).resolve().parents[1] / "client" / "index.html"


@app.get("/", include_in_schema=False)
def index():
    """Serve the canvas UI from the same origin as the API and the WebSocket."""
    return FileResponse(CLIENT_PAGE)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}

app.include_router(versions.router)