from typing import Any

KINDS = {"add", "update", "delete"}


class InvalidOpError(ValueError):
    pass


class Room:
    """State of one board: ordered operations applied with last-write-wins."""

    def __init__(self) -> None:
        self.seq = 0
        # object id -> {"data": {...}, "deleted": bool}  (deleted = tombstone)
        self.objects: dict[str, dict[str, Any]] = {}

    def apply(self, op: Any) -> int:
        if not isinstance(op, dict):
            raise InvalidOpError("op must be an object")
        kind, oid = op.get("kind"), op.get("id")
        if kind not in KINDS:
            raise InvalidOpError("unknown kind")
        if not isinstance(oid, str) or not 0 < len(oid) <= 64:
            raise InvalidOpError("bad id")
        data = op.get("data", {})
        if not isinstance(data, dict):
            raise InvalidOpError("data must be an object")

        self.seq += 1  # server decides the order
        current = self.objects.get(oid)
        if kind == "add":
            self.objects[oid] = {"data": data, "deleted": False}
        elif kind == "update":
            if current and not current["deleted"]:
                current["data"] = data  # last write wins, whole object
        else:  # delete
            self.objects[oid] = {"data": {}, "deleted": True}
        return self.seq

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {"id": oid, "data": o["data"]}
            for oid, o in self.objects.items()
            if not o["deleted"]
        ]