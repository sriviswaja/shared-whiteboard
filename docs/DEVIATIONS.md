# Deviations from the SRS, SAD and Test Plan

Team 11, Shared Whiteboard. Status at development freeze, 30 Oct 2026.
Each item says what the documents say, what was built, and why.

## 1. Functional deviations

| # | Ref | Documents say | What was built | Reason |
|---|-----|---------------|----------------|--------|
| D-1 | WB-F-034, SAD 5.2 | Restoring a version notifies participants with a `version:restored` message | Restore creates the new version and audit entry, then sends every connected client a `board:reset` message (reason `restore`) carrying the restored objects. Behaviour is as required; only the message name differs. | The gateway already had `board:reset` for replacing a whole board; reusing it avoided a second message type. |
| D-2 | SAD 5.x | REST errors use `{"error": {"code": ...}}` | FastAPI's default `{"detail": ...}` is used. WebSocket close codes (4001, 4002, 4003, 4290) are as documented. | Framework default kept; only the body shape differs. |
| D-3 | WB-F-023, TC-Sync-04 | While offline a user can still draw, and the changes merge after reconnecting | The client reconnects automatically (retry after 1, 2, 4... up to 10 s) and takes the latest board state, but the canvas is read-only while disconnected. | Queueing and merging offline edits was out of scope for the sprint. |
| D-4 | WB-F-010 | Strokes are sent as drawn | Strokes longer than about 2,000 points are thinned before sending, to stay inside the gateway's 64 KB message and 5,000-point limits. | Protects the server limits (WB-SR-003) at no visible cost to normal drawing. |

## 2. Verification deviations (Test Plan)

| # | Test cases | Planned | Actual |
|---|-----------|---------|--------|
| D-5 | TC-Draw-01..06, TC-Sync-01/02/04, TC-Ver-01..03 (UI side) | Automated browser tests | Automated with Playwright (`tests/e2e/`, 13 tests, two separate browser sessions per test), on **Chromium only**, and **not run in CI** (they skip when Playwright is not installed). |
| D-6 | TC-Perf-03 (30 fps, 1,000 objects), TC-Compat-01 (Chromium, Firefox, WebKit) | Automated | Not run. |
| D-7 | TC-Ops-01 (99% availability), TC-Sec-01 (TLS scan) | Run against a deployed host | **Not run: the system was not deployed.** `tests/ops/check_tls.sh` implements TC-Sec-01 and is ready to run against a deployment. |
| D-8 | All other cases | pytest and k6 | Implemented as planned: 160 pytest tests, 13 browser tests, and the k6 load tests (TC-Perf-01/02, TC-Sec-04). |

## 3. Process deviations

| # | Planned | Actual |
|---|---------|--------|
| D-9 | Backlog, story points and assignments by 12 Oct; Sprint-1 on 19-23 Oct | Backend work was merged earlier (11 Oct). The canvas UI arrived on 27 Oct and was connected to the server on 30 Oct. The GitHub Project and 32 backlog issues (one per SRS requirement) were created on 30 Oct, so the issue-tracking history does not show the work as it happened. |
| D-10 | Even contribution across the team | Commits were uneven (the version service, CI and docs were mostly done by one member; the UI arrived late). Work was reassigned mid-project. See the commit history. |

## 4. Document updates made

- SAD v1.1 (27 Oct): data model, version API and layout aligned with the implementation.
- SRS and STP: RTM status to be updated with the final results above (pending at time of writing).
