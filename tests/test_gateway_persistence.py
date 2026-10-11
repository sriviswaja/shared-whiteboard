"""Gateway + database together (feature/board-service): TC-Persist-01, WB-F-030, WB-F-040."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.server.db import Base
from src.server.gateway import persistence
from src.server.gateway.hub import Hub
from src.server.gateway.room import BoardRoom
from src.server.gateway.ws import hub as app_hub
from src.server.models import Board
from src.server.services import board_ops, snapshots

BOARD = "b" * 32


@pytest.fixture(autouse=True)
def fresh_gateway():
    app_hub.reset()
    yield
    app_hub.reset()


@pytest.fixture
def store():
    """An in-memory database plus an `open_db` like the endpoint uses."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    with Session() as db:
        db.add(Board(id=BOARD, name="t"))
        db.commit()

    def get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    return persistence.opener_from_dependency(get_db)


def live_hub(store):
    """A hub whose room for BOARD is loaded from the database and saves back to it."""
    persistence.flush()                      # saves are written in the background
    hub = Hub(rate=1_000_000)
    with store() as db:
        room = persistence.room_from_db(db, BOARD)
    persistence.attach_store(room, store)
    hub.rooms[BOARD] = room
    return hub


def drain(conn):
    out = []
    while not conn.outbox.empty():
        out.append(conn.outbox.get_nowait())
    return out


def add(hub, conn, oid, op_id=None, z=0, **props):
    import json
    props = {"points": [[0, 0], [1, 1]], "colour": "#000000", "width": 2, **props}
    hub.handle(conn, json.dumps({"type": "op:add", "opId": op_id or f"op-{oid}", "object": {
        "id": oid, "type": "stroke", "z": z, "props": props}}))


def send(hub, conn, **msg):
    import json
    hub.handle(conn, json.dumps(msg))


# ---- TC-Persist-01 through the gateway

def test_tc_persist_01_ws_objects_survive_a_server_restart(client):
    board = client.post("/api/boards", json={"name": "t"}).json()["id"]
    drawn = {}
    with client.websocket_connect(f"/ws/boards/{board}?name=Asha") as ws:
        ws.receive_json()
        for i in range(20):
            props = {"points": [[i, i], [i + 1, i + 1]], "colour": "#d62828", "width": 3}
            drawn[f"o{i}"] = props
            ws.send_json({"type": "op:add", "opId": f"op{i}", "object": {
                "id": f"o{i}", "type": "stroke", "z": i, "props": props}})
        seen = 0
        while seen < 20:                       # wait until every op is acknowledged
            seen += ws.receive_json()["type"] == "op"
    persistence.flush()
    app_hub.reset()                            # "restart": all rooms and sessions forgotten
    with client.websocket_connect(f"/ws/boards/{board}?name=Ben") as ws:
        welcome = ws.receive_json()
    assert welcome["type"] == "welcome" and welcome["seq"] == 20
    assert {o["id"]: o["props"] for o in welcome["objects"]} == drawn
    assert [o["z"] for o in welcome["objects"]] == list(range(20))


def test_tc_persist_01_updates_and_deletes_survive_a_restart(store):
    hub = live_hub(store)
    a = hub.connect(BOARD, "A")
    add(hub, a, "keep", colour="#111111", width=2)
    add(hub, a, "gone")
    send(hub, a, type="op:update", opId="u1", objectId="keep", changes={"colour": "#ff0000", "z": 5})
    send(hub, a, type="op:delete", opId="d1", objectId="gone")

    reopened = live_hub(store)                 # new process, same database
    obj = reopened.room(BOARD).objects()
    assert len(obj) == 1 and obj[0]["id"] == "keep"
    assert obj[0]["props"]["colour"] == "#ff0000" and obj[0]["props"]["width"] == 2
    assert obj[0]["z"] == 5
    assert reopened.room(BOARD).seq == 4


def test_ops_are_stored_in_the_flat_format_with_matching_seq(store):
    hub = live_hub(store)
    a = hub.connect(BOARD, "A")
    add(hub, a, "o1", colour="#123456")
    send(hub, a, type="op:update", opId="u1", objectId="o1", changes={"width": 9})
    persistence.flush()
    with store() as db:
        ops = board_ops.list_ops(db, BOARD)
        assert [(o.seq, o.op_type) for o in ops] == [(1, "add"), (2, "update")]
        assert ops[0].payload["type"] == "stroke" and ops[0].payload["colour"] == "#123456"
        assert "props" not in ops[0].payload
        assert board_ops.load_board_state(db, BOARD)["o1"]["width"] == 9


def test_seq_continues_after_a_restart_with_no_gap(store):
    hub = live_hub(store)
    a = hub.connect(BOARD, "A")
    for i in range(3):
        add(hub, a, f"o{i}")
    reopened = live_hub(store)
    b = reopened.connect(BOARD, "B")
    drain(b)
    add(reopened, b, "next")
    assert [m["seq"] for m in drain(b) if m["type"] == "op"] == [4]
    persistence.flush()
    with store() as db:
        assert [o.seq for o in board_ops.list_ops(db, BOARD)] == [1, 2, 3, 4]


def test_rejected_and_duplicate_ops_are_not_saved(store):
    hub = live_hub(store)
    a = hub.connect(BOARD, "A")
    add(hub, a, "o1", op_id="same")
    add(hub, a, "o1", op_id="same")                                  # duplicate opId
    send(hub, a, type="op:update", opId="x", objectId="ghost", changes={"width": 1})
    send(hub, a, type="op:update", opId="y", objectId="o1", changes={"type": "text"})  # reserved
    persistence.flush()
    with store() as db:
        assert len(board_ops.list_ops(db, BOARD)) == 1


def test_resume_after_restart_falls_back_to_a_full_welcome(store):
    hub = live_hub(store)
    a = hub.connect(BOARD, "A")
    for i in range(3):
        add(hub, a, f"o{i}")
    reopened = live_hub(store)
    b = reopened.connect(BOARD, "B")
    drain(b)
    send(reopened, b, type="resume", lastSeq=1)                      # log is gone after restart
    welcome = drain(b)[0]
    assert welcome["type"] == "welcome" and len(welcome["objects"]) == 3


def test_database_failure_does_not_break_the_live_board(store):
    hub = live_hub(store)
    room = hub.room(BOARD)
    room.listeners.clear()

    def broken():
        raise RuntimeError("db down")
        yield  # pragma: no cover

    persistence.attach_store(room, persistence.opener_from_dependency(broken))
    a = hub.connect(BOARD, "A")
    drain(a)
    add(hub, a, "o1")                                                # must not raise
    assert [m["type"] for m in drain(a)] == ["op"]


# ---- WB-F-030: auto-snapshot driven by the gateway

def test_wb_f_030_auto_snapshot_after_100_ops(store):
    hub = live_hub(store)
    a = hub.connect(BOARD, "A")
    for i in range(99):
        add(hub, a, f"o{i}")
    persistence.flush()
    with store() as db:
        assert snapshots.latest_snapshot(db, BOARD) is None
    add(hub, a, "o99")
    persistence.flush()
    with store() as db:
        snap = snapshots.latest_snapshot(db, BOARD)
        assert snap is not None and snap.is_auto and snap.seq == 100
        assert len(snap.state) == 100
    reopened = live_hub(store)                                       # snapshot + replay loads fine
    assert len(reopened.room(BOARD).objects()) == 100 and reopened.room(BOARD).seq == 100


# ---- loading helpers

def test_room_from_db_of_an_empty_board_is_empty(store):
    with store() as db:
        room = persistence.room_from_db(db, BOARD)
    assert room.seq == 0 and room.objects() == []


def test_objects_from_state_skips_entries_without_a_type():
    objs = persistence.objects_from_state({"a": {"type": "rect", "z": 2, "x": 1}, "b": {"x": 9}})
    assert objs == [{"id": "a", "type": "rect", "z": 2, "props": {"x": 1}}]


def test_load_state_resets_log_so_resume_cannot_replay_stale_ops():
    room = BoardRoom(BOARD)
    room.apply("c", "add", "op1", "o1", {"type": "rect", "z": 0, "props": {"x": 1}})
    room.load_state([], 7)
    assert room.seq == 7 and room.ops_since(0) is None and room.ops_since(7) == []


# ---- restart after a version restore (WB-F-034 + persistence)

def test_restore_then_restart_shows_the_restored_board(client):
    board = client.post("/api/boards", json={"name": "t"}).json()["id"]
    with client.websocket_connect(f"/ws/boards/{board}?name=Asha") as ws:
        ws.receive_json()
        for oid in ("one", "two"):
            ws.send_json({"type": "op:add", "opId": oid, "object": {
                "id": oid, "type": "rect", "z": 0, "props": {"x": 1, "y": 1}}})
        acks = 0
        while acks < 2:
            acks += ws.receive_json()["type"] == "op"
        persistence.flush()
        version = client.post(f"/api/boards/{board}/versions",
                              json={"name": "two objects", "author": "Asha"}).json()["id"]
        ws.send_json({"type": "op:add", "opId": "three", "object": {
            "id": "three", "type": "rect", "z": 0, "props": {"x": 2, "y": 2}}})
        while ws.receive_json()["type"] != "op":
            pass
    persistence.flush()
    assert client.post(f"/api/boards/{board}/versions/{version}/restore",
                       json={"author": "Ben"}).status_code == 201
    app_hub.reset()
    with client.websocket_connect(f"/ws/boards/{board}?name=Ben") as ws:
        welcome = ws.receive_json()
    assert sorted(o["id"] for o in welcome["objects"]) == ["one", "two"]


# ---- validation: 'type' is reserved because it is stored next to the properties

def test_type_cannot_be_used_as_a_property_name():
    import json
    from src.server.gateway import validation
    for msg in (
        {"type": "op:add", "opId": "1", "object": {"id": "a", "type": "rect", "props": {"type": "x"}}},
        {"type": "op:update", "opId": "1", "objectId": "a", "changes": {"type": "text"}},
    ):
        with pytest.raises(validation.InvalidMessage):
            validation.parse(json.dumps(msg))
