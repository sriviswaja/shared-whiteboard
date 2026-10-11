import copy

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuditLog, BoardSnapshot
from .snapshots import MAX_SNAPSHOTS_PER_BOARD, _current_seq, prune_snapshots


def list_versions(db: Session, board_id: str) -> list[BoardSnapshot]:
    """Newest first. Create/prune (and the 50 cap) live in snapshots.py."""
    stmt = (
        select(BoardSnapshot)
        .where(BoardSnapshot.board_id == board_id)
        .order_by(BoardSnapshot.id.desc())
        .limit(MAX_SNAPSHOTS_PER_BOARD)
    )
    return list(db.scalars(stmt))


def get_version(db: Session, board_id: str, version_id: int) -> BoardSnapshot | None:
    return db.scalar(
        select(BoardSnapshot).where(
            BoardSnapshot.board_id == board_id, BoardSnapshot.id == version_id
        )
    )


def restore_version(
    db: Session, board_id: str, version_id: int, author: str
) -> BoardSnapshot | None:
    """Restore = save a NEW snapshot holding the old state. History is never rewritten.

    snapshots.load_state_with_snapshot always starts from the latest snapshot, so the
    restored state becomes the live board automatically.
    """
    old = get_version(db, board_id, version_id)
    if old is None:
        return None
    new = BoardSnapshot(
        board_id=board_id,
        seq=_current_seq(db, board_id),
        state=copy.deepcopy(old.state),
        name=f"Restored from version {old.id}",
        author=author,
        is_auto=False,
    )
    db.add(new)
    db.flush()  # assigns new.id so the audit row can point at it
    db.add(
        AuditLog(
            board_id=board_id,
            action="restore",
            from_version=old.id,
            new_version=new.id,
        )
    )
    db.commit()
    db.refresh(new)
    prune_snapshots(db, board_id)
    return new


def list_audit(db: Session, board_id: str) -> list[AuditLog]:
    stmt = select(AuditLog).where(AuditLog.board_id == board_id).order_by(AuditLog.id)
    return list(db.scalars(stmt))