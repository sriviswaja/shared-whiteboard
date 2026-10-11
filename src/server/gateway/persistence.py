"""Board Service persistence: save every applied operation (in the background), load boards on first use.

Covers SRS WB-F-040 (boards persist), WB-F-030 (auto-snapshot) and SAD 4.1.3/6.5.

The stored format is the one in services/board_ops.py: an object is a flat dict, with
`type` and `z` stored next to its properties. The gateway's rooms use a structured
{type, z, props} form, so this module converts at the boundary and nothing else has
to change.
"""
import atexit
import logging
import queue
import threading
from contextlib import contextmanager
from typing import Callable, ContextManager

from sqlalchemy.orm import Session

from ..models import BoardOp
from ..services.snapshots import (
    _current_seq,
    create_snapshot,
    load_state_with_snapshot,
    should_auto_snapshot,
)
from .room import BoardRoom, Operation

log = logging.getLogger(__name__)

DbOpener = Callable[[], ContextManager[Session]]
RESERVED = ("type", "z")


def stored_payload(op: Operation) -> dict:
    """Operation payload in the flat stored format."""
    if op.op_type == "add":
        return {"type": op.payload["type"], "z": op.payload["z"], **op.payload["props"]}
    return op.payload


def objects_from_state(state: dict[str, dict]) -> list[dict]:
    """Stored flat state -> the room's {id, type, z, props} objects."""
    return [
        {"id": oid, "type": flat["type"], "z": flat.get("z", 0),
         "props": {k: v for k, v in flat.items() if k not in RESERVED}}
        for oid, flat in state.items()
        if "type" in flat
    ]


def room_from_db(db: Session, board_id: str) -> BoardRoom:
    """Rebuild a room: latest snapshot plus the operations after it."""
    room = BoardRoom(board_id)
    room.load_state(objects_from_state(load_state_with_snapshot(db, board_id)),
                    _current_seq(db, board_id))
    return room


class _Writer:
    """Background writer: operations are queued by the gateway and saved in batches.

    The gateway handles every socket on one thread, so a blocking database write per
    operation caps the whole server (TC-Perf-02: 150 ops/s made latency climb to seconds).
    Here the gateway only does `queue.put`; one worker thread saves what has queued up in a
    single transaction. Operations carry their own seq, so the stored log always matches
    what clients were sent. A crash can lose the last few milliseconds of operations;
    `flush()` runs at exit so a normal shutdown loses nothing.
    """

    MAX_BATCH = 500

    def __init__(self):
        self._queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def submit(self, open_db: DbOpener, board_id: str, op: Operation) -> None:
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, name="op-writer", daemon=True)
                self._thread.start()
        self._queue.put((open_db, board_id, op))

    def flush(self) -> None:
        """Block until everything queued so far has been written."""
        self._queue.join()

    def _run(self) -> None:
        while True:
            batch = [self._queue.get()]
            while len(batch) < self.MAX_BATCH:
                try:
                    batch.append(self._queue.get_nowait())
                except queue.Empty:
                    break
            try:
                self._write(batch)
            except Exception:  # never take the live board down because the database failed
                log.exception("could not save %d operations", len(batch))
            finally:
                for _ in batch:
                    self._queue.task_done()

    @staticmethod
    def _write(batch) -> None:
        groups: dict = {}
        for open_db, board_id, op in batch:           # keep each board's ops in order
            groups.setdefault((id(open_db), board_id), (open_db, board_id, []))[2].append(op)
        for open_db, board_id, ops in groups.values():
            with open_db() as db:
                db.add_all(
                    BoardOp(board_id=board_id, seq=op.seq, client_id=op.client_id,
                            op_type=op.op_type, object_id=op.object_id,
                            payload=stored_payload(op))
                    for op in ops
                )
                db.commit()
                if should_auto_snapshot(db, board_id):
                    create_snapshot(db, board_id, author="auto", auto=True)


_writer = _Writer()
flush = _writer.flush
atexit.register(flush)


def attach_store(room: BoardRoom, open_db: DbOpener) -> None:
    """Save every operation the room applies (in the background), with auto-snapshots."""
    room.listeners.append(lambda op: _writer.submit(open_db, room.board_id, op))


def opener_from_dependency(factory) -> DbOpener:
    """Turn a FastAPI `get_db`-style generator into `with open_db() as db:`."""

    @contextmanager
    def open_db():
        gen = factory()
        db = next(gen)
        try:
            yield db
        finally:
            gen.close()

    return open_db
