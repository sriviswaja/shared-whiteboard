"""Board Service persistence: save every applied operation, load boards on first use.

Covers SRS WB-F-040 (boards persist), WB-F-030 (auto-snapshot) and SAD 4.1.3/6.5.

The stored format is the one in services/board_ops.py: an object is a flat dict, with
`type` and `z` stored next to its properties. The gateway's rooms use a structured
{type, z, props} form, so this module converts at the boundary and nothing else has
to change.
"""
import logging
from contextlib import contextmanager
from typing import Callable, ContextManager

from sqlalchemy.orm import Session

from ..services.board_ops import append_op
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


def attach_store(room: BoardRoom, open_db: DbOpener) -> None:
    """Save each applied operation, and take an automatic snapshot when the rule says so."""

    def save(op: Operation) -> None:
        try:
            with open_db() as db:
                row = append_op(db, room.board_id, op.client_id, op.op_type,
                                op.object_id, stored_payload(op))
                if row.seq != op.seq:
                    log.error("seq drift on board %s: room %s, stored %s",
                              room.board_id, op.seq, row.seq)
                if should_auto_snapshot(db, room.board_id):
                    create_snapshot(db, room.board_id, author="auto", auto=True)
        except Exception:  # never take the live board down because the database failed
            log.exception("could not save op %s on board %s", op.seq, room.board_id)

    room.listeners.append(save)


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
