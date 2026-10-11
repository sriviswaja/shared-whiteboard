"""Sync Gateway hub: connections, rooms and the per-message pipeline.

Pipeline for every incoming frame (SAD 4.1.2): membership check (WB-SR-006),
rate limit (WB-SR-004), size + schema validation (WB-SR-003), then the board
room assigns a seq and the result is broadcast to everyone on the board.

Each connection has an outbound queue drained by one writer task. Broadcasting
only does `put_nowait`, so messages reach every client in seq order even when
several connections are being handled at once.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable

from ..services.session import Participant, SessionService
from . import validation
from .ratelimit import TokenBucket
from .room import BoardRoom, OperationRejected

RATE_LIMIT_PER_SECOND = 60
RATE_LIMIT_CLOSE_AFTER = 120      # dropped messages (within the window below) before closing
RATE_LIMIT_WINDOW = 5.0           # seconds; older drops are forgotten
CURSOR_MIN_INTERVAL = 1 / 20      # about 20 cursor messages per second
OUTBOX_LIMIT = 2000               # slow consumers are disconnected, not buffered forever

CLOSE_RATE_LIMIT = 4290
CLOSE_SLOW_CONSUMER = 4008


@dataclass
class Connection:
    board_id: str
    participant: Participant
    bucket: TokenBucket
    outbox: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(OUTBOX_LIMIT))
    dropped: int = 0
    drop_window_start: float = 0.0
    last_cursor: float = 0.0
    closing: bool = False
    loop: asyncio.AbstractEventLoop | None = None   # set by the WebSocket endpoint

    @property
    def client_id(self) -> str:
        return self.participant.client_id

    def send(self, message: dict) -> None:
        """Queue a message. Safe to call from another event loop's thread (the test client
        runs every socket on its own loop); on a single loop it queues directly."""
        if self.loop is not None and not self._on_own_loop():
            self.loop.call_soon_threadsafe(self._put, message)
        else:
            self._put(message)

    def _on_own_loop(self) -> bool:
        try:
            return asyncio.get_running_loop() is self.loop
        except RuntimeError:
            return False

    def _put(self, message: dict) -> None:
        try:
            self.outbox.put_nowait(message)
        except asyncio.QueueFull:
            self.closing = True


class Hub:
    def __init__(self, sessions: SessionService | None = None,
                 rate: float = RATE_LIMIT_PER_SECOND,
                 clock: Callable[[], float] = time.monotonic,
                 room_factory: Callable[[str], BoardRoom] = BoardRoom):
        self.sessions = sessions or SessionService()
        self.rate = rate
        self.clock = clock
        self.room_factory = room_factory
        self.rooms: dict[str, BoardRoom] = {}
        self.connections: dict[str, dict[str, Connection]] = {}

    def reset(self) -> None:
        """Forget everything (used by tests)."""
        self.__init__(rate=self.rate, clock=self.clock, room_factory=self.room_factory)

    # ---- joining and leaving -------------------------------------------------

    def room(self, board_id: str) -> BoardRoom:
        if board_id not in self.rooms:
            self.rooms[board_id] = self.room_factory(board_id)
        return self.rooms[board_id]

    def connect(self, board_id: str, name) -> Connection:
        """Admit a client. Raises SessionError (4002 full, 4003 bad name)."""
        participant = self.sessions.join(board_id, name)
        conn = Connection(board_id, participant, TokenBucket(self.rate, clock=self.clock))
        self.connections.setdefault(board_id, {})[conn.client_id] = conn
        room = self.room(board_id)
        conn.send(self._welcome(conn, room))
        self._broadcast_presence(board_id)
        return conn

    def disconnect(self, conn: Connection) -> None:
        self.sessions.leave(conn.board_id, conn.client_id)
        peers = self.connections.get(conn.board_id, {})
        peers.pop(conn.client_id, None)
        if not peers:
            self.connections.pop(conn.board_id, None)
        else:
            self._broadcast_presence(conn.board_id)

    # ---- incoming messages ---------------------------------------------------

    def handle(self, conn: Connection, raw: str | bytes) -> int | None:
        """Process one frame. Returns a WebSocket close code if the connection must close."""
        if not self.sessions.is_member(conn.board_id, conn.client_id):
            conn.send(_error(4003, "Not a member of this board"))
            return 4003
        if not conn.bucket.allow():
            now = self.clock()
            if conn.dropped == 0 or now - conn.drop_window_start > RATE_LIMIT_WINDOW:
                conn.dropped, conn.drop_window_start = 0, now   # an old burst is forgiven
            conn.dropped += 1
            if conn.dropped == 1 or conn.dropped % 30 == 0:
                conn.send(_error(CLOSE_RATE_LIMIT, "Rate limit exceeded"))
            return CLOSE_RATE_LIMIT if conn.dropped >= RATE_LIMIT_CLOSE_AFTER else None
        try:
            msg = validation.parse(raw)
        except (validation.InvalidMessage, validation.PayloadTooLarge) as err:
            conn.send(_error(err.code, str(err)))
            return None

        kind = msg["type"]
        room = self.room(conn.board_id)
        if kind == "ping":
            conn.send({"type": "pong"})
        elif kind == "cursor:move":
            self._cursor(conn, msg)
        elif kind == "resume":
            self._resume(conn, room, msg["lastSeq"])
        else:
            self._operation(conn, room, msg)
        return CLOSE_SLOW_CONSUMER if conn.closing else None

    def _operation(self, conn: Connection, room: BoardRoom, msg: dict) -> None:
        kind = msg["type"]
        try:
            if kind == "op:add":
                obj = msg["object"]
                op, is_new = room.apply(conn.client_id, "add", msg["opId"], obj["id"], obj)
            elif kind == "op:update":
                op, is_new = room.apply(conn.client_id, "update", msg["opId"],
                                        msg["objectId"], msg["changes"])
            else:
                op, is_new = room.apply(conn.client_id, "delete", msg["opId"],
                                        msg["objectId"], {})
        except OperationRejected as err:
            conn.send({**_error(err.code, str(err)), "opId": msg["opId"]})
            return
        if is_new:
            self._broadcast(conn.board_id, op.to_message())
        else:
            conn.send(op.to_message())  # duplicate resend: acknowledge only

    def _cursor(self, conn: Connection, msg: dict) -> None:
        now = self.clock()
        if now - conn.last_cursor < CURSOR_MIN_INTERVAL:
            return  # throttled; cursor updates are best-effort and never stored
        conn.last_cursor = now
        self._broadcast(conn.board_id, {
            "type": "cursor", "clientId": conn.client_id,
            "name": conn.participant.name, "x": msg["x"], "y": msg["y"],
        }, skip=conn.client_id)

    def _resume(self, conn: Connection, room: BoardRoom, last_seq: int) -> None:
        missed = room.ops_since(last_seq)
        if missed is None:
            conn.send(self._welcome(conn, room))     # gap too big: full state
        else:
            for op in missed:
                conn.send(op.to_message())

    # ---- outgoing ------------------------------------------------------------

    def board_reset(self, board_id: str, objects: list[dict], reason: str = "restore") -> None:
        """Replace the live board for everyone (used by the Version Service on restore)."""
        seq = self.room(board_id).replace_state(objects)
        self._broadcast(board_id, {"type": "board:reset", "seq": seq,
                                   "objects": objects, "reason": reason})

    def _welcome(self, conn: Connection, room: BoardRoom) -> dict:
        return {
            "type": "welcome", "clientId": conn.client_id, "seq": room.seq,
            "objects": room.objects(), "participants": self._participants(conn.board_id),
        }

    def _participants(self, board_id: str) -> list[dict]:
        return [{"clientId": p.client_id, "name": p.name}
                for p in self.sessions.participants(board_id)]

    def _broadcast_presence(self, board_id: str) -> None:
        self._broadcast(board_id, {"type": "presence",
                                   "participants": self._participants(board_id)})

    def _broadcast(self, board_id: str, message: dict, skip: str | None = None) -> None:
        for client_id, conn in list(self.connections.get(board_id, {}).items()):
            if client_id != skip:
                conn.send(message)


def _error(code: int, message: str) -> dict:
    return {"type": "error", "code": code, "message": message}
