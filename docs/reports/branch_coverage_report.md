# Branch Coverage Report

Project: Shared Whiteboard (Team 11, Section E). Report date: 05-11-2026.

Code under test: main at 5768ae4 (canvas wired, availability test merged) plus the test-ID fix (tests/e2e and tests/test_restore_notifies.py renamed).

Environment: Python 3.13.16, pytest 9.1.1 (pytest-cov), FastAPI 0.162.0, SQLAlchemy 2.1.6, Playwright with Chromium; Linux; SQLite in memory for the unit and integration tests, SQLite file for the browser tests.

## Summary

| Measure | Covered | Total | Coverage |
|---|---|---|---|
| Branches | 188 | 204 | **92.2%** |
| Partially covered branch points | 14 | | |
| Missing branch outcomes | 16 | | |

A branch is each outcome (true or false) of an `if`, loop or exception handler. Measured with `pytest --cov-branch` over `src/`.

## By file

| File | Branches | Covered | Coverage | Branches not taken (line -> line) |
|---|---|---|---|---|
| `src/__init__.py` | 0 | 0 | 100.0% | - |
| `src/server/__init__.py` | 0 | 0 | 100.0% | - |
| `src/server/api/__init__.py` | 0 | 0 | 100.0% | - |
| `src/server/api/boards.py` | 2 | 2 | 100.0% | - |
| `src/server/api/versions.py` | 8 | 8 | 100.0% | - |
| `src/server/db.py` | 0 | 0 | 100.0% | - |
| `src/server/gateway/__init__.py` | 0 | 0 | 100.0% | - |
| `src/server/gateway/hub.py` | 36 | 36 | 100.0% | - |
| `src/server/gateway/persistence.py` | 14 | 13 | 92.9% | 91->96 |
| `src/server/gateway/ratelimit.py` | 2 | 2 | 100.0% | - |
| `src/server/gateway/room.py` | 28 | 25 | 89.3% | 108->109, 115->116, 144->145 |
| `src/server/gateway/validation.py` | 58 | 50 | 86.2% | 63->64, 84->85, 96->97, 108->109, 110->113, 111->112, 113->92, 113->114 |
| `src/server/gateway/ws.py` | 10 | 7 | 70.0% | 68->69, 76->80, 77->79 |
| `src/server/main.py` | 0 | 0 | 100.0% | - |
| `src/server/models.py` | 0 | 0 | 100.0% | - |
| `src/server/services/__init__.py` | 0 | 0 | 100.0% | - |
| `src/server/services/board.py` | 0 | 0 | 100.0% | - |
| `src/server/services/board_ops.py` | 10 | 9 | 90.0% | 52->47 |
| `src/server/services/merge.py` | 20 | 20 | 100.0% | - |
| `src/server/services/session.py` | 8 | 8 | 100.0% | - |
| `src/server/services/snapshots.py` | 6 | 6 | 100.0% | - |
| `src/server/services/versions.py` | 2 | 2 | 100.0% | - |

Files with no branches (plain data or declarations) show 100%.

## Combined (statements + branches)

coverage.py's combined figure is 96.1% (994 of 1034).
