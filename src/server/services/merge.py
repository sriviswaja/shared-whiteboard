"""Order-independent merge of board ops (TC-Sync-05, WB-F-022).

Last-write-wins per field. Every op gets a total-order stamp
(timestamp, client_id, seq), so applying the same set of ops in any order,
any number of times, yields the same board.
"""
from datetime import datetime, timezone


def _aware(dt: datetime) -> datetime:
    # SQLite returns naive datetimes; treat them as UTC.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def stamp(op) -> tuple:
    return (_aware(op.created_at), op.client_id, op.seq)


def merge_ops(ops) -> dict[str, dict]:
    created: dict = {}  # object_id -> newest add stamp
    deleted: dict = {}  # object_id -> newest delete stamp
    fields: dict = {}   # object_id -> {field: (stamp, value)}

    for op in ops:
        s = stamp(op)
        oid = op.object_id
        if op.op_type == "add":
            if oid not in created or s > created[oid]:
                created[oid] = s
        elif op.op_type == "delete":
            if oid not in deleted or s > deleted[oid]:
                deleted[oid] = s
        if op.op_type in ("add", "update"):
            slot = fields.setdefault(oid, {})
            for key, value in op.payload.items():
                if key not in slot or s > slot[key][0]:
                    slot[key] = (s, value)

    state: dict[str, dict] = {}
    for oid, c in created.items():
        d = deleted.get(oid)
        if d is not None and d > c:
            continue  # deleted after it was last created
        state[oid] = {
            key: value
            for key, (s, value) in fields.get(oid, {}).items()
            if s >= c  # ignore edits made before the latest (re)creation
        }
    return state
