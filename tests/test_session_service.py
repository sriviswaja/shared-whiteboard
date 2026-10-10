import pytest

from src.server.services.session import (
    MAX_PARTICIPANTS,
    BoardFullError,
    InvalidNameError,
    SessionService,
)

BOARD = "board-a"


def fill(svc, board_id, count):
    return [svc.join(board_id, f"user{i}") for i in range(count)]


# ---- TC-Board-02: join with a display name (WB-F-002)

def test_tc_board_02_valid_name_joins():
    svc = SessionService()
    p = svc.join(BOARD, "Asha")
    assert p.name == "Asha"
    assert p.client_id
    assert svc.is_member(BOARD, p.client_id)


@pytest.mark.parametrize("bad_name", ["", "   ", None, "x" * 31])
def test_tc_board_02_invalid_name_rejected(bad_name):
    svc = SessionService()
    with pytest.raises(InvalidNameError):
        svc.join(BOARD, bad_name)
    assert svc.participants(BOARD) == []


def test_tc_board_02_name_of_30_characters_is_accepted():
    svc = SessionService()
    assert svc.join(BOARD, "x" * 30).name == "x" * 30


def test_tc_board_02_name_is_trimmed():
    svc = SessionService()
    assert svc.join(BOARD, "  Asha  ").name == "Asha"


# ---- TC-Board-03: participants list (WB-F-003)

def test_tc_board_03_participants_follow_join_and_leave():
    svc = SessionService()
    a = svc.join(BOARD, "A")
    b = svc.join(BOARD, "B")
    assert [p.name for p in svc.participants(BOARD)] == ["A", "B"]
    assert svc.leave(BOARD, b.client_id) is True
    assert [p.name for p in svc.participants(BOARD)] == ["A"]
    assert svc.leave(BOARD, b.client_id) is False  # already gone
    assert svc.is_member(BOARD, a.client_id)


# ---- TC-Board-04: 20-participant limit (WB-F-004)

def test_tc_board_04_21st_participant_is_refused():
    svc = SessionService()
    fill(svc, BOARD, MAX_PARTICIPANTS)
    with pytest.raises(BoardFullError) as err:
        svc.join(BOARD, "late")
    assert err.value.code == 4002
    assert len(svc.participants(BOARD)) == MAX_PARTICIPANTS


def test_tc_board_04_slot_frees_when_someone_leaves():
    svc = SessionService()
    people = fill(svc, BOARD, MAX_PARTICIPANTS)
    svc.leave(BOARD, people[0].client_id)
    assert svc.join(BOARD, "late").name == "late"


def test_tc_board_04_boards_are_independent():
    svc = SessionService()
    fill(svc, BOARD, MAX_PARTICIPANTS)
    assert svc.join("board-b", "Asha").name == "Asha"


# ---- TC-Sec-06: membership check (WB-SR-006)

def test_tc_sec_06_is_member_only_for_the_joined_board_and_client():
    svc = SessionService()
    p = svc.join(BOARD, "Asha")
    assert svc.is_member(BOARD, p.client_id) is True
    assert svc.is_member("board-b", p.client_id) is False
    assert svc.is_member(BOARD, "unknown") is False
    svc.leave(BOARD, p.client_id)
    assert svc.is_member(BOARD, p.client_id) is False


def test_client_ids_are_unique():
    svc = SessionService()
    ids = {p.client_id for p in fill(svc, BOARD, MAX_PARTICIPANTS)}
    assert len(ids) == MAX_PARTICIPANTS
