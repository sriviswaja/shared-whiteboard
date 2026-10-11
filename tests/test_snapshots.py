from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.server.db import Base
from src.server.models import Board, BoardSnapshot
from src.server.services.board_ops import append_op, load_board_state
from src.server.services.snapshots import (
    create_snapshot,
    latest_snapshot,
    load_state_with_snapshot,
    prune_snapshots,
    should_auto_snapshot,
)

BOARD_ID = "b" * 32


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'snap.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Board(id=BOARD_ID, name="t"))
    session.commit()
    yield session
    session.close()
    engine.dispose()


def add_ops(db, n, prefix="o"):
    for i in range(n):
        append_op(db, BOARD_ID, "c1", "add", f"{prefix}{i}", {"i": i})


def test_snapshot_plus_tail_equals_full_replay(db):
    add_ops(db, 5)
    create_snapshot(db, BOARD_ID, author="sushir")
    append_op(db, BOARD_ID, "c2", "update", "o1", {"i": 99})
    append_op(db, BOARD_ID, "c2", "delete", "o0")
    assert load_state_with_snapshot(db, BOARD_ID) == load_board_state(db, BOARD_ID)


def test_snapshot_records_seq_and_state(db):
    add_ops(db, 3)
    snap = create_snapshot(db, BOARD_ID, author="sushir", name="before demo")
    assert snap.seq == 3
    assert snap.name == "before demo"
    assert snap.is_auto is False
    assert set(snap.state) == {"o0", "o1", "o2"}


def test_snapshot_on_empty_board(db):
    snap = create_snapshot(db, BOARD_ID, author="sushir")
    assert snap.seq == 0
    assert snap.state == {}


def test_load_does_not_mutate_stored_snapshot(db):
    add_ops(db, 2)
    create_snapshot(db, BOARD_ID, author="sushir")
    append_op(db, BOARD_ID, "c1", "add", "extra", {})
    load_state_with_snapshot(db, BOARD_ID)
    assert "extra" not in latest_snapshot(db, BOARD_ID).state


def test_prune_keeps_newest_50(db):
    for i in range(55):
        create_snapshot(db, BOARD_ID, author="sushir", name=f"v{i}")
    snaps = list(db.scalars(select(BoardSnapshot).where(BoardSnapshot.board_id == BOARD_ID)))
    assert len(snaps) == 50
    names = {s.name for s in snaps}
    assert "v0" not in names and "v54" in names


def test_prune_returns_removed_count(db):
    for i in range(5):
        create_snapshot(db, BOARD_ID, author="sushir")
    assert prune_snapshots(db, BOARD_ID, keep=2) == 3


def test_auto_snapshot_after_100_ops(db):
    add_ops(db, 99)
    assert should_auto_snapshot(db, BOARD_ID) is False
    add_ops(db, 1, prefix="x")
    assert should_auto_snapshot(db, BOARD_ID) is True


def test_auto_snapshot_after_5_minutes_of_activity(db):
    add_ops(db, 3)
    later = datetime.now(timezone.utc) + timedelta(minutes=6)
    assert should_auto_snapshot(db, BOARD_ID) is False
    assert should_auto_snapshot(db, BOARD_ID, now=later) is True


def test_no_auto_snapshot_without_new_ops(db):
    add_ops(db, 3)
    create_snapshot(db, BOARD_ID, author="system", auto=True)
    later = datetime.now(timezone.utc) + timedelta(minutes=30)
    assert should_auto_snapshot(db, BOARD_ID, now=later) is False


def test_counter_resets_after_snapshot(db):
    add_ops(db, 100)
    assert should_auto_snapshot(db, BOARD_ID) is True
    create_snapshot(db, BOARD_ID, author="system", auto=True)
    assert should_auto_snapshot(db, BOARD_ID) is False
