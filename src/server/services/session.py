"""Session Service: who is connected to which board.

Covers SRS WB-F-002 (join with a display name), WB-F-003 (participant list),
WB-F-004 (20-participant cap) and WB-SR-006 (membership check).
State is held in memory only and is never written to the database.
"""
import secrets
from dataclasses import dataclass

MAX_PARTICIPANTS = 20
MIN_NAME_LENGTH = 1
MAX_NAME_LENGTH = 30


class SessionError(Exception):
    """Base class for join problems. `code` matches the WebSocket error codes in the SAD."""

    code = 0


class InvalidNameError(SessionError):
    code = 4003


class BoardFullError(SessionError):
    code = 4002


@dataclass(frozen=True)
class Participant:
    client_id: str
    name: str


class SessionService:
    def __init__(self, max_participants: int = MAX_PARTICIPANTS):
        self._max = max_participants
        # board_id -> {client_id: Participant}; a dict keeps join order
        self._boards: dict[str, dict[str, Participant]] = {}

    def join(self, board_id: str, name) -> Participant:
        """Admit a client to a board, or raise InvalidNameError / BoardFullError."""
        name = (name or "").strip()
        if not MIN_NAME_LENGTH <= len(name) <= MAX_NAME_LENGTH:
            raise InvalidNameError(
                f"Display name must be {MIN_NAME_LENGTH} to {MAX_NAME_LENGTH} characters"
            )
        room = self._boards.get(board_id, {})
        if len(room) >= self._max:
            raise BoardFullError("Board is full")
        participant = Participant(client_id=secrets.token_hex(4), name=name)
        self._boards.setdefault(board_id, room)[participant.client_id] = participant
        return participant

    def leave(self, board_id: str, client_id: str) -> bool:
        """Remove a client. Returns True if they were on the board."""
        room = self._boards.get(board_id)
        if not room or client_id not in room:
            return False
        del room[client_id]
        if not room:
            del self._boards[board_id]
        return True

    def participants(self, board_id: str) -> list[Participant]:
        """Current participants in the order they joined."""
        return list(self._boards.get(board_id, {}).values())

    def is_member(self, board_id: str, client_id: str) -> bool:
        """True only if this client is currently on this board."""
        return client_id in self._boards.get(board_id, {})
