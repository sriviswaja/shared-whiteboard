from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Board(Base):
    __tablename__ = "boards"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class BoardOp(Base):
    """One edit operation on a board. The (board_id, seq) pair gives each board
    a strict, gap-free ordering that can be replayed to rebuild its state."""

    __tablename__ = "board_ops"
    __table_args__ = (UniqueConstraint("board_id", "seq", name="uq_board_seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    board_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("boards.id"), index=True
    )
    seq: Mapped[int] = mapped_column(Integer)
    client_id: Mapped[str] = mapped_column(String(64))
    op_type: Mapped[str] = mapped_column(String(16))  # add | update | delete
    object_id: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
