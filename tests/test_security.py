"""Security test cases from the STP: TC-Sec-02 (WB-SR-002) and TC-Sec-05 (WB-SR-005)."""
import re
import secrets

import pytest

from src.server.api.versions import get_db  # noqa: F401  (same override key as conftest)
from src.server.main import app
from src.server.services import board as board_service
from src.server.services import versions as vs
from src.server.services.board_ops import append_op

MIN_ID_BITS = 128


@pytest.fixture
def db(client):
    """A DB session on the same in-memory database the API uses."""
    gen = app.dependency_overrides[get_db]()
    session = next(gen)
    yield session
    gen.close()


# ---- TC-Sec-02: unguessable board IDs (WB-SR-002) ------------------------------

def test_tc_sec_02_10000_ids_are_unique_and_at_least_128_bits():
    ids = [board_service.new_board_id() for _ in range(10_000)]
    assert len(set(ids)) == 10_000                              # no duplicates
    for board_id in ids:
        assert re.fullmatch(r"[0-9a-f]{32}", board_id)          # 32 hex chars = 128 bits
        assert len(board_id) * 4 >= MIN_ID_BITS
        assert len(board_id) >= 22                              # STP: >= 22 URL-safe characters


def test_tc_sec_02_ids_are_not_sequential_or_sorted():
    ids = [board_service.new_board_id() for _ in range(200)]
    assert ids != sorted(ids)
    assert len({i[:4] for i in ids}) > 100                      # prefixes are spread out, not a counter


def test_tc_sec_02_id_generator_uses_a_cryptographic_source(monkeypatch):
    calls = []
    real = secrets.token_hex

    def spy(n):
        calls.append(n)
        return real(n)

    monkeypatch.setattr(board_service.secrets, "token_hex", spy)
    board_service.new_board_id()
    assert calls == [16]                                        # 16 bytes = 128 bits from `secrets`


def test_tc_sec_02_1000_random_ids_all_return_404(client):
    client.post("/api/boards")                                  # a real board exists; guesses must still miss
    for _ in range(1000):
        guess = secrets.token_hex(16)
        assert client.get(f"/api/boards/{guess}").status_code == 404


def test_tc_sec_02_random_ids_cannot_reach_versions_either(client):
    guess = secrets.token_hex(16)
    assert client.get(f"/api/boards/{guess}/versions").status_code == 404
    assert client.post(f"/api/boards/{guess}/versions").status_code == 404


def test_tc_sec_02_created_boards_get_distinct_ids_through_the_api(client):
    ids = {client.post("/api/boards").json()["id"] for _ in range(200)}
    assert len(ids) == 200


# ---- TC-Sec-05: append-only history (WB-SR-005) --------------------------------

@pytest.fixture
def two_versions(client, db):
    board = client.post("/api/boards").json()["id"]
    base = f"/api/boards/{board}/versions"
    append_op(db, board, "c1", "add", "s1", {"x": 1})
    a = client.post(base, json={"name": "first", "author": "Asha"}).json()["id"]
    append_op(db, board, "c1", "update", "s1", {"x": 2})
    append_op(db, board, "c1", "add", "s2", {"y": 2})
    b = client.post(base, json={"name": "second", "author": "Ben"}).json()["id"]
    return board, base, a, b


def test_tc_sec_05_two_restores_in_turn_lose_no_snapshot(client, two_versions):
    board, base, a, b = two_versions
    first = client.post(f"{base}/{a}/restore", json={"author": "Chitra"}).json()["id"]
    second = client.post(f"{base}/{b}/restore", json={"author": "Dev"}).json()["id"]

    listed = [v["id"] for v in client.get(base).json()]
    assert listed == [second, first, b, a]                      # all four are still there, newest first
    assert client.get(f"{base}/{a}").json()["state"] == {"s1": {"x": 1}}
    assert client.get(f"{base}/{b}").json()["state"] == {"s1": {"x": 2}, "s2": {"y": 2}}


def test_tc_sec_05_there_is_no_way_to_delete_or_edit_a_version(client, two_versions):
    board, base, a, b = two_versions
    for method in ("delete", "put", "patch"):
        assert getattr(client, method)(f"{base}/{a}").status_code in (404, 405)
        assert getattr(client, method)(base).status_code in (404, 405)
    assert client.delete(f"{base}/{a}/restore").status_code in (404, 405)
    assert len(client.get(base).json()) == 2                    # nothing changed

    destructive = [
        (route.path, sorted(route.methods or []))
        for route in app.routes
        if "versions" in getattr(route, "path", "")
        and {"DELETE", "PUT", "PATCH"} & set(route.methods or [])
    ]
    assert destructive == []                                    # no such route is registered at all


def test_tc_sec_05_each_restore_has_an_audit_entry_with_when_and_which_version(client, db, two_versions):
    board, base, a, b = two_versions
    first = client.post(f"{base}/{a}/restore", json={"author": "Chitra"}).json()["id"]
    second = client.post(f"{base}/{b}/restore", json={"author": "Dev"}).json()["id"]

    log = vs.list_audit(db, board)
    assert [(e.action, e.from_version, e.new_version) for e in log] == [
        ("restore", a, first),
        ("restore", b, second),
    ]
    assert all(e.created_at is not None for e in log)           # when


def test_tc_sec_05_restores_record_who_did_them(client, two_versions):
    board, base, a, b = two_versions
    first = client.post(f"{base}/{a}/restore", json={"author": "Chitra"}).json()
    second = client.post(f"{base}/{b}/restore", json={"author": "Dev"}).json()
    assert (first["author"], first["name"]) == ("Chitra", f"Restored from version {a}")
    assert (second["author"], second["name"]) == ("Dev", f"Restored from version {b}")


def test_tc_sec_05_restore_is_audited_even_after_a_failed_attempt(client, db, two_versions):
    board, base, a, b = two_versions
    assert client.post(f"{base}/9999/restore").status_code == 404
    assert vs.list_audit(db, board) == []                       # a failed restore leaves no false record
    assert len(client.get(base).json()) == 2
