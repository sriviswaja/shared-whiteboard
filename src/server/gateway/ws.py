"""WebSocket endpoint: wss://<host>/ws/boards/{board_id}?name=<displayName> (SAD 5.2)."""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..db import get_db
from ..services import board as board_service
from ..services.session import SessionError
from . import persistence
from .hub import Hub

IDLE_TIMEOUT_SECONDS = 120   # clients ping every 30 s, so this means a dead connection

router = APIRouter()
hub = Hub()


def _opener(websocket: WebSocket) -> persistence.DbOpener:
    # Honours test overrides of get_db. Sessions are opened per use, never held open
    # for the whole socket.
    return persistence.opener_from_dependency(
        websocket.app.dependency_overrides.get(get_db, get_db))


def _board_exists(open_db: persistence.DbOpener, board_id: str) -> bool:
    with open_db() as db:
        return board_service.get_board(db, board_id) is not None


def _ensure_room(open_db: persistence.DbOpener, board_id: str) -> None:
    """First connection to a board since the server started: load it and start saving."""
    if board_id in hub.rooms:
        return
    with open_db() as db:
        room = persistence.room_from_db(db, board_id)
    persistence.attach_store(room, open_db)
    hub.rooms[board_id] = room


async def _writer(websocket: WebSocket, conn) -> None:
    while True:
        await websocket.send_json(await conn.outbox.get())


@router.websocket("/ws/boards/{board_id}")
async def board_socket(websocket: WebSocket, board_id: str, name: str = ""):
    await websocket.accept()
    open_db = _opener(websocket)
    if not _board_exists(open_db, board_id):
        await websocket.send_json({"type": "error", "code": 4001, "message": "Board not found"})
        await websocket.close(code=4001)
        return
    _ensure_room(open_db, board_id)
    try:
        conn = hub.connect(board_id, name)
    except SessionError as err:
        await websocket.send_json({"type": "error", "code": err.code, "message": str(err)})
        await websocket.close(code=err.code)
        return

    conn.loop = asyncio.get_running_loop()
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
