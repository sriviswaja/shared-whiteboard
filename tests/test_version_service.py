from datetime import datetime, timedelta, timezone

import pytest

from src.server.api.versions import get_db  # noqa: F401  (same override key as conftest)
from src.server.main import app
from src.server.services import versions as vs
from src.server.services.board_ops import append_op
from src.server.services.snapshots import (
    create_snapshot,
    load_state_with_snapshot,
    should_auto_snapshot,
)


@pytest.fixture
def db(client):
    """A DB session on the same in-memory database the API uses."""
    gen = app.dependency_overrides[get_db]()
    session = next(gen)
    yield session
    gen.close()


@pytest.fixture
def board(client):
    return client.post("/api/boards").json()["id"]


def add_ops(db, board, n, start=0):
    for i in range(start, start + n):
        append_op(db, board, "c1", "add", f"o{i}", {"i": i})


# ---- TC-Ver-01: auto snapshot -------------------------------------------------

def test_tc_ver_01_auto_snapshot_after_100_ops(db, board):
    add_ops(db, board, 99)
    assert should_auto_snapshot(db, board) is False
    add_ops(db, board, 1, start=99)
    assert should_auto_snapshot(db, board) is True
    snap = create_snapshot(db, board, author="system", auto=True)
    assert snap.is_auto is True
    assert should_auto_snapshot(db, board) is False  # counter starts again


def test_tc_ver_01_auto_snapshot_after_5_minutes(db, board):
    add_ops(db, board, 1)
    assert should_auto_snapshot(db, board) is False
    later = datetime.now(timezone.utc) + timedelta(minutes=6)
    assert should_auto_snapshot(db, board, now=later) is True


def test_tc_ver_01_no_snapshot_without_changes(db, board):
    later = datetime.now(timezone.utc) + timedelta(hours=1)
    assert should_auto_snapshot(db, board, now=later) is False


# ---- TC-Ver-02: named snapshot ------------------------------------------------

def test_tc_ver_02_named_snapshot(client, db, board):
    add_ops(db, board, 2)
    r = client.post(
        f"/api/boards/{board}/versions",
        json={"name": "before demo", "author": "Viswaja"},
    )
    assert r.status_code == 201
    data = r.json()
    assert (data["name"], data["author"], data["is_auto"], data["seq"]) == (
        "before demo", "Viswaja", False, 2,
    )


def test_tc_ver_02_unknown_board_404(client):
    assert client.post("/api/boards/" + "0" * 32 + "/versions").status_code == 404


# ---- TC-Ver-03: version list --------------------------------------------------

def test_tc_ver_03_list_is_newest_first_and_capped_at_50(client, board):
    for _ in range(55):
        client.post(f"/api/boards/{board}/versions")
    versions = client.get(f"/api/boards/{board}/versions").json()
    ids = [v["id"] for v in versions]
    assert len(ids) == 50
    assert ids == sorted(ids, reverse=True)


def test_tc_ver_03_empty_list(client, board):
    assert client.get(f"/api/boards/{board}/versions").json() == []


# ---- TC-Ver-04: preview -------------------------------------------------------

def test_tc_ver_04_preview_returns_the_saved_state(client, db, board):
    append_op(db, board, "c1", "add", "s1", {"x": 1})
    vid = client.post(f"/api/boards/{board}/versions").json()["id"]
    append_op(db, board, "c1", "update", "s1", {"x": 99})  # board changes afterwards
    r = client.get(f"/api/boards/{board}/versions/{vid}")
    assert r.status_code == 200
    assert r.json()["state"] == {"s1": {"x": 1}}


def test_tc_ver_04_unknown_version_404(client, board):
    assert client.get(f"/api/boards/{board}/versions/9999").status_code == 404


# ---- TC-Ver-05: restore -------------------------------------------------------

def test_tc_ver_05_restore_creates_new_version_and_keeps_history(client, db, board):
    base = f"/api/boards/{board}/versions"
    append_op(db, board, "c1", "add", "s1", {"x": 1})
    a = client.post(base).json()["id"]
    append_op(db, board, "c1", "update", "s1", {"x": 99})
    append_op(db, board, "c1", "add", "s2", {"y": 2})
    b = client.post(base).json()["id"]

    r = client.post(f"{base}/{a}/restore", json={"author": "Viswaja"})
    assert r.status_code == 201
    new_id = r.json()["id"]
    assert r.json()["name"] == f"Restored from version {a}"

    # history is intact: old versions still there, newest first
    assert [v["id"] for v in client.get(base).json()] == [new_id, b, a]
    assert client.get(f"{base}/{b}").json()["state"] == {
        "s1": {"x": 99}, "s2": {"y": 2},
    }
    # the live board now shows the restored content, and new edits build on it
    assert load_state_with_snapshot(db, board) == {"s1": {"x": 1}}
    append_op(db, board, "c1", "update", "s1", {"z": 5})
    assert load_state_with_snapshot(db, board) == {"s1": {"x": 1, "z": 5}}


def test_tc_ver_05_restore_unknown_version_404(client, board):
    assert client.post(f"/api/boards/{board}/versions/9999/restore").status_code == 404


def test_tc_ver_05_restore_writes_audit_log(client, db, board):
    base = f"/api/boards/{board}/versions"
    append_op(db, board, "c1", "add", "s1", {"x": 1})
    a = client.post(base).json()["id"]
    new_id = client.post(f"{base}/{a}/restore").json()["id"]
    log = vs.list_audit(db, board)
    assert len(log) == 1
    assert (log[0].action, log[0].from_version, log[0].new_version) == (
        "restore", a, new_id,
    )