import copy
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..models import BoardOp, BoardSnapshot
from .board_ops import apply_ops, list_ops

AUTO_SNAPSHOT_OPS = 100
AUTO_SNAPSHOT_MINUTES = 5
MAX_SNAPSHOTS_PER_BOARD = 50


def _aware(dt: datetime) -> datetime:
    # SQLite returns naive datetimes; treat them as UTC.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def latest_snapshot(db: Session, board_id: str) -> BoardSnapshot | None:
    stmt = (
        select(BoardSnapshot)
        .where(BoardSnapshot.board_id == board_id)
        .order_by(BoardSnapshot.id.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def load_state_with_snapshot(db: Session, board_id: str) -> dict[str, dict]:
    """Start from the latest snapshot and replay only the ops after it."""
    snap = latest_snapshot(db, board_id)
    if snap is None:
        return apply_ops({}, list_ops(db, board_id))
    state = copy.deepcopy(snap.state)
    return apply_ops(state, list_ops(db, board_id, after_seq=snap.seq))


def _current_seq(db: Session, board_id: str) -> int:
    return db.scalar(
        select(func.max(BoardOp.seq)).where(BoardOp.board_id == board_id)
    ) or 0


def create_snapshot(
    db: Session,
    board_id: str,
    author: str,
    name: str | None = None,
    auto: bool = False,
) -> BoardSnapshot:
    snap = BoardSnapshot(
        board_id=board_id,
        seq=_current_seq(db, board_id),
        state=load_state_with_snapshot(db, board_id),
        name=name,
        author=author,
        is_auto=auto,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    prune_snapshots(db, board_id)
    return snap


def prune_snapshots(
    db: Session, board_id: str, keep: int = MAX_SNAPSHOTS_PER_BOARD
) -> int:
    """Keep only the newest `keep` snapshots for a board. Returns how many were removed."""
    keep_ids = list(
        db.scalars(
            select(BoardSnapshot.id)
            .where(BoardSnapshot.board_id == board_id)
            .order_by(BoardSnapshot.id.desc())
            .limit(keep)
        )
    )
    result = db.execute(
        delete(BoardSnapshot).where(
            BoardSnapshot.board_id == board_id,
            BoardSnapshot.id.not_in(keep_ids),
        )
    )
    db.commit()
    return result.rowcount or 0


def should_auto_snapshot(
    db: Session,
    board_id: str,
    now: datetime | None = None,
    max_ops: int = AUTO_SNAPSHOT_OPS,
    max_minutes: int = AUTO_SNAPSHOT_MINUTES,
) -> bool:
    """SRS rule: snapshot after 100 new ops, or 5 minutes of activity since the last one."""
    now = now or datetime.now(timezone.utc)
    snap = latest_snapshot(db, board_id)
    since_seq = snap.seq if snap else 0
    new_ops = list_ops(db, board_id, after_seq=since_seq)
    if not new_ops:
        return False
    if len(new_ops) >= max_ops:
        return True
    reference = _aware(snap.created_at) if snap else _aware(new_ops[0].created_at)
    return now - reference >= timedelta(minutes=max_minutes)
