from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import AuditLog, Version

LIST_LIMIT = 50
AUTO_EVERY_OPS = 100
AUTO_EVERY_SECONDS = 300


def should_auto_snapshot(ops_since_last: int, seconds_since_last: float) -> bool:
    """Auto snapshot every 100 ops or 5 minutes, but only if something changed."""
    return ops_since_last > 0 and (
        ops_since_last >= AUTO_EVERY_OPS or seconds_since_last >= AUTO_EVERY_SECONDS
    )


def _next_number(db: Session, board_id: str) -> int:
    current = db.scalar(
        select(func.max(Version.number)).where(Version.board_id == board_id)
    )
    return (current or 0) + 1


def create_version(
    db: Session, board_id: str, kind: str, seq: int, state: list, label: str | None = None
) -> Version:
    version = Version(
        board_id=board_id,
        number=_next_number(db, board_id),
        kind=kind,
        label=label,
        seq=seq,
        state=state,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def list_versions(db: Session, board_id: str, limit: int = LIST_LIMIT) -> list[Version]:
    stmt = (
        select(Version)
        .where(Version.board_id == board_id)
        .order_by(Version.number.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def get_version(db: Session, board_id: str, number: int) -> Version | None:
    return db.scalar(
        select(Version).where(Version.board_id == board_id, Version.number == number)
    )


def restore_version(
    db: Session, board_id: str, number: int, current_seq: int
) -> Version | None:
    """Restoring copies an old version into a NEW version. History is never rewritten."""
    old = get_version(db, board_id, number)
    if old is None:
        return None
    new = create_version(
        db, board_id, "restore", current_seq, old.state,
        label=f"Restored from version {number}",
    )
    db.add(
        AuditLog(
            board_id=board_id, action="restore",
            from_version=number, new_version=new.number,
        )
    )
    db.commit()
    return new


def list_audit(db: Session, board_id: str) -> list[AuditLog]:
    stmt = select(AuditLog).where(AuditLog.board_id == board_id).order_by(AuditLog.id)
    return list(db.scalars(stmt))