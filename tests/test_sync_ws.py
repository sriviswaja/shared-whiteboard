from contextlib import ExitStack

import pytest
from starlette.websockets import WebSocketDisconnect

from src.server.api.ws import get_hub, get_sessions
from src.server.main import app
from src.server.services.session import SessionService
from src.server.services.sync import SyncHub


@pytest.fixture
def ws_client(client):
    hub, sessions = SyncHub(), SessionService()
    app.dependency_overrides[get_hub] = lambda: hub
    app.dependency_overrides[get_sessions] = lambda: sessions
    return client  # conftest clears the overrides afterwards


def make_board(client):
    return client.post("/api/boards").json()["id"]


def url(board_id, name):
    return f"/ws/boards/{board_id}?name={name}"


def recv_until(ws, pred):
    for _ in range(30):
        msg = ws.receive_json()
        if pred(msg):
            return msg
    raise AssertionError("expected message never arrived")


def recv_type(ws, kind):
    return recv_until(ws, lambda m: m["type"] == kind)


def recv_presence(ws, count):
    return recv_until(
        ws, lambda m: m["type"] == "presence" and len(m["participants"]) == count
    )


def assert_closed_with(ws, code):
    with pytest.raises(WebSocketDisconnect) as exc:
        for _ in range(30):
            ws.receive_json()  # skip any queued messages until the close arrives
    assert exc.value.code == code


def test_tc_board_02_join_gets_welcome(ws_client):
    board = make_board(ws_client)
    with ws_client.websocket_connect(url(board, "Alice")) as a:
        w = recv_type(a, "welcome")
        assert w["seq"] == 0 and w["objects"] == []
        assert w["participants"][0]["name"] == "Alice"


def test_tc_board_03_presence_updates_on_leave(ws_client):
    board = make_board(ws_client)
    with ws_client.websocket_connect(url(board, "A")) as a:
        recv_type(a, "welcome")
        with ws_client.websocket_connect(url(board, "B")) as b:
            recv_type(b, "welcome")
            recv_presence(a, 2)
        recv_presence(a, 1)


def test_tc_board_04_21st_participant_rejected(ws_client):
    board = make_board(ws_client)
    with ExitStack() as stack:
        for i in range(20):
            ws = stack.enter_context(ws_client.websocket_connect(url(board, f"u{i}")))
            recv_type(ws, "welcome")
        extra = stack.enter_context(ws_client.websocket_connect(url(board, "late")))
        assert_closed_with(extra, 4002)


def test_tc_board_04_unknown_board_closes_4001(ws_client):
    with ws_client.websocket_connect(url("0" * 32, "A")) as ws:
        assert_closed_with(ws, 4001)


def test_invalid_name_closes_4003(ws_client):
    board = make_board(ws_client)
    with ws_client.websocket_connect(url(board, "")) as ws:
        assert_closed_with(ws, 4003)


def test_invalid_message_closes_4003(ws_client):
    board = make_board(ws_client)
    with ws_client.websocket_connect(url(board, "A")) as ws:
        recv_type(ws, "welcome")
        ws.send_json({"type": "op", "op": {"kind": "explode", "id": "x"}})
        assert_closed_with(ws, 4003)


def test_tc_sync_01_op_broadcast_to_everyone(ws_client):
    board = make_board(ws_client)
    op = {"kind": "add", "id": "s1", "data": {"shape": "rect"}}
    with ws_client.websocket_connect(url(board, "A")) as a, \
            ws_client.websocket_connect(url(board, "B")) as b:
        wa = recv_type(a, "welcome")
        recv_type(b, "welcome")
        a.send_json({"type": "op", "op": op})
        ma, mb = recv_type(a, "op"), recv_type(b, "op")
        assert ma == mb
        assert ma["seq"] == 1
        assert ma["client_id"] == wa["client_id"]
        assert ma["op"] == op


def test_tc_sync_01_server_orders_ops(ws_client):
    board = make_board(ws_client)
    with ws_client.websocket_connect(url(board, "A")) as a:
        recv_type(a, "welcome")
        for i in range(3):
            a.send_json({"type": "op", "op": {"kind": "add", "id": f"s{i}", "data": {}}})
        assert [recv_type(a, "op")["seq"] for _ in range(3)] == [1, 2, 3]


def test_tc_sync_04_reconnect_gets_full_state(ws_client):
    board = make_board(ws_client)
    with ws_client.websocket_connect(url(board, "A")) as a:
        recv_type(a, "welcome")
        a.send_json({"type": "op", "op": {"kind": "add", "id": "s1", "data": {"x": 1}}})
        a.send_json({"type": "op", "op": {"kind": "add", "id": "s2", "data": {"x": 2}}})
        recv_type(a, "op")
        recv_type(a, "op")
    with ws_client.websocket_connect(url(board, "A")) as a2:
        w = recv_type(a2, "welcome")
    assert {o["id"] for o in w["objects"]} == {"s1", "s2"}
    assert w["seq"] == 2