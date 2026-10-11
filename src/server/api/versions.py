from datetime import datetime
from typing import Any, Protocol

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import board as board_service
from ..services import versions as version_service

router = APIRouter(prefix="/api/boards/{board_id}/versions", tags=["versions"])


class StateSource(Protocol):
    """Where the live board state comes from. The sync gateway will implement this."""

    def snapshot(self, board_id: str) -> tuple[int, list[dict]]: ...
    def replace(self, board_id: str, objects: list[dict]) -> None: ...


class NullStateSource:
    """Placeholder until the sync gateway is merged: an always-empty board."""

    def snapshot(self, board_id: str) -> tuple[int, list[dict]]:
        return 0, []

    def replace(self, board_id: str, objects: list[dict]) -> None:
        pass


_source = NullStateSource()


def get_state_source() -> StateSource:
    return _source


class VersionCreate(BaseModel):
    label: str | None = Field(default=None, max_length=100)


class VersionSummary(BaseModel):
    number: int
    kind: str
    label: str | None
    seq: int
    created_at: datetime

    model_config = {"from_attributes": True}


class VersionDetail(VersionSummary):
    state: list[dict[str, Any]]


def _require_board(db: Session, board_id: str) -> None:
    if board_service.get_board(db, board_id) is None:
        raise HTTPException(status_code=404, detail="Board not found")


@router.post("", response_model=VersionSummary, status_code=201)
def save_named_version(
    board_id: str,
    body: VersionCreate | None = None,
    db: Session = Depends(get_db),
    source: StateSource = Depends(get_state_source),
):
    _require_board(db, board_id)
    seq, objects = source.snapshot(board_id)
    label = body.label if body else None
    return version_service.create_version(db, board_id, "named", seq, objects, label)


@router.get("", response_model=list[VersionSummary])
def list_versions(board_id: str, db: Session = Depends(get_db)):
    _require_board(db, board_id)
    return version_service.list_versions(db, board_id)


@router.get("/{number}", response_model=VersionDetail)
def preview_version(board_id: str, number: int, db: Session = Depends(get_db)):
    _require_board(db, board_id)
    version = version_service.get_version(db, board_id, number)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.post("/{number}/restore", response_model=VersionSummary, status_code=201)
def restore_version(
    board_id: str,
    number: int,
    db: Session = Depends(get_db),
    source: StateSource = Depends(get_state_source),
):
    _require_board(db, board_id)
    seq, _ = source.snapshot(board_id)
    new = version_service.restore_version(db, board_id, number, seq)
    if new is None:
        raise HTTPException(status_code=404, detail="Version not found")
    source.replace(board_id, new.state)  # push the restored content onto the live board
    return new