import itertools
import random
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.server.db import Base
from src.server.models import Board
from src.server.services.board_ops import append_op, apply_ops, list_ops
from src.server.services.merge import merge_ops

BASE = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)
FIELDS = ["x", "y", "color"]


def op(seq, client, kind, oid, payload=None, ms=0):
    return SimpleNamespace(
        seq=seq,
        client_id=client,
        op_type=kind,
        object_id=oid,
        payload=payload or {},
        created_at=BASE + timedelta(milliseconds=ms),
    )


def random_ops(rng, n_ops=60, n_clients=4, n_objects=6):
    """Random workload; timestamps cluster in 30 ms so ties are common."""
    ops = []
    for seq in range(1, n_ops + 1):
        kind = rng.choices(["add", "update", "delete"], weights=[3, 5, 2])[0]
        if kind == "add":
            payload = {"x": rng.randrange(100), "y": rng.randrange(100)}
        elif kind == "update":
            payload = {rng.choice(FIELDS): rng.randrange(100)}
        else:
            payload = {}
        ops.append(
            op(seq, f"c{rng.randrange(n_clients)}", kind,
               f"o{rng.randrange(n_objects)}", payload, ms=rng.randrange(30))
        )
    return ops


def assert_all_orders_converge(ops, expected):
    for perm in itertools.permutations(ops):
        assert merge_ops(list(perm)) == expected


# ---- TC-Sync-05: randomized convergence -------------------------------------

@pytest.mark.parametrize("seed", range(20))
def test_tc_sync_05_random_workloads_converge(seed):
    rng = random.Random(seed)
    ops = random_ops(rng)
    expected = merge_ops(ops)
    for _ in range(25):
        shuffled = ops[:]
        rng.shuffle(shuffled)
        assert merge_ops(shuffled) == expected


def test_tc_sync_05_every_client_ends_with_same_board():
    rng = random.Random(42)
    ops = random_ops(rng, n_ops=100, n_clients=5)
    boards = []
    for _ in range(5):  # each simulated client receives ops in its own order
        received = ops[:]
        rng.shuffle(received)
        boards.append(merge_ops(received))
    assert all(b == boards[0] for b in boards)


def test_redelivered_ops_are_idempotent():
    # reconnect/resync may resend ops a client already has
    ops = random_ops(random.Random(7))
    assert merge_ops(ops + ops) == merge_ops(ops)
    assert merge_ops(ops[:30] + ops) == merge_ops(ops)


# ---- WB-F-022: concurrent-edit scenarios (checked in every arrival order) ---

def test_concurrent_edits_to_different_fields_both_survive():
    ops = [
        op(1, "c1", "add", "o1", {"x": 0, "y": 0}, ms=0),
        op(2, "c1", "update", "o1", {"x": 5}, ms=10),
        op(3, "c2", "update", "o1", {"y": 7}, ms=10),
    ]
    assert_all_orders_converge(ops, {"o1": {"x": 5, "y": 7}})


def test_same_field_same_timestamp_higher_client_id_wins():
    ops = [
        op(1, "c1", "add", "o1", {"x": 0, "y": 0}, ms=0),
        op(2, "c1", "update", "o1", {"x": 1}, ms=10),
        op(3, "c2", "update", "o1", {"x": 2}, ms=10),
    ]
    assert_all_orders_converge(ops, {"o1": {"x": 2, "y": 0}})


def test_same_field_later_timestamp_beats_higher_client_id():
    ops = [
        op(1, "c1", "add", "o1", {"x": 0, "y": 0}, ms=0),
        op(2, "c2", "update", "o1", {"x": 2}, ms=10),
        op(3, "c1", "update", "o1", {"x": 1}, ms=20),
    ]
    assert_all_orders_converge(ops, {"o1": {"x": 1, "y": 0}})


def test_delete_after_update_removes_object():
    ops = [
        op(1, "c1", "add", "o1", {"x": 0}, ms=0),
        op(2, "c2", "update", "o1", {"x": 1}, ms=10),
        op(3, "c1", "delete", "o1", ms=20),
    ]
    assert_all_orders_converge(ops, {})


def test_update_after_delete_does_not_resurrect():
    ops = [
        op(1, "c1", "add", "o1", {"x": 0}, ms=0),
        op(2, "c1", "delete", "o1", ms=10),
        op(3, "c2", "update", "o1", {"x": 9}, ms=20),
    ]
    assert_all_orders_converge(ops, {})


def test_re_add_after_delete_starts_fresh():
    ops = [
        op(1, "c1", "add", "o1", {"x": 1, "y": 1}, ms=0),
        op(2, "c1", "delete", "o1", ms=10),
        op(3, "c2", "update", "o1", {"y": 3}, ms=15),
        op(4, "c1", "add", "o1", {"x": 9}, ms=20),
    ]
    assert_all_orders_converge(ops, {"o1": {"x": 9}})


def test_update_for_unknown_object_is_ignored():
    ops = [op(1, "c1", "update", "ghost", {"x": 1}, ms=0)]
    assert merge_ops(ops) == {}


# ---- Why this module exists -------------------------------------------------

def test_seq_order_replay_is_order_dependent():
    a = op(1, "c1", "add", "o1", {"x": 1}, ms=0)
    d = op(2, "c2", "delete", "o1", ms=5)
    assert apply_ops({}, [a, d]) == {}
    assert apply_ops({}, [d, a]) == {"o1": {"x": 1}}  # differs by arrival order
    assert merge_ops([a, d]) == merge_ops([d, a]) == {}


def test_merge_matches_seq_replay_for_in_order_ops(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'merge.db'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    board_id = "c" * 32
    db.add(Board(id=board_id, name="t"))
    db.commit()
    append_op(db, board_id, "c1", "add", "o1", {"x": 1, "y": 1})
    append_op(db, board_id, "c1", "update", "o1", {"x": 2})
    append_op(db, board_id, "c1", "add", "o2", {"x": 9})
    append_op(db, board_id, "c1", "delete", "o2")
    ops = list_ops(db, board_id)
    assert merge_ops(ops) == apply_ops({}, ops) == {"o1": {"x": 2, "y": 1}}
    db.close()
    engine.dispose()
