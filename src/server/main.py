from contextlib import asynccontextmanager

from fastapi import FastAPI

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


@app.get("/healthz")
def healthz():
    return {"status": "ok"}

app.include_router(versions.router)