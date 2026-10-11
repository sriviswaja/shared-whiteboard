import pytest


@pytest.mark.parametrize("length", [1, 100])
def test_tc_board_01_name_length_boundaries_accepted(client, length):
    r = client.post("/api/boards", json={"name": "x" * length})
    assert r.status_code == 201
    assert len(r.json()["name"]) == length


def test_tc_board_01_malformed_id_not_found(client):
    r = client.get("/api/boards/not-a-real-id")
    assert r.status_code in (404, 422)


@pytest.mark.parametrize("bad_name", [123, None, ["a"], {"a": 1}])
def test_tc_board_01_wrong_type_name_rejected(client, bad_name):
    r = client.post("/api/boards", json={"name": bad_name})
    assert r.status_code == 422


def test_tc_sec_03_script_in_name_does_not_break_api(client):
    payload = "<script>alert(1)</script>"
    r = client.post("/api/boards", json={"name": payload})
    assert r.status_code == 201
    board_id = r.json()["id"]
    assert client.get(f"/api/boards/{board_id}").status_code == 200
