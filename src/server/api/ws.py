from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import board as board_service
from ..services.room import InvalidOpError
from ..services.session import BoardFullError, InvalidNameError, SessionService
from ..services.sync import SyncHub

router = APIRouter()

_hub = SyncHub()
_sessions = SessionService()


def get_hub() -> SyncHub:
    return _hub


def get_sessions() -> SessionService:
    return _sessions


def _presence(sessions: SessionService, board_id: str) -> dict:
    return {
        "type": "presence",
        "participants": [
            {"client_id": p.client_id, "name": p.name}
            for p in sessions.participants(board_id)
        ],
    }


@router.websocket("/ws/boards/{board_id}")
async def board_socket(
    ws: WebSocket,
    board_id: str,
    name: str = "",
    db: Session = Depends(get_db),
    hub: SyncHub = Depends(get_hub),
    sessions: SessionService = Depends(get_sessions),
):
    # Accept first so browsers can actually read our close codes.
    await ws.accept()
    if board_service.get_board(db, board_id) is None:
        await ws.close(code=4001)  # board not found
        return
    try:
        me = sessions.join(board_id, name)
    except InvalidNameError:
        await ws.close(code=4003)
        return
    except BoardFullError:
        await ws.close(code=4002)
        return

    room = hub.room(board_id)
    hub.connect(board_id, me.client_id, ws)
    try:
        await ws.send_json(
            {
                "type": "welcome",
                "client_id": me.client_id,
                "seq": room.seq,
                "objects": room.snapshot(),
                "participants": _presence(sessions, board_id)["participants"],
            }
        )
        await hub.broadcast(board_id, _presence(sessions, board_id))

        while True:
            try:
                msg = await ws.receive_json()
            except ValueError:  # not valid JSON
                await ws.close(code=4003)
                return
            if not isinstance(msg, dict) or msg.get("type") != "op":
                await ws.close(code=4003)
                return
            try:
                seq = room.apply(msg.get("op"))
            except InvalidOpError:
                await ws.close(code=4003)
                return
            await hub.broadcast(
                board_id,
                {"type": "op", "seq": seq, "client_id": me.client_id, "op": msg["op"]},
            )
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(board_id, me.client_id)
        sessions.leave(board_id, me.client_id)
        await hub.broadcast(board_id, _presence(sessions, board_id))