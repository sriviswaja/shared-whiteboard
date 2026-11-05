import secrets

import pytest

from src.server.db import get_db
from src.server.main import app
from src.server.services import versions as vs
from src.server.services.board import new_board_id
from src.server.services.board_ops import append_op


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


# ---- TC-Sec-02: unguessable board IDs (WB-SR-002) -----------------------------

def test_tc_sec_02_generated_ids_are_long_and_unique():
    ids = [new_board_id() for _ in range(10_000)]
    assert len(set(ids)) == 10_000  # no duplicates
    for board_id in ids:
        assert len(board_id) >= 22  # STP: at least 22 URL-safe characters
        assert len(board_id) * 4 >= 128  # 32 hex characters = 128 bits
        int(board_id, 16)  # hex only


def test_tc_sec_02_random_ids_never_find_a_board(client, board):
    # A real board exists, so a guess must not hit it by accident.
    for _ in range(1_000):
        guess = secrets.token_hex(16)
        assert guess != board
        assert client.get(f"/api/boards/{guess}").status_code == 404


@pytest.mark.parametrize("bad_id", ["1", "admin", "0" * 31, "../etc/passwd", "%00"])
def test_tc_sec_02_malformed_ids_are_404_not_errors(client, bad_id):
    assert client.get(f"/api/boards/{bad_id}").status_code == 404


# ---- TC-Sec-05: append-only history (WB-SR-005) -------------------------------

def test_tc_sec_05_restores_never_lose_a_snapshot(client, db, board):
    base = f"/api/boards/{board}/versions"
    append_op(db, board, "c1", "add", "s1", {"x": 1})
    a = client.post(base).json()["id"]
    append_op(db, board, "c1", "update", "s1", {"x": 2})
    b = client.post(base).json()["id"]

    first = client.post(f"{base}/{a}/restore", json={"author": "Asha"}).json()["id"]
    second = client.post(f"{base}/{b}/restore", json={"author": "Ben"}).json()["id"]

    ids = [v["id"] for v in client.get(base).json()]
    assert ids == [second, first, b, a]  # all four exist, nothing lost
    assert client.get(f"{base}/{a}").json()["state"] == {"s1": {"x": 1}}
    assert client.get(f"{base}/{b}").json()["state"] == {"s1": {"x": 2}}


def test_tc_sec_05_versions_cannot_be_deleted_through_the_api(client, db, board):
    base = f"/api/boards/{board}/versions"
    append_op(db, board, "c1", "add", "s1", {"x": 1})
    vid = client.post(base).json()["id"]

    for path in (f"{base}/{vid}", base, f"{base}/{vid}/restore"):
        assert client.delete(path).status_code in (404, 405)
    assert client.get(f"{base}/{vid}").status_code == 200  # still there


def test_tc_sec_05_each_restore_has_an_audit_entry(client, db, board):
    base = f"/api/boards/{board}/versions"
    append_op(db, board, "c1", "add", "s1", {"x": 1})
    a = client.post(base).json()["id"]
    append_op(db, board, "c1", "update", "s1", {"x": 2})
    b = client.post(base).json()["id"]
    client.post(f"{base}/{a}/restore", json={"author": "Asha"})
    client.post(f"{base}/{b}/restore", json={"author": "Ben"})

    log = vs.list_audit(db, board)
    assert [(e.author, e.from_version) for e in log] == [("Asha", a), ("Ben", b)]
    for entry in log:
        assert entry.action == "restore"
        assert entry.created_at is not None  # when
        assert entry.new_version is not None