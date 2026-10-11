from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import board as board_service

router = APIRouter(prefix="/api/boards", tags=["boards"])


class BoardCreate(BaseModel):
    name: str = Field(default="Untitled board", min_length=1, max_length=100)


class BoardOut(BaseModel):
    id: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("", response_model=BoardOut, status_code=201)
def create_board(body: BoardCreate | None = None, db: Session = Depends(get_db)):
    body = body or BoardCreate()
    return board_service.create_board(db, body.name)


@router.get("/{board_id}", response_model=BoardOut)
def get_board(board_id: str, db: Session = Depends(get_db)):
    board = board_service.get_board(db, board_id)
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return board