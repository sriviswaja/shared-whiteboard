import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.server.db import Base
from src.server.models import Board, BoardOp
from src.server.services.board_ops import append_op, list_ops, load_board_state

BOARD_ID = "a" * 32


def make_session(url):
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)(), engine


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'test.db'}"


def seed_board(db):
    db.add(Board(id=BOARD_ID, name="t"))
    db.commit()


def test_tc_persist_01_state_survives_restart(db_url):
    db, engine = make_session(db_url)
    seed_board(db)
    append_op(db, BOARD_ID, "c1", "add", "o1", {"x": 1, "y": 2})
    append_op(db, BOARD_ID, "c2", "update", "o1", {"x": 5})
    append_op(db, BOARD_ID, "c1", "add", "o2", {"x": 9})
    db.close()
    engine.dispose()  # simulate server restart

    db2, _ = make_session(db_url)
    assert load_board_state(db2, BOARD_ID) == {
        "o1": {"x": 5, "y": 2},
        "o2": {"x": 9},
    }


def test_sequence_numbers_are_gapless_per_board(db_url):
    db, _ = make_session(db_url)
    seed_board(db)
    seqs = [append_op(db, BOARD_ID, "c1", "add", f"o{i}").seq for i in range(5)]
    assert seqs == [1, 2, 3, 4, 5]


def test_delete_removes_object(db_url):
    db, _ = make_session(db_url)
    seed_board(db)
    append_op(db, BOARD_ID, "c1", "add", "o1", {"x": 1})
    append_op(db, BOARD_ID, "c2", "delete", "o1")
    assert load_board_state(db, BOARD_ID) == {}


def test_list_ops_after_seq_supports_resync(db_url):
    db, _ = make_session(db_url)
    seed_board(db)
    for i in range(4):
        append_op(db, BOARD_ID, "c1", "add", f"o{i}")
    assert [op.seq for op in list_ops(db, BOARD_ID, after_seq=2)] == [3, 4]


def test_invalid_op_type_rejected(db_url):
    db, _ = make_session(db_url)
    seed_board(db)
    with pytest.raises(ValueError):
        append_op(db, BOARD_ID, "c1", "explode", "o1")


def test_duplicate_seq_rejected_by_db(db_url):
    db, _ = make_session(db_url)
    seed_board(db)
    append_op(db, BOARD_ID, "c1", "add", "o1")
    db.add(BoardOp(board_id=BOARD_ID, seq=1, client_id="c2",
                   op_type="add", object_id="o2", payload={}))
    with pytest.raises(IntegrityError):
        db.commit()
