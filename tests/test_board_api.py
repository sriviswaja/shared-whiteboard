import re


def test_tc_board_01_create_board(client):
    r = client.post("/api/boards", json={"name": "Sprint planning"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Sprint planning"
    assert re.fullmatch(r"[0-9a-f]{32}", data["id"])  # 128-bit id


def test_tc_board_01_create_board_default_name(client):
    r = client.post("/api/boards")
    assert r.status_code == 201
    assert r.json()["name"] == "Untitled board"


def test_tc_board_01_ids_are_unique(client):
    ids = {client.post("/api/boards").json()["id"] for _ in range(50)}
    assert len(ids) == 50


def test_tc_board_01_get_board_roundtrip(client):
    created = client.post("/api/boards", json={"name": "A"}).json()
    r = client.get(f"/api/boards/{created['id']}")
    assert r.status_code == 200
    assert r.json() == created


def test_tc_board_01_unknown_board_404(client):
    r = client.get("/api/boards/" + "0" * 32)
    assert r.status_code == 404


def test_tc_board_01_invalid_name_rejected(client):
    assert client.post("/api/boards", json={"name": ""}).status_code == 422
    assert client.post("/api/boards", json={"name": "x" * 101}).status_code == 422