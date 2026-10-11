from fastapi import WebSocket

from .room import Room


class SyncHub:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}
        self.conns: dict[str, dict[str, WebSocket]] = {}

    def room(self, board_id: str) -> Room:
        return self.rooms.setdefault(board_id, Room())

    def connect(self, board_id: str, client_id: str, ws: WebSocket) -> None:
        self.conns.setdefault(board_id, {})[client_id] = ws

    def disconnect(self, board_id: str, client_id: str) -> None:
        self.conns.get(board_id, {}).pop(client_id, None)

    async def broadcast(self, board_id: str, message: dict) -> None:
        for ws in list(self.conns.get(board_id, {}).values()):
            try:
                await ws.send_json(message)
            except Exception:
                pass  # that client's own handler will clean it up