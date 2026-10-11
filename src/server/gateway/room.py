"""Board room: the in-memory, ordered state of one board.

Covers SRS WB-F-020 (broadcast needs one order), WB-F-022 (last-write-wins,
convergence) and WB-F-023 (resume after reconnect). See SAD 4.2, 6.1 and AD-02.

Every accepted operation gets the next `seq` for the board. That single order
is what makes all clients converge. Rules:

* add     - creates an object. Re-using an id (live or deleted) is rejected.
* update  - changes only the properties it names; the later seq wins per
            property, so edits to different properties both survive.
* delete  - marks a tombstone. A late update can never revive the object.
* opId    - client-generated; a repeated opId is acknowledged with the original
            seq and is NOT applied or broadcast again (safe re-send on reconnect).

The room is plain synchronous code, so a seq is assigned and applied atomically
and the unit tests need no event loop. Persistence (feature/persistence) hooks
in through `listeners`: each callback receives every applied `Operation`.
"""
from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Any, Callable

MAX_LOG = 5000        # operations kept for resume; older gaps fall back to full state
MAX_SEEN_OP_IDS = 20000


class OperationRejected(Exception):
    """The operation is valid JSON but cannot be applied (maps to WS error 4004)."""

    code = 4004


@dataclass(frozen=True)
class Operation:
    seq: int
    op_id: str
    client_id: str
    op_type: str          # add | update | delete
    object_id: str
    payload: dict

    def to_message(self) -> dict:
        return {
            "type": "op",
            "seq": self.seq,
            "opId": self.op_id,
            "clientId": self.client_id,
            "opType": self.op_type,
            "objectId": self.object_id,
            "payload": self.payload,
        }


@dataclass
class Element:
    id: str
    type: str
    z: int
    props: dict
    deleted: bool = False
    updated_seq: int = 0
    prop_seq: dict = field(default_factory=dict)   # property -> seq of last write

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "z": self.z, "props": self.props}


class BoardRoom:
    def __init__(self, board_id: str):
        self.board_id = board_id
        self.seq = 0
        self.elements: dict[str, Element] = {}
        self._log: deque[Operation] = deque(maxlen=MAX_LOG)
        self._seen: OrderedDict[str, Operation] = OrderedDict()
        self.listeners: list[Callable[[Operation], None]] = []

    # ---- applying operations -------------------------------------------------

    def apply(self, client_id: str, op_type: str, op_id: str, object_id: str,
              data: dict) -> tuple[Operation, bool]:
        """Apply one validated operation.

        Returns (operation, is_new). is_new is False for a duplicate opId; the
        caller should acknowledge the sender but not broadcast again.
        Raises OperationRejected if the operation cannot be applied.
        """
        previous = self._seen.get(op_id)
        if previous is not None:
            return previous, False

        seq = self.seq + 1  # only committed below, once the operation has applied
        if op_type == "add":
            payload = self._add(object_id, data, seq)
        elif op_type == "update":
            payload = self._update(object_id, data, seq)
        elif op_type == "delete":
            payload = self._delete(object_id, seq)
        else:  # pragma: no cover - validation stops this earlier
            raise OperationRejected(f"Unknown operation {op_type}")

        self.seq = seq
        op = Operation(seq, op_id, client_id, op_type, object_id, payload)
        self._log.append(op)
        self._seen[op_id] = op
        if len(self._seen) > MAX_SEEN_OP_IDS:
            self._seen.popitem(last=False)
        for listener in self.listeners:
            listener(op)
        return op, True

    def _add(self, object_id: str, data: dict, seq: int) -> dict:
        if object_id in self.elements:
            raise OperationRejected("Object id already used")
        element = Element(
            id=object_id,
            type=data["type"],
            z=data.get("z", 0),
            props=dict(data["props"]),
            updated_seq=seq,
            prop_seq={k: seq for k in data["props"]},
        )
        self.elements[object_id] = element
        return {"type": element.type, "z": element.z, "props": dict(element.props)}

    def _update(self, object_id: str, changes: dict, seq: int) -> dict:
        element = self.elements.get(object_id)
        if element is None or element.deleted:
            raise OperationRejected("Object not found")
        changes = dict(changes)
        if "z" in changes:
            element.z = changes["z"]
        for key, value in changes.items():
            if key != "z":
                element.props[key] = value
            element.prop_seq[key] = seq
        element.updated_seq = seq
        return changes

    def _delete(self, object_id: str, seq: int) -> dict:
        element = self.elements.get(object_id)
        if element is None:
            raise OperationRejected("Object not found")
        element.deleted = True  # tombstone: kept so late updates cannot revive it
        element.updated_seq = seq
        return {}

    # ---- reading state -------------------------------------------------------

    def objects(self) -> list[dict]:
        """Live (non-deleted) objects in z-order, then creation order."""
        live = [e for e in self.elements.values() if not e.deleted]
        live.sort(key=lambda e: e.z)
        return [e.to_dict() for e in live]

    def ops_since(self, last_seq: int) -> list[Operation] | None:
        """Operations after `last_seq`, or None when the log cannot cover the gap.

        None means the client must take a full-state welcome instead.
        """
        if last_seq > self.seq or last_seq < 0:
            return None
        if last_seq == self.seq:
            return []
        if not self._log or self._log[0].seq > last_seq + 1:
            return None
        return [op for op in self._log if op.seq > last_seq]

    def load_state(self, objects: list[dict], seq: int) -> None:
        """Start the room from saved state (used when a board is opened after a restart).

        The op log and duplicate-opId memory start empty, so a client resuming from an
        older seq gets a full welcome instead of a replay.
        """
        self.seq = seq
        self.elements = {
            o["id"]: Element(o["id"], o["type"], o.get("z", 0), dict(o["props"]),
                             updated_seq=seq, prop_seq={k: seq for k in o["props"]})
            for o in objects
        }
        self._log.clear()
        self._seen.clear()

    def replace_state(self, objects: list[dict]) -> int:
        """Swap in a whole new board (version restore). Returns the current seq.

        The seq does NOT change: it must keep matching the saved operation log, which a
        restore does not touch. Clients treat `board:reset` as authoritative whatever its
        seq, and the cleared log makes older resumes fall back to a full welcome.
        """
        self.load_state(objects, self.seq)
        return self.seq
