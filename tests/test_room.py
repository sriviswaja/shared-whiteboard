import pytest

from src.server.services.room import InvalidOpError, Room


def add(oid, **data):
    return {"kind": "add", "id": oid, "data": data}


def test_tc_sync_01_sequence_numbers_increase():
    r = Room()
    assert [r.apply(add(f"o{i}")) for i in range(3)] == [1, 2, 3]


def test_tc_sync_03_last_write_wins():
    r = Room()
    r.apply(add("o1", x=1))
    r.apply({"kind": "update", "id": "o1", "data": {"x": 2}})
    r.apply({"kind": "update", "id": "o1", "data": {"x": 3}})
    assert r.snapshot() == [{"id": "o1", "data": {"x": 3}}]


def test_tc_sync_03_update_after_delete_is_ignored():
    r = Room()
    r.apply(add("o1", x=1))
    r.apply({"kind": "delete", "id": "o1"})
    r.apply({"kind": "update", "id": "o1", "data": {"x": 9}})
    assert r.snapshot() == []


def test_tc_sync_03_delete_unknown_object_is_harmless():
    r = Room()
    r.apply({"kind": "delete", "id": "ghost"})
    assert r.snapshot() == []


@pytest.mark.parametrize(
    "bad",
    [
        "not a dict",
        {"kind": "explode", "id": "a"},
        {"kind": "add"},
        {"kind": "add", "id": ""},
        {"kind": "add", "id": "a", "data": "nope"},
    ],
)
def test_invalid_ops_rejected(bad):
    with pytest.raises(InvalidOpError):
        Room().apply(bad)