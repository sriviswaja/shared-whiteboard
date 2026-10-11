# Load tests (k6)

Performance and rate-limit tests from the Test Plan (STP section 5). They run against a
live server, not through pytest (`pytest` ignores this folder).

| File | Test case | Requirement | Pass criteria |
|---|---|---|---|
| `latency.js` | TC-Perf-01 | WB-NF-001 | 20 users, 1 board, 5 ops/s each for 5 min: p95 send-to-receive <= 300 ms, no op lost, no disconnect |
| `capacity.js` | TC-Perf-02 | WB-NF-002 | 20 users on one board plus 10 users on 5 other boards: no errors or disconnects, p95 <= 300 ms on every board |
| `ratelimit.js` | TC-Sec-04 | WB-SR-004 | One client floods 500 msg/s for 10 s: it gets error 4290 and is disconnected, got <= 150 replies; 4 normal users keep p95 <= 300 ms |

A run passes when k6 prints green ticks on every threshold and exits with code 0
(`✗` and exit code 99 mean a threshold failed).

## Run

1. Install k6: Windows `winget install k6 --source winget` (or `choco install k6`); macOS `brew install k6`.
2. Start a fresh server in one terminal (a fresh database avoids old boards and snapshots skewing the numbers):

   ```powershell
   Remove-Item load.db -ErrorAction SilentlyContinue
   $env:DATABASE_URL = "sqlite:///./load.db"
   uvicorn src.server.main:app --port 8000
   ```

3. In a second terminal:

   ```powershell
   k6 run tests/load/latency.js                    # TC-Perf-01, 5 minutes
   k6 run tests/load/capacity.js                   # TC-Perf-02, 5 minutes
   k6 run tests/load/ratelimit.js                  # TC-Sec-04, about 30 seconds
   k6 run -e SECONDS=30 tests/load/latency.js      # quick check while developing
   k6 run -e BASE_URL=https://your-host tests/load/latency.js   # a deployed instance
   ```

Run the server and k6 on the same machine so one clock measures send and receive.
The exit criteria in the STP ask for two consecutive passing runs.

## How latency is measured

Every update carries `Date.now()` in its `t` field. When another user receives that
broadcast, `sync_latency = Date.now() - t`. Echoes of a user's own operations are used
only to detect lost operations (`ops_unacked` must be 0).

## Reference results (Linux container, one machine, server and k6 together)

| Test | Result |
|---|---|
| TC-Perf-01 (300 s, 30,000 ops) | p95 14 ms, max 110 ms, 0 lost, 0 disconnects |
| TC-Perf-02 (30 users, 6 boards) | p95 6 ms busy board, 5 ms other boards, 0 lost |
| TC-Sec-04 | flooder got 82 replies, error 4290 and disconnect; normal users p95 37 ms |

Your laptop will differ. Record your own numbers in the Test Summary Report.
