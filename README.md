# Shared Whiteboard

A real-time collaborative whiteboard: multiple people draw, write and edit on one shared board at the same time, changes sync live, and every board keeps a version history.

Team 11, Section E, PES University (Software Engineering).
Design docs are in [`docs/`](docs): SRS, SAD and Test Plan.

## Status

| Area | State |
|---|---|
| Board creation and lookup (REST + database) | Done |
| Session service (join, leave, 20-participant limit) | Done |
| Persistence (ordered ops, snapshots, state replay) | Done |
| Version history (list, preview, restore, audit log) | Done (backend) |
| Sync gateway (WebSocket, real-time broadcast, rate limiting) | Done |
| Canvas UI (`canvas.html`: pen, shapes, text, eraser, undo/redo, cursors) | Done as a standalone demo (see Known limitations) |
| Load tests (k6) and security tests | Done |

Development is frozen as of 30 Oct 2026. Planned vs delivered differences are listed in [`docs/DEVIATIONS.md`](docs/DEVIATIONS.md). The backlog is tracked in the repository's GitHub Project.

## Quick start

Requires Python 3.11 or newer.

```bash
git clone https://github.com/sriviswaja/shared-whiteboard.git
cd shared-whiteboard

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

pytest                             # run the test suite
uvicorn src.server.main:app --reload
```

To try the canvas, open `canvas.html` in two tabs of the same browser.

The server runs at http://127.0.0.1:8000. Interactive API docs are at http://127.0.0.1:8000/docs. The database is a local SQLite file (`whiteboard.db`, created on first start). Set `DATABASE_URL` to use another database such as PostgreSQL.

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/healthz` | Health check |
| POST | `/api/boards` | Create a board, returns its 128-bit random id |
| GET | `/api/boards/{id}` | Get a board (404 if unknown) |
| POST | `/api/boards/{id}/versions` | Save a named version |
| GET | `/api/boards/{id}/versions` | List versions, newest first (max 50) |
| GET | `/api/boards/{id}/versions/{version_id}` | Preview one version |
| POST | `/api/boards/{id}/versions/{version_id}/restore` | Restore (creates a new version, history is kept) |

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/boards \
     -H "Content-Type: application/json" \
     -d '{"name": "Sprint planning"}'
```

Real-time sync uses a WebSocket at `/ws/boards/{board_id}`.

Anyone with the board link can join, there are no accounts. Error codes used on the WebSocket: 4001 board not found, 4002 board full, 4003 invalid message, 4290 rate limited.

## Project layout

```
src/server/
  main.py          FastAPI app
  db.py            database connection
  models.py        tables (boards, ops, snapshots, audit log)
  api/             HTTP endpoints
  gateway/         WebSocket sync (hub, rooms, validation, rate limiting)
  services/        business logic (sessions, ops, snapshots, versions)
canvas.html        canvas UI (single file)
tests/             pytest tests, test names carry their STP test case id
tests/load/        k6 load tests (latency, capacity, rate limiting)
tests/ops/         TLS check script (TC-Sec-01)
docs/              SRS, SAD, Test Plan, deviations
```

## Testing

Every feature has a test whose name includes its test case id from the Test Plan, so you can run one area at a time:

```bash
pytest -k tc_ver        # version history tests
pytest -k tc_board_04   # a single test case
```

The security tests are in `tests/test_security.py`. Load tests are described in `tests/load/README.md`.

CI (GitHub Actions) runs the whole suite on every push and pull request.

## Contributing

1. `git checkout main && git pull`
2. Create a branch per feature: `git checkout -b feature/<name>`
3. Add a test for the feature, run `pytest` locally
4. Push and open a pull request into `main`
5. A teammate other than the author must approve it, and CI must pass before merging

`main` is protected: no direct pushes.

## Known limitations

- `canvas.html` currently syncs between tabs of the same browser (BroadcastChannel). It is not yet connected to the server's WebSocket gateway.
- Restoring a version through the REST API does not notify connected clients; they see it on reload.
- UI behaviour (TC-Draw), 30 fps and cross-browser checks were verified manually, not with automated tests.
- TC-Ops-01 and TC-Sec-01 were not run because the system was not deployed.

See [`docs/DEVIATIONS.md`](docs/DEVIATIONS.md) for details.

## Team

| Name | Area |
|---|---|
| Sriviswaja M | Version history, CI, docs |
| Samhitha | Canvas UI |
| Shloka | Sync gateway |
| Sushir | Persistence, tests, performance |