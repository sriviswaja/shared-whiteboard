from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..gateway import persistence
from ..gateway.ws import hub
from ..services import board as board_service
from ..services import snapshots as snapshot_service
from ..services import versions as version_service

router = APIRouter(prefix="/api/boards/{board_id}/versions", tags=["versions"])


class VersionCreate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    author: str = Field(default="anonymous", min_length=1, max_length=64)


class RestoreRequest(BaseModel):
    author: str = Field(default="anonymous", min_length=1, max_length=64)


class VersionSummary(BaseModel):
    id: int
    name: str | None
    author: str
    is_auto: bool
    seq: int
    created_at: datetime

    model_config = {"from_attributes": True}


class VersionDetail(VersionSummary):
    state: dict[str, dict[str, Any]]


def _require_board(db: Session, board_id: str) -> None:
    if board_service.get_board(db, board_id) is None:
        raise HTTPException(status_code=404, detail="Board not found")


@router.post("", response_model=VersionSummary, status_code=201)
def save_named_version(
    board_id: str, body: VersionCreate | None = None, db: Session = Depends(get_db)
):
    _require_board(db, board_id)
    persistence.flush()   # include the strokes still waiting in the background writer
    body = body or VersionCreate()
    return snapshot_service.create_snapshot(
        db, board_id, author=body.author, name=body.name, auto=False
    )


@router.get("", response_model=list[VersionSummary])
def list_versions(board_id: str, db: Session = Depends(get_db)):
    _require_board(db, board_id)
    return version_service.list_versions(db, board_id)


@router.get("/{version_id}", response_model=VersionDetail)
def preview_version(board_id: str, version_id: int, db: Session = Depends(get_db)):
    _require_board(db, board_id)
    version = version_service.get_version(db, board_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


@router.post("/{version_id}/restore", response_model=VersionSummary, status_code=201)
def restore_version(
    board_id: str,
    version_id: int,
    body: RestoreRequest | None = None,
    db: Session = Depends(get_db),
):
    _require_board(db, board_id)
    persistence.flush()
    author = (body or RestoreRequest()).author
    new = version_service.restore_version(db, board_id, version_id, author)
    if new is None:
        raise HTTPException(status_code=404, detail="Version not found")
    if board_id in hub.rooms:
        # WB-F-034: everyone connected to the board sees the restored version at once
        hub.board_reset(board_id, persistence.objects_from_state(new.state), reason="restore")
    return new