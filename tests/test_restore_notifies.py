"""TC-Ver-03 / WB-F-034: restoring a version updates everyone connected to the board."""
import pytest

from src.server.gateway.ws import hub


@pytest.fixture(autouse=True)
def fresh_gateway():
    hub.reset()
    yield
    hub.reset()


def read_until(ws, kind):
    for _ in range(20):
        msg = ws.receive_json()
        if msg["type"] == kind:
            return msg
    raise AssertionError(f"never received {kind}")


def test_tc_ver_03_restore_notifies_connected_clients(client):
    board_id = client.post("/api/boards", json={"name": "t"}).json()["id"]
    empty = client.post(f"/api/boards/{board_id}/versions", json={"name": "empty"}).json()["id"]

    with client.websocket_connect(f"/ws/boards/{board_id}?name=Alice") as alice, \
         client.websocket_connect(f"/ws/boards/{board_id}?name=Bob") as bob:
        read_until(alice, "welcome")
        read_until(bob, "welcome")
        alice.send_json({"type": "op:add", "opId": "o1", "object": {
            "id": "r1", "type": "rect", "props": {"x": 1, "y": 2, "w": 3, "h": 4}}})
        read_until(bob, "op")                                   # Bob sees the rectangle

        res = client.post(f"/api/boards/{board_id}/versions/{empty}/restore",
                          json={"author": "Alice"})
        assert res.status_code == 201

        for ws in (alice, bob):
            reset = read_until(ws, "board:reset")
            assert reset["objects"] == []                       # the empty version is back
            assert reset["reason"] == "restore"
    assert hub.rooms[board_id].objects() == []


def test_tc_ver_03_restore_with_nobody_connected_still_works(client):
    board_id = client.post("/api/boards", json={"name": "t"}).json()["id"]
    v = client.post(f"/api/boards/{board_id}/versions", json={"name": "v"}).json()["id"]
    res = client.post(f"/api/boards/{board_id}/versions/{v}/restore", json={"author": "A"})
    assert res.status_code == 201
