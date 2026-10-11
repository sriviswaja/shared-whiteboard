"""Tests for the Sync Gateway (feature/sync-gateway).

Hub-level tests drive the gateway directly with a fake clock (fast and exact).
The `ws_` tests go through a real WebSocket on the FastAPI app.
"""
import hashlib
import json
import random
from contextlib import ExitStack

import pytest
from starlette.websockets import WebSocketDisconnect

from src.server.gateway import validation
from src.server.gateway.hub import Hub
from src.server.gateway.room import BoardRoom, OperationRejected
from src.server.gateway.ws import hub as app_hub
from src.server.services.session import BoardFullError, InvalidNameError

BOARD = "board-a"


# ---------------------------------------------------------------- helpers

class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.fixture(autouse=True)
def fresh_gateway():
    app_hub.reset()
    yield
    app_hub.reset()


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def hub(clock):
    # High rate so functional tests are not throttled; the rate-limit tests build their own Hub.
    return Hub(clock=clock, rate=1_000_000)


def drain(conn):
    out = []
    while not conn.outbox.empty():
        out.append(conn.outbox.get_nowait())
    return out


def ops_of(messages):
    return [m for m in messages if m["type"] == "op"]


def send(hub, conn, **msg):
    return hub.handle(conn, json.dumps(msg))


def stroke(object_id, **props):
    base = {"points": [[0, 0], [1, 1]], "colour": "#000000", "width": 2}
    base.update(props)
    return {"id": object_id, "type": "stroke", "z": 0, "props": base}


def add(hub, conn, object_id, op_id=None, **props):
    return send(hub, conn, type="op:add", opId=op_id or f"op-{object_id}",
                object=stroke(object_id, **props))


# ---------------------------------------------------------------- TC-Board-02/03/04 over the gateway

def test_tc_board_02_join_gets_welcome_with_client_id_and_state(hub):
    conn = hub.connect(BOARD, "Asha")
    welcome = drain(conn)[0]
    assert welcome["type"] == "welcome"
    assert welcome["clientId"] == conn.client_id
    assert welcome["objects"] == [] and welcome["seq"] == 0
    assert welcome["participants"] == [{"clientId": conn.client_id, "name": "Asha"}]


@pytest.mark.parametrize("bad", ["", "   ", "x" * 31])
def test_tc_board_02_bad_names_are_refused(hub, bad):
    with pytest.raises(InvalidNameError):
        hub.connect(BOARD, bad)


def test_tc_board_03_presence_follows_join_and_leave(hub):
    a = hub.connect(BOARD, "A")
    drain(a)
    b = hub.connect(BOARD, "B")
    presence = [m for m in drain(a) if m["type"] == "presence"][-1]
    assert [p["name"] for p in presence["participants"]] == ["A", "B"]
    hub.disconnect(b)
    presence = [m for m in drain(a) if m["type"] == "presence"][-1]
    assert [p["name"] for p in presence["participants"]] == ["A"]


def test_tc_board_04_21st_client_refused_then_admitted_after_a_leave(hub):
    conns = [hub.connect(BOARD, f"u{i}") for i in range(20)]
    with pytest.raises(BoardFullError) as err:
        hub.connect(BOARD, "late")
    assert err.value.code == 4002
    hub.disconnect(conns[0])
    assert hub.connect(BOARD, "late").participant.name == "late"


# ---------------------------------------------------------------- TC-Sync-01: broadcast in order

def test_tc_sync_01_every_client_gets_all_100_ops_in_order_without_duplicates(hub):
    a = hub.connect(BOARD, "A")
    others = [hub.connect(BOARD, n) for n in "BCD"]
    for c in [a, *others]:
        drain(c)
    for i in range(100):
        add(hub, a, f"obj{i}")
    for c in [a, *others]:           # the sender gets its own ops back as the acknowledgement
        got = ops_of(drain(c))
        assert [m["seq"] for m in got] == list(range(1, 101))
        assert [m["objectId"] for m in got] == [f"obj{i}" for i in range(100)]
    assert ops_of(drain(others[0])) == []


def test_tc_sync_01_ack_carries_op_id_and_server_seq(hub):
    a = hub.connect(BOARD, "A")
    drain(a)
    add(hub, a, "o1", op_id="my-op")
    msg = ops_of(drain(a))[0]
    assert (msg["opId"], msg["seq"], msg["clientId"], msg["opType"]) == (
        "my-op", 1, a.client_id, "add")


def test_tc_sync_01_boards_are_isolated(hub):
    a = hub.connect("board-a", "A")
    b = hub.connect("board-b", "B")
    drain(a), drain(b)
    add(hub, a, "o1")
    assert ops_of(drain(b)) == []
    assert hub.room("board-b").seq == 0


# ---------------------------------------------------------------- TC-Sync-02: remote cursors

def test_tc_sync_02_cursor_is_relayed_with_name_to_others_only(hub):
    a, b = hub.connect(BOARD, "Asha"), hub.connect(BOARD, "Ben")
    drain(a), drain(b)
    send(hub, a, type="cursor:move", x=10, y=20)
    assert drain(b) == [{"type": "cursor", "clientId": a.client_id,
                         "name": "Asha", "x": 10, "y": 20}]
    assert drain(a) == []


def test_tc_sync_02_cursor_is_throttled_to_about_20_per_second_and_never_stored(hub, clock):
    a, b = hub.connect(BOARD, "A"), hub.connect(BOARD, "B")
    drain(b)
    for _ in range(10):                       # 10 moves at the same instant
        send(hub, a, type="cursor:move", x=1, y=1)
    assert len(drain(b)) == 1
    clock.now += 0.06
    send(hub, a, type="cursor:move", x=2, y=2)
    assert len(drain(b)) == 1
    assert hub.room(BOARD).seq == 0           # cursors never touch board state


# ---------------------------------------------------------------- TC-Sync-03: last-write-wins

def room_with_object():
    room = BoardRoom(BOARD)
    room.apply("a", "add", "o0", "x", stroke("x", colour="#111111", width=2))
    return room


def test_tc_sync_03_same_property_higher_seq_wins():
    room = room_with_object()
    room.apply("a", "update", "oa", "x", {"colour": "red"})
    room.apply("b", "update", "ob", "x", {"colour": "blue"})
    assert room.elements["x"].props["colour"] == "blue"   # B's op got the higher seq
    assert room.elements["x"].prop_seq["colour"] == 3


def test_tc_sync_03_different_properties_both_kept():
    room = room_with_object()
    room.apply("a", "update", "oa", "x", {"colour": "red"})
    room.apply("b", "update", "ob", "x", {"width": 9})
    props = room.elements["x"].props
    assert (props["colour"], props["width"]) == ("red", 9)


def test_tc_sync_03_update_after_delete_is_ignored_tombstone():
    room = room_with_object()
    room.apply("a", "delete", "od", "x", {})
    with pytest.raises(OperationRejected):
        room.apply("b", "update", "ou", "x", {"colour": "red"})
    assert room.objects() == []
    assert room.seq == 2                      # the rejected op consumed no seq


def test_tc_sync_03_rejected_ops_are_not_broadcast_and_sender_gets_an_error(hub):
    a, b = hub.connect(BOARD, "A"), hub.connect(BOARD, "B")
    drain(a), drain(b)
    send(hub, a, type="op:update", opId="u1", objectId="ghost", changes={"colour": "red"})
    err = drain(a)[0]
    assert (err["type"], err["code"], err["opId"]) == ("error", 4004, "u1")
    assert drain(b) == []


def test_tc_sync_03_concurrent_edits_end_identical_for_all_clients(hub):
    a, b, c = (hub.connect(BOARD, n) for n in "ABC")
    add(hub, a, "x", colour="#000000", width=1)
    history = {id(conn): ops_of(drain(conn)) for conn in (a, b, c)}
    send(hub, a, type="op:update", opId="a1", objectId="x", changes={"colour": "red"})
    send(hub, b, type="op:update", opId="b1", objectId="x", changes={"colour": "blue"})
    send(hub, a, type="op:update", opId="a2", objectId="x", changes={"width": 7})
    finals = []
    for conn in (a, b, c):
        replica = Replica()
        replica.apply_all(history[id(conn)] + ops_of(drain(conn)))
        finals.append(replica.digest())
    assert len(set(finals)) == 1
    assert hub.room(BOARD).elements["x"].props["colour"] == "blue"
    assert hub.room(BOARD).elements["x"].props["width"] == 7


# ---------------------------------------------------------------- TC-Sync-04: reconnect and resync

def test_tc_sync_04_resume_replays_missed_ops(hub):
    a, b = hub.connect(BOARD, "A"), hub.connect(BOARD, "B")
    add(hub, a, "o1")
    last_seen = ops_of(drain(b))[-1]["seq"]
    hub.disconnect(b)                                  # B goes offline
    for i in range(2, 6):
        add(hub, a, f"o{i}")
    b2 = hub.connect(BOARD, "B")                       # reconnects, new connection
    drain(b2)
    send(hub, b2, type="resume", lastSeq=last_seen)
    assert [m["seq"] for m in ops_of(drain(b2))] == [2, 3, 4, 5]


def test_tc_sync_04_offline_stroke_reaches_others_exactly_once_even_if_resent(hub):
    a, b = hub.connect(BOARD, "A"), hub.connect(BOARD, "B")
    drain(a), drain(b)
    hub.disconnect(b)
    b2 = hub.connect(BOARD, "B")
    drain(a), drain(b2)
    add(hub, b2, "queued", op_id="queued-op")
    add(hub, b2, "queued", op_id="queued-op")          # client re-sends after a flaky reconnect
    assert [m["objectId"] for m in ops_of(drain(a))] == ["queued"]
    acks = ops_of(drain(b2))
    assert [m["seq"] for m in acks] == [1, 1]          # both acknowledged with the same seq
    assert hub.room(BOARD).seq == 1


def test_tc_sync_04_gap_larger_than_log_falls_back_to_full_state(hub):
    a = hub.connect(BOARD, "A")
    add(hub, a, "o1")
    hub.room(BOARD)._log.clear()                       # simulate the log having been trimmed
    drain(a)
    send(hub, a, type="resume", lastSeq=0)
    welcome = drain(a)[0]
    assert welcome["type"] == "welcome"
    assert [o["id"] for o in welcome["objects"]] == ["o1"] and welcome["seq"] == 1


def test_tc_sync_04_resume_from_the_future_gets_full_state(hub):
    a = hub.connect(BOARD, "A")
    drain(a)
    send(hub, a, type="resume", lastSeq=999)           # e.g. server restarted, seq went back
    assert drain(a)[0]["type"] == "welcome"


# ---------------------------------------------------------------- TC-Sync-05: convergence under load

class Replica:
    """A minimal client model: applies broadcast ops in order."""

    def __init__(self):
        self.objects = {}
        self.last_seq = 0

    def apply_all(self, messages):
        for m in messages:
            assert m["seq"] == self.last_seq + 1 or m["seq"] <= self.last_seq, "gap or reorder"
            if m["seq"] <= self.last_seq:
                continue                                # duplicate delivery is ignored
            self.last_seq = m["seq"]
            if m["opType"] == "add":
                self.objects[m["objectId"]] = {"props": dict(m["payload"]["props"]), "deleted": False}
            elif m["opType"] == "update":
                self.objects[m["objectId"]]["props"].update(
                    {k: v for k, v in m["payload"].items() if k != "z"})
            else:
                self.objects[m["objectId"]]["deleted"] = True

    def digest(self):
        live = {k: v["props"] for k, v in self.objects.items() if not v["deleted"]}
        return hashlib.sha256(json.dumps(live, sort_keys=True).encode()).hexdigest()


def test_tc_sync_05_ten_clients_200_random_ops_each_all_converge(hub):
    rng = random.Random(42)
    conns = [hub.connect(BOARD, f"u{i}") for i in range(10)]
    replicas = [Replica() for _ in conns]
    known, counter = [], 0
    for _ in range(200):
        for conn in rng.sample(conns, len(conns)):      # clients act "at once", interleaved
            action = rng.choice(["add", "add", "update", "update", "update", "delete"])
            if action == "add" or not known:
                counter += 1
                known.append(f"o{counter}")
                add(hub, conn, known[-1], op_id=f"{conn.client_id}-{counter}", n=counter)
            else:
                target = rng.choice(known)
                if action == "update":
                    send(hub, conn, type="op:update", opId=f"{conn.client_id}-{counter}-{rng.random()}",
                         objectId=target, changes={rng.choice(["colour", "width", "x"]): rng.randint(0, 99)})
                else:
                    send(hub, conn, type="op:delete", opId=f"{conn.client_id}-d-{rng.random()}",
                         objectId=target)
    digests = set()
    for conn, replica in zip(conns, replicas):
        replica.apply_all(ops_of(drain(conn)))
        digests.add(replica.digest())
    room = hub.room(BOARD)
    server = hashlib.sha256(json.dumps(
        {o["id"]: o["props"] for o in room.objects()}, sort_keys=True).encode()).hexdigest()
    assert digests == {server}
    assert all(r.last_seq == room.seq for r in replicas)


# ---------------------------------------------------------------- TC-Sec-03: validation and XSS

@pytest.mark.parametrize("raw", [
    "not json", "[]", '{"type": "evil"}', '{"no": "type"}',
    '{"type": "op:add", "opId": "x"}',
    '{"type": "op:add", "opId": "x", "object": {"id": "1", "type": "nope", "props": {"a": 1}}}',
    '{"type": "cursor:move", "x": "left", "y": 1}',
    '{"type": "op:update", "opId": "x", "objectId": "1", "changes": {}}',
    '{"type": "resume", "lastSeq": -1}',
])
def test_tc_sec_03_bad_messages_get_4003_and_connection_stays_open(hub, raw):
    a = hub.connect(BOARD, "A")
    drain(a)
    assert hub.handle(a, raw) is None                   # None = do not close
    err = drain(a)[0]
    assert (err["type"], err["code"]) == ("error", 4003)
    assert hub.room(BOARD).seq == 0


def test_tc_sec_03_oversized_message_rejected_with_413(hub):
    a = hub.connect(BOARD, "A")
    drain(a)
    assert hub.handle(a, "x" * (validation.MAX_MESSAGE_BYTES + 1)) is None
    assert drain(a)[0]["code"] == 413


def test_tc_sec_03_script_text_is_stored_and_relayed_as_plain_text(hub):
    a, b = hub.connect(BOARD, "A"), hub.connect(BOARD, "B")
    drain(a), drain(b)
    payload = "<script>alert(1)</script><img src=x onerror=alert(1)>"
    send(hub, a, type="op:add", opId="t1",
         object={"id": "t", "type": "text", "z": 1, "props": {"x": 1, "y": 1, "text": payload}})
    relayed = ops_of(drain(b))[0]["payload"]["props"]["text"]
    assert relayed == payload                           # untouched data, drawn on canvas, never as HTML
    assert hub.room(BOARD).objects()[0]["props"]["text"] == payload


def test_tc_sec_03_text_length_and_point_count_limits(hub):
    a = hub.connect(BOARD, "A")
    drain(a)
    too_long = {"id": "t", "type": "text", "props": {"text": "a" * (validation.MAX_TEXT_LENGTH + 1)}}
    assert hub.handle(a, json.dumps({"type": "op:add", "opId": "1", "object": too_long})) is None
    many = {"id": "s", "type": "stroke",
            "props": {"points": [[0, 0]] * (validation.MAX_STROKE_POINTS + 1)}}
    hub.handle(a, json.dumps({"type": "op:add", "opId": "2", "object": many}))
    assert [m["code"] for m in drain(a)] == [4003, 4003]


# ---------------------------------------------------------------- TC-Sec-04: rate limiting

def test_tc_sec_04_flooder_is_throttled_to_about_60_per_second_and_gets_4290(clock):
    hub = Hub(clock=clock)
    flooder, other = hub.connect(BOARD, "Flood"), hub.connect(BOARD, "Calm")
    drain(flooder), drain(other)
    for i in range(500):                                # 500 messages in the same second
        hub.handle(flooder, json.dumps({"type": "ping"}))
    replies = drain(flooder)
    assert sum(m["type"] == "pong" for m in replies) == 60
    assert any(m.get("code") == 4290 for m in replies)
    add(hub, other, "fine")                             # the other client is unaffected
    assert len(ops_of(drain(other))) == 1


def test_tc_sec_04_persistent_flooding_closes_the_connection(clock):
    hub = Hub(clock=clock)
    flooder = hub.connect(BOARD, "Flood")
    closes = [hub.handle(flooder, '{"type": "ping"}') for _ in range(400)]
    assert 4290 in closes


def test_tc_sec_04_occasional_bursts_do_not_add_up_to_a_disconnect(clock):
    hub = Hub(clock=clock)
    a = hub.connect(BOARD, "A")
    closes = []
    for _ in range(5):                                  # a burst well over the limit, every 10 s
        closes += [hub.handle(a, '{"type": "ping"}') for _ in range(130)]
        clock.now += 10
    assert 4290 not in closes


def test_tc_sec_04_bucket_refills_over_time(clock):
    hub = Hub(clock=clock)
    a = hub.connect(BOARD, "A")
    drain(a)
    for _ in range(60):
        hub.handle(a, '{"type": "ping"}')
    hub.handle(a, '{"type": "ping"}')                   # 61st, throttled
    clock.now += 1.0
    hub.handle(a, '{"type": "ping"}')
    types = [m["type"] for m in drain(a)]
    assert types.count("pong") == 61 and types.count("error") == 1


# ---------------------------------------------------------------- TC-Sec-06: membership on every message

def test_tc_sec_06_message_after_leaving_is_rejected_and_changes_nothing(hub):
    a = hub.connect(BOARD, "A")
    hub.sessions.leave(BOARD, a.client_id)              # membership revoked (e.g. dropped session)
    assert add(hub, a, "ghost") == 4003
    assert hub.room(BOARD).seq == 0


def test_tc_sec_06_connection_can_only_ever_touch_its_own_board(hub):
    a = hub.connect("board-a", "A")
    hub.connect("board-b", "B")
    send(hub, a, type="op:add", opId="x", boardId="board-b", object=stroke("o1"))
    assert hub.room("board-a").seq == 1
    assert hub.room("board-b").seq == 0


# ---------------------------------------------------------------- restore hook (used by Version Service)

def test_board_reset_replaces_state_for_everyone_and_keeps_seq_in_step_with_the_log(hub):
    a, b = hub.connect(BOARD, "A"), hub.connect(BOARD, "B")
    add(hub, a, "old")
    drain(a), drain(b)
    hub.board_reset(BOARD, [stroke("restored")])
    msg = [m for m in drain(b) if m["type"] == "board:reset"][0]
    assert msg["seq"] == 1 and [o["id"] for o in msg["objects"]] == ["restored"]
    assert [o["id"] for o in hub.room(BOARD).objects()] == ["restored"]


def test_persistence_listener_sees_every_applied_op_once(hub):
    seen = []
    hub.room(BOARD).listeners.append(seen.append)
    a = hub.connect(BOARD, "A")
    add(hub, a, "o1", op_id="same")
    add(hub, a, "o1", op_id="same")                     # duplicate: not applied again
    assert [op.seq for op in seen] == [1]


# ---------------------------------------------------------------- real WebSocket (through the app)

def new_board(client):
    return client.post("/api/boards", json={"name": "t"}).json()["id"]


def recv_type(ws, kind):
    for _ in range(50):
        msg = ws.receive_json()
        if msg["type"] == kind:
            return msg
    raise AssertionError(f"no {kind} message")


def test_tc_sync_01_ws_two_browsers_see_each_others_strokes(client):
    board = new_board(client)
    with client.websocket_connect(f"/ws/boards/{board}?name=Asha") as a, \
            client.websocket_connect(f"/ws/boards/{board}?name=Ben") as b:
        assert recv_type(a, "welcome")["participants"][0]["name"] == "Asha"
        recv_type(b, "welcome")
        a.send_json({"type": "op:add", "opId": "s1", "object": stroke("s1")})
        got = recv_type(b, "op")
        assert (got["seq"], got["objectId"], got["opType"]) == (1, "s1", "add")
        assert recv_type(a, "op")["opId"] == "s1"       # sender's acknowledgement


def test_tc_sync_04_ws_reconnect_with_resume_catches_up(client):
    board = new_board(client)
    with client.websocket_connect(f"/ws/boards/{board}?name=A") as a:
        recv_type(a, "welcome")
        with client.websocket_connect(f"/ws/boards/{board}?name=B") as b:
            recv_type(b, "welcome")
        for i in range(3):                              # B is offline now
            a.send_json({"type": "op:add", "opId": f"o{i}", "object": stroke(f"o{i}")})
            recv_type(a, "op")
        with client.websocket_connect(f"/ws/boards/{board}?name=B") as b2:
            recv_type(b2, "welcome")
            b2.send_json({"type": "resume", "lastSeq": 0})
            assert [recv_type(b2, "op")["seq"] for _ in range(3)] == [1, 2, 3]


def test_tc_board_02_ws_unknown_board_closes_with_4001(client):
    with client.websocket_connect("/ws/boards/" + "0" * 32 + "?name=Asha") as ws:
        assert ws.receive_json()["code"] == 4001
        with pytest.raises(WebSocketDisconnect) as err:
            ws.receive_json()
        assert err.value.code == 4001


def test_tc_board_02_ws_empty_name_closes_with_4003(client):
    board = new_board(client)
    with client.websocket_connect(f"/ws/boards/{board}?name=") as ws:
        assert ws.receive_json()["code"] == 4003
        with pytest.raises(WebSocketDisconnect) as err:
            ws.receive_json()
        assert err.value.code == 4003


def test_tc_board_04_ws_21st_client_refused_with_4002(client):
    board = new_board(client)
    with ExitStack() as stack:
        for i in range(20):
            ws = stack.enter_context(client.websocket_connect(f"/ws/boards/{board}?name=u{i}"))
            recv_type(ws, "welcome")
        with client.websocket_connect(f"/ws/boards/{board}?name=late") as late:
            assert late.receive_json()["code"] == 4002
            with pytest.raises(WebSocketDisconnect) as err:
                late.receive_json()
            assert err.value.code == 4002


def test_tc_sec_03_ws_garbage_does_not_drop_the_connection(client):
    board = new_board(client)
    with client.websocket_connect(f"/ws/boards/{board}?name=A") as ws:
        recv_type(ws, "welcome")
        ws.send_text("{{{ not json")
        assert recv_type(ws, "error")["code"] == 4003
        ws.send_json({"type": "ping"})
        recv_type(ws, "pong")                            # still alive


def test_tc_board_03_ws_leaver_disappears_from_presence(client):
    board = new_board(client)
    with client.websocket_connect(f"/ws/boards/{board}?name=A") as a:
        recv_type(a, "welcome")
        with client.websocket_connect(f"/ws/boards/{board}?name=B") as b:
            recv_type(b, "welcome")
            assert [p["name"] for p in recv_type(a, "presence")["participants"]][-1:] in (["A"], ["B"])
            names = []
            while "B" not in names:
                names = [p["name"] for p in recv_type(a, "presence")["participants"]]
        while names != ["A"]:
            names = [p["name"] for p in recv_type(a, "presence")["participants"]]
        assert names == ["A"]
