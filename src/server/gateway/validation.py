"""Message validation for the Sync Gateway (SRS WB-SR-003, SAD 5.2 and 6.2).

Raises `InvalidMessage` (WS error 4003) or `PayloadTooLarge` (413). The caller
drops the message and keeps the connection open. Text is only ever stored and
relayed as plain strings; the client draws it on a canvas and never injects it
as HTML.
"""
import json
import math

MAX_MESSAGE_BYTES = 64 * 1024
MAX_ID_LENGTH = 64
MAX_STROKE_POINTS = 5000
MAX_TEXT_LENGTH = 2000
MAX_PROPS = 20
OBJECT_TYPES = {"stroke", "rect", "ellipse", "line", "text"}
CLIENT_TYPES = {"op:add", "op:update", "op:delete", "cursor:move", "resume", "ping"}


class InvalidMessage(Exception):
    code = 4003


class PayloadTooLarge(Exception):
    code = 413


def parse(raw: str | bytes) -> dict:
    """Decode a raw frame into a validated message dict."""
    size = len(raw.encode("utf-8")) if isinstance(raw, str) else len(raw)
    if size > MAX_MESSAGE_BYTES:
        raise PayloadTooLarge("Message too large")
    try:
        msg = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise InvalidMessage("Message is not valid JSON")
    if not isinstance(msg, dict):
        raise InvalidMessage("Message must be a JSON object")
    kind = msg.get("type")
    if kind not in CLIENT_TYPES:
        raise InvalidMessage("Unknown message type")
    if kind == "op:add":
        _op_id(msg)
        _object(msg.get("object"))
    elif kind == "op:update":
        _op_id(msg)
        _id(msg.get("objectId"), "objectId")
        _props(msg.get("changes"), allow_z=True, required=True)
    elif kind == "op:delete":
        _op_id(msg)
        _id(msg.get("objectId"), "objectId")
    elif kind == "cursor:move":
        _number(msg.get("x"), "x")
        _number(msg.get("y"), "y")
    elif kind == "resume":
        last = msg.get("lastSeq")
        if not isinstance(last, int) or isinstance(last, bool) or last < 0:
            raise InvalidMessage("lastSeq must be a non-negative integer")
    return msg


def _id(value, name):
    if not isinstance(value, str) or not 1 <= len(value) <= MAX_ID_LENGTH:
        raise InvalidMessage(f"{name} must be a string of 1 to {MAX_ID_LENGTH} characters")


def _op_id(msg):
    _id(msg.get("opId"), "opId")


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise InvalidMessage(f"{name} must be a finite number")


def _object(obj):
    if not isinstance(obj, dict):
        raise InvalidMessage("object must be an object")
    _id(obj.get("id"), "object.id")
    if obj.get("type") not in OBJECT_TYPES:
        raise InvalidMessage("Unknown object type")
    if "z" in obj:
        _number(obj["z"], "z")
        if not isinstance(obj["z"], int):
            raise InvalidMessage("z must be an integer")
    _props(obj.get("props"), allow_z=False, required=True)


def _props(props, allow_z, required):
    if not isinstance(props, dict) or (required and not props) or len(props) > MAX_PROPS:
        raise InvalidMessage("props/changes must be a small non-empty object")
    for key, value in props.items():
        if key == "z":
            if not allow_z or isinstance(value, bool) or not isinstance(value, int):
                raise InvalidMessage("z must be an integer")
            continue
        if key == "points":
            if (not isinstance(value, list) or len(value) > MAX_STROKE_POINTS
                    or not all(isinstance(p, list) and len(p) == 2
                               and all(_finite(c) for c in p) for p in value)):
                raise InvalidMessage("points must be a list of [x, y] numbers")
        elif key == "text":
            if not isinstance(value, str) or len(value) > MAX_TEXT_LENGTH:
                raise InvalidMessage(f"text must be a string up to {MAX_TEXT_LENGTH} characters")
        elif isinstance(value, bool) or isinstance(value, (int, float)):
            if not _finite(value):
                raise InvalidMessage(f"{key} must be finite")
        elif isinstance(value, str):
            if len(value) > 200:
                raise InvalidMessage(f"{key} is too long")
        elif value is not None:
            raise InvalidMessage(f"{key} has an unsupported value")


def _finite(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
