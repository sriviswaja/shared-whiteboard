# Code Coverage Report

Project: Shared Whiteboard (Team 11, Section E). Report date: 05-11-2026.

Code under test: main at 5768ae4 (canvas wired, availability test merged) plus the test-ID fix (tests/e2e and tests/test_restore_notifies.py renamed).

Environment: Python 3.13.16, pytest 9.1.1 (pytest-cov), FastAPI 0.162.0, SQLAlchemy 2.1.6, Playwright with Chromium; Linux; SQLite in memory for the unit and integration tests, SQLite file for the browser tests.

## Summary

| Measure | Covered | Total | Coverage |
|---|---|---|---|
| Statements (lines) | 806 | 830 | **97.1%** |

Scope: all Python code under `src/` (14 source files, 175 tests). The browser code in `src/client/index.html` is exercised by the Playwright tests but is not measured here.

## By file

| File | Statements | Missed | Coverage | Lines not executed |
|---|---|---|---|---|
| `src/__init__.py` | 0 | 0 | 100.0% | - |
| `src/server/__init__.py` | 0 | 0 | 100.0% | - |
| `src/server/api/__init__.py` | 0 | 0 | 100.0% | - |
| `src/server/api/boards.py` | 24 | 0 | 100.0% | - |
| `src/server/api/versions.py` | 58 | 0 | 100.0% | - |
| `src/server/db.py` | 14 | 4 | 71.4% | 19-21, 23 |
| `src/server/gateway/__init__.py` | 0 | 0 | 100.0% | - |
| `src/server/gateway/hub.py` | 142 | 2 | 98.6% | 66-67 |
| `src/server/gateway/persistence.py` | 76 | 0 | 100.0% | - |
| `src/server/gateway/ratelimit.py` | 17 | 0 | 100.0% | - |
| `src/server/gateway/room.py` | 103 | 3 | 97.1% | 109, 116, 145 |
| `src/server/gateway/validation.py` | 89 | 7 | 92.1% | 64, 85, 97, 109, 112-114 |
| `src/server/gateway/ws.py` | 62 | 5 | 91.9% | 69-70, 79, 83-84 |
| `src/server/main.py` | 23 | 3 | 87.0% | 15-16, 30 |
| `src/server/models.py` | 41 | 0 | 100.0% | - |
| `src/server/services/__init__.py` | 0 | 0 | 100.0% | - |
| `src/server/services/board.py` | 13 | 0 | 100.0% | - |
| `src/server/services/board_ops.py` | 27 | 0 | 100.0% | - |
| `src/server/services/merge.py` | 30 | 0 | 100.0% | - |
| `src/server/services/session.py` | 41 | 0 | 100.0% | - |
| `src/server/services/snapshots.py` | 45 | 0 | 100.0% | - |
| `src/server/services/versions.py` | 25 | 0 | 100.0% | - |

## What the uncovered lines are

- **Real application start-up** (`db.py` 19-23, `main.py` 15-16 and 30): the real database session, table creation at start-up and serving the page at `/`. The unit and integration tests replace the database session and do not start the app, while the browser tests do run the real server, but in a separate process that this measurement does not see.
- **Rejection of unusual bad messages** (`validation.py` 64, 85, 97, 109-114): an id that is too long, a non-integer `z`, a number that is not finite, a text value over 200 characters, an unsupported value type. The common bad inputs (malformed JSON, unknown type, oversized message) are covered.
- **Rare gateway cases** (`room.py` 109, 116, 145; `hub.py` 66-67; `ws.py` 69-70, 79, 83-84): forgetting very old operation ids to bound memory, re-using or updating an unknown object id, a full outgoing queue for a slow client, and parts of the connection close sequence.

None of these is on the normal user path. Covering them would need extra negative tests; they are listed as known gaps, not defects.
