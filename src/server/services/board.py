import secrets

from sqlalchemy.orm import Session

from ..models import Board


def new_board_id() -> str:
    # 16 random bytes = 128 bits, shown as 32 hex chars.
    # The board link is the only access control, so it must be unguessable.
    return secrets.token_hex(16)


def create_board(db: Session, name: str) -> Board:
    board = Board(id=new_board_id(), name=name)
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


def get_board(db: Session, board_id: str) -> Board | None:
    return db.get(Board, board_id)