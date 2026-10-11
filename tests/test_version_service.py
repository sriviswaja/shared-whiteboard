import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.server import models  # noqa: F401
from src.server.api.versions import get_state_source
from src.server.db import Base
from src.server.main import app
from src.server.services import versions as vs

A = [{"id": "s1", "data": {"x": 1}}]
B = [{"id": "s1", "data": {"x": 99}}, {"id": "s2", "data": {}}]


class FakeSource:
    def __init__(self):
        self.seq = 0
        self.objects = []
        self.replaced = None

    def snapshot(self, board_id):
        return self.seq, list(self.objects)

    def replace(self, board_id, objects):
        self.replaced = objects
        self.objects = objects


@pytest.fixture
def source(client):
    s = FakeSource()
    app.dependency_overrides[get_state_source] = lambda: s
    return s  # conftest clears overrides afterwards


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()


def make_board(client):
    return client.post("/api/boards").json()["id"]


# ---- TC-Ver-01: auto snapshot -------------------------------------------------

@pytest.mark.parametrize(
    "ops,secs,expected",
    [(99, 299, False), (100, 0, True), (1, 300, True), (0, 9999, False)],
)
def test_tc_ver_01_auto_snapshot_rule(ops, secs, expected):
    assert vs.should_auto_snapshot(ops, secs) is expected


def test_tc_ver_01_auto_versions_are_numbered_in_order(db):
    v1 = vs.create_version(db, "b1", "auto", 100, A)
    v2 = vs.create_version(db, "b1", "auto", 200, B)
    assert (v1.number, v2.number) == (1, 2)
    assert vs.create_version(db, "other", "auto", 1, A).number == 1  # per board


# ---- TC-Ver-02: named snapshot ------------------------------------------------

def test_tc_ver_02_named_snapshot(client, source):
    board = make_board(client)
    source.seq, source.objects = 7, A
    r = client.post(f"/api/boards/{board}/versions", json={"label": "before demo"})
    assert r.status_code == 201
    data = r.json()
    assert (data["number"], data["kind"], data["label"], data["seq"]) == (
        1, "named", "before demo", 7,
    )
    assert client.post(f"/api/boards/{board}/versions").json()["number"] == 2


def test_tc_ver_02_unknown_board_404(client, source):
    assert client.post("/api/boards/" + "0" * 32 + "/versions").status_code == 404


# ---- TC-Ver-03: version list --------------------------------------------------

def test_tc_ver_03_list_is_newest_first_and_capped_at_50(client, source):
    board = make_board(client)
    for _ in range(55):
        client.post(f"/api/boards/{board}/versions")
    versions = client.get(f"/api/boards/{board}/versions").json()
    assert len(versions) == 50
    assert versions[0]["number"] == 55 and versions[-1]["number"] == 6


def test_tc_ver_03_empty_list(client, source):
    board = make_board(client)
    assert client.get(f"/api/boards/{board}/versions").json() == []


# ---- TC-Ver-04: preview -------------------------------------------------------

def test_tc_ver_04_preview_returns_the_saved_state(client, source):
    board = make_board(client)
    source.seq, source.objects = 7, A
    client.post(f"/api/boards/{board}/versions")
    source.objects = B  # the board changes afterwards
    r = client.get(f"/api/boards/{board}/versions/1")
    assert r.status_code == 200
    assert r.json()["state"] == A and r.json()["seq"] == 7


def test_tc_ver_04_unknown_version_404(client, source):
    board = make_board(client)
    assert client.get(f"/api/boards/{board}/versions/5").status_code == 404


# ---- TC-Ver-05: restore -------------------------------------------------------

def test_tc_ver_05_restore_creates_new_version_and_keeps_history(client, source):
    board = make_board(client)
    base = f"/api/boards/{board}/versions"
    source.objects = A
    client.post(base)
    source.objects = B
    client.post(base)

    r = client.post(f"{base}/1/restore")
    assert r.status_code == 201
    assert r.json()["number"] == 3 and r.json()["kind"] == "restore"
    assert source.replaced == A  # live board got the old content back

    assert [v["number"] for v in client.get(base).json()] == [3, 2, 1]
    assert client.get(f"{base}/3").json()["state"] == A
    assert client.get(f"{base}/2").json()["state"] == B  # history untouched


def test_tc_ver_05_restore_unknown_version_404(client, source):
    board = make_board(client)
    assert client.post(f"/api/boards/{board}/versions/9/restore").status_code == 404


def test_tc_ver_05_restore_writes_audit_log(db):
    vs.create_version(db, "b1", "named", 1, A, "first")
    new = vs.restore_version(db, "b1", 1, current_seq=5)
    log = vs.list_audit(db, "b1")
    assert len(log) == 1
    assert (log[0].action, log[0].from_version, log[0].new_version) == (
        "restore", 1, new.number,
    )