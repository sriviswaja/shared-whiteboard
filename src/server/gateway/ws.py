"""WebSocket endpoint: wss://<host>/ws/boards/{board_id}?name=<displayName> (SAD 5.2)."""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..db import get_db
from ..services import board as board_service
from ..services.session import SessionError
from .hub import Hub

IDLE_TIMEOUT_SECONDS = 120   # clients ping every 30 s, so this means a dead connection

router = APIRouter()
hub = Hub()


def _board_exists(websocket: WebSocket, board_id: str) -> bool:
    # Open and close the DB session right here instead of holding it for the whole
    # socket. Honours test overrides of get_db.
    factory = websocket.app.dependency_overrides.get(get_db, get_db)
    gen = factory()
    db = next(gen)
    try:
        return board_service.get_board(db, board_id) is not None
    finally:
        gen.close()


async def _writer(websocket: WebSocket, conn) -> None:
    while True:
        await websocket.send_json(await conn.outbox.get())


@router.websocket("/ws/boards/{board_id}")
async def board_socket(websocket: WebSocket, board_id: str, name: str = ""):
    await websocket.accept()
    if not _board_exists(websocket, board_id):
        await websocket.send_json({"type": "error", "code": 4001, "message": "Board not found"})
        await websocket.close(code=4001)
        return
    try:
        conn = hub.connect(board_id, name)
    except SessionError as err:
        await websocket.send_json({"type": "error", "code": err.code, "message": str(err)})
        await websocket.close(code=err.code)
        return

    writer = asyncio.create_task(_writer(websocket, conn))
    close_code = 1000
    try:
        while True:
            raw = await asyncio.wait_for(websocket.receive_text(), IDLE_TIMEOUT_SECONDS)
            code = hub.handle(conn, raw)
            if code is not None:
                close_code = code
                break
    except (WebSocketDisconnect, asyncio.TimeoutError, RuntimeError):
        pass
    finally:
        hub.disconnect(conn)
        # let already-queued messages (like the last error) go out before closing
        for _ in range(50):
            if conn.outbox.empty():
                break
            await asyncio.sleep(0.01)
        writer.cancel()
        try:
            await websocket.close(code=close_code)
        except RuntimeError:
            pass
