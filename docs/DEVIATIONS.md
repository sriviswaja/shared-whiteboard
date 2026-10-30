# Deviations from the SRS, SAD and Test Plan

Team 11, Shared Whiteboard. Status at development freeze, 30 Oct 2026.
Each item says what the documents say, what was built, and why.

## 1. Functional deviations

| # | Ref | Documents say | What was built | Reason / plan |
|---|-----|---------------|----------------|---------------|
| D-1 | WB-F-034 | Restoring a version creates a new version and **notifies all participants** | Restore creates the new version and an audit-log entry (WB-SR-005), but connected clients are **not** notified. They see the restored state when they reload or rejoin. `hub.board_reset` exists but the REST endpoint does not call it, and the `version:restored` message is not implemented. | Not completed within the sprint. Known gap; the fix is to call `hub.board_reset` from the restore endpoint. |
| D-2 | WB-F-033 | Read-only preview of any version | The backend can return the stored state of any version (REST), but the canvas UI has no read-only preview mode. | Not completed within the sprint; the UI work was prioritised on drawing and sync. |
| D-3 | SAD 5.x | REST errors use `{"error": {"code": ...}}` | FastAPI's default `{"detail": ...}` is used. WebSocket close codes (4001, 4002, 4003, 4290) are as documented. | Framework default kept; behaviour is equivalent, only the body shape differs. |

## 2. Structural deviations

| # | Ref | Documents say | What was built | Reason |
|---|-----|---------------|----------------|--------|
| D-4 | SAD layout | Client code lives under `src/client/` and is served by FastAPI | The canvas UI is a single file, `canvas.html`, at the repo root, opened directly and connecting to the server over WebSocket | The UI was delivered as one self-contained page; moving and serving it was not done before the freeze. |

## 3. Verification deviations (Test Plan)

| # | Test cases | Planned | Actual |
|---|-----------|---------|--------|
| D-5 | TC-Draw-01..06 | Automated Playwright tests | Verified **manually** in two browser windows (pen, shapes, text, select/move/resize/delete, eraser, undo/redo all work). No automated tests. |
| D-6 | TC-Perf-03 (30 fps), TC-Compat-01 (Chromium, Firefox, WebKit) | Automated | Not run. |
| D-7 | TC-Ops-01 (99% availability), TC-Sec-01 (TLS scan) | Run against a deployed host | **Not run: the system was not deployed.** `tests/ops/check_tls.sh` implements TC-Sec-01 and is ready to run against a deployment. |
| D-8 | All other cases | pytest and k6 | Implemented as planned: 158 automated tests plus k6 load tests (TC-Perf-01/02, TC-Sec-04) pass in CI. |

## 4. Process deviations

| # | Planned | Actual |
|---|---------|--------|
| D-9 | Backlog, story points and assignments by 12 Oct; Sprint-1 on 19-23 Oct | Backend work was merged earlier (11 Oct) and the UI on 27 Oct. The GitHub Project and 32 backlog issues (one per SRS requirement) were created on 30 Oct, so issue-tracking history does not show the work as it happened. |
| D-10 | Even contribution across the team | Commits were uneven (the version service, CI and docs were mostly done by one member; the UI arrived late). Work was reassigned mid-project. See the commit history. |


## 5. Document updates made

- SAD v1.1 (27 Oct): data model, version API and layout aligned with the implementation.
- SRS and STP: RTM status to be updated with the final results above (pending at time of writing).
