from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import BoardOp

VALID_OP_TYPES = {"add", "update", "delete"}


def append_op(
    db: Session,
    board_id: str,
    client_id: str,
    op_type: str,
    object_id: str,
    payload: dict | None = None,
) -> BoardOp:
    if op_type not in VALID_OP_TYPES:
        raise ValueError(f"invalid op_type: {op_type}")
    last = db.scalar(
        select(func.max(BoardOp.seq)).where(BoardOp.board_id == board_id)
    )
    op = BoardOp(
        board_id=board_id,
        seq=(last or 0) + 1,
        client_id=client_id,
        op_type=op_type,
        object_id=object_id,
        payload=payload or {},
    )
    db.add(op)
    db.commit()
    db.refresh(op)
    return op


def list_ops(db: Session, board_id: str, after_seq: int = 0) -> list[BoardOp]:
    stmt = (
        select(BoardOp)
        .where(BoardOp.board_id == board_id, BoardOp.seq > after_seq)
        .order_by(BoardOp.seq)
    )
    return list(db.scalars(stmt))


def load_board_state(db: Session, board_id: str) -> dict[str, dict]:
    """Rebuild the board by replaying its ops in order (last write wins per object)."""
    state: dict[str, dict] = {}
    for op in list_ops(db, board_id):
        if op.op_type == "add":
            state[op.object_id] = dict(op.payload)
        elif op.op_type == "update":
            state.setdefault(op.object_id, {}).update(op.payload)
        elif op.op_type == "delete":
            state.pop(op.object_id, None)
    return state
