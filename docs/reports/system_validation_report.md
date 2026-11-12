# System Validation Report

Project: Shared Whiteboard (Team 11, Section E). Report date: 05-11-2026.

Code under test: main at 5768ae4 (canvas wired, availability test merged) plus the test-ID fix (tests/e2e and tests/test_restore_notifies.py renamed).

Environment: Python 3.13.16, pytest 9.1.1 (pytest-cov), FastAPI 0.162.0, SQLAlchemy 2.1.6, Playwright with Chromium; Linux; SQLite in memory for the unit and integration tests, SQLite file for the browser tests.

## Summary

Each SRS requirement is validated by running the test cases the STP assigns to it (requirements traceability matrix, STP section 13). Results come from the automated runs in this report (pytest and Playwright) and from the k6 load runs recorded in STP section 13.3.

| Result | Requirements |
|---|---|
| Validated | 29 of 32 |
| Partly validated | 1 of 32 |
| Not validated | 2 of 32 |
| Failed | 0 of 32 |

## Requirement by requirement

| SRS ID | Requirement | Test cases | Result | Evidence |
|---|---|---|---|---|
| WB-F-001 | Create board | TC-Board-01 | **VALIDATED** | TC-Board-01: Pass (13 automated tests) |
| WB-F-002 | Join via link | TC-Board-02 | **VALIDATED** | TC-Board-02: Pass (13 automated tests) |
| WB-F-003 | Active participants | TC-Board-03 | **VALIDATED** | TC-Board-03: Pass (3 automated tests) |
| WB-F-004 | 20-user limit | TC-Board-04 | **VALIDATED** | TC-Board-04: Pass (5 automated tests) |
| WB-F-010 | Pen tool | TC-Draw-01 | **VALIDATED** | TC-Draw-01: Pass (1 automated test) |
| WB-F-011 | Shapes | TC-Draw-02 | **VALIDATED** | TC-Draw-02: Pass (1 automated test) |
| WB-F-012 | Text boxes | TC-Draw-03 | **VALIDATED** | TC-Draw-03: Pass (2 automated tests) |
| WB-F-013 | Select / move / resize / delete | TC-Draw-04 | **VALIDATED** | TC-Draw-04: Pass (2 automated tests) |
| WB-F-014 | Eraser | TC-Draw-05 | **VALIDATED** | TC-Draw-05: Pass (1 automated test) |
| WB-F-015 | Undo / redo | TC-Draw-06 | **VALIDATED** | TC-Draw-06: Pass (1 automated test) |
| WB-F-020 | Real-time broadcast | TC-Sync-01 | **VALIDATED** | TC-Sync-01: Pass (5 automated tests) |
| WB-F-021 | Remote cursors | TC-Sync-02 | **VALIDATED** | TC-Sync-02: Pass (3 automated tests) |
| WB-F-022 | Conflict resolution (LWW) | TC-Sync-03 | **VALIDATED** | TC-Sync-03: Pass (5 automated tests) |
| WB-F-023 | Reconnect and resync | TC-Sync-04 | **VALIDATED** | TC-Sync-04: Pass (7 automated tests) |
| WB-F-030 | Auto-snapshot | TC-Ver-01 | **VALIDATED** | TC-Ver-01: Pass (3 automated tests) |
| WB-F-031 | Named snapshot | TC-Ver-02 | **VALIDATED** | TC-Ver-02: Pass (3 automated tests) |
| WB-F-032 | Version list | TC-Ver-03 | **VALIDATED** | TC-Ver-03: Pass (2 automated tests) |
| WB-F-033 | Preview version | TC-Ver-04 | **VALIDATED** | TC-Ver-04: Pass (3 automated tests) |
| WB-F-034 | Restore version | TC-Ver-05 | **VALIDATED** | TC-Ver-05: Pass (6 automated tests) |
| WB-F-040 | Board persistence | TC-Persist-01 | **VALIDATED** | TC-Persist-01: Pass (3 automated tests) |
| WB-NF-001 | Sync latency <= 300 ms | TC-Perf-01 | **VALIDATED** | TC-Perf-01: Pass (k6 5-minute runs by the QA Lead, STP 13.3) |
| WB-NF-002 | 20 users per board | TC-Perf-02 | **VALIDATED** | TC-Perf-02: Pass (k6 5-minute run by the QA Lead, STP 13.3) |
| WB-NF-003 | 99% availability | TC-Ops-01 | **PARTLY** | TC-Ops-01: Restart check run (tests/ops/check_availability.sh): server killed with kill -9 restarted in 1.7 s and the board survived; 99% monthly uptime not measured (system not deployed) |
| WB-NF-004 | Convergence within 2 s | TC-Sync-05 | **VALIDATED** | TC-Sync-05: Pass (22 automated tests) |
| WB-NF-005 | Browser compatibility | TC-Compat-01 | **VALIDATED** | TC-Compat-01: Pass (15 automated E2E tests executed across Chromium, Firefox and WebKit; 45 passed, 0 failed) |
| WB-NF-006 | 30 fps rendering | TC-Perf-03 | **NOT VALIDATED** | TC-Perf-03: Not run |
| WB-SR-001 | TLS 1.2+ | TC-Sec-01 | **NOT VALIDATED** | TC-Sec-01: Not run (script ready, system not deployed) |
| WB-SR-002 | Unguessable board IDs | TC-Sec-02 | **VALIDATED** | TC-Sec-02: Pass (7 automated tests) |
| WB-SR-003 | Input validation / XSS | TC-Sec-03 | **VALIDATED** | TC-Sec-03: Pass (14 automated tests) |
| WB-SR-004 | Rate limiting | TC-Sec-04 | **VALIDATED** | TC-Sec-04: Pass (4 automated tests) |
| WB-SR-005 | Append-only history | TC-Sec-05 | **VALIDATED** | TC-Sec-05: Pass (3 automated tests) |
| WB-SR-006 | Per-message membership check | TC-Sec-06 | **VALIDATED** | TC-Sec-06: Pass (3 automated tests) |

## Requirements not fully validated, and why

- **WB-NF-003** (PARTLY): TC-Ops-01: Restart check run (tests/ops/check_availability.sh): server killed with kill -9 restarted in 1.7 s and the board survived; 99% monthly uptime not measured (system not deployed)
- **WB-NF-006** (NOT VALIDATED): TC-Perf-03: Not run
- **WB-SR-001** (NOT VALIDATED): TC-Sec-01: Not run (script ready, system not deployed)

These gaps are also recorded in `docs/DEVIATIONS.md` (D-6 and D-7): the 30 fps check was not run, the TLS check needs a deployed host, and the availability requirement was checked for restart only (monthly uptime needs a deployment).

## System-level scenarios exercised in real browsers

Two separate browser sessions on one board (Playwright across Chromium, Firefox, WebKit): drawing with every tool syncs to the other user; live cursors with names; a late joiner receives the existing board; a disconnected client is read-only, reconnects and receives the latest state; save, list, preview (read-only) and restore versions, with the other user updated at once. See `tests/e2e/test_canvas_sync.py`, `scripts/run_cross_browser.py`, and the results in the unit test report.
