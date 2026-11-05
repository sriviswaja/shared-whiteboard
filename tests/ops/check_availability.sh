#!/usr/bin/env bash
# TC-Ops-01 (WB-NF-003): the server comes back by itself after it is killed.
#
# Starts the server under scripts/run_server.sh, creates a board, kills the
# uvicorn process with kill -9 and measures how long /healthz is down.
# Pass: healthy again within MAX_RESTART seconds (default 30) and the board
# created before the kill is still there afterwards (WB-F-040).
#
# Run from the repo root with the virtualenv active:
#   bash tests/ops/check_availability.sh
# Options (environment variables): PORT, HEALTH_PATH, MAX_RESTART
set -u

PORT="${PORT:-8010}"
HEALTH_PATH="${HEALTH_PATH:-/healthz}"
MAX_RESTART="${MAX_RESTART:-30}"
BASE="http://127.0.0.1:${PORT}"
URL="${BASE}${HEALTH_PATH}"
DB_FILE="$(mktemp -t wb-availability.XXXXXX)"
export DATABASE_URL="sqlite:///${DB_FILE}"
export PORT
export HOST="127.0.0.1"
LOG="$(mktemp -t wb-availability-log.XXXXXX)"
SUP=""

code() { curl -s -o /dev/null -m 2 -w '%{http_code}' "$1" 2>/dev/null; }
now()  { python3 -c 'import time; print(int(time.time()*1000))'; }
cleanup() {
  if [ -n "$SUP" ]; then
    kill "$SUP" 2>/dev/null
    { wait "$SUP"; } 2>/dev/null
  fi
  rm -f "$DB_FILE" "${DB_FILE}"* "$LOG"
}
fail() {
  echo "FAIL: $1"
  if [ -s "$LOG" ]; then echo "--- last server output ---"; tail -n 20 "$LOG"; fi
  exit 1
}
trap cleanup EXIT

command -v uvicorn >/dev/null || fail "uvicorn not found. Activate the virtualenv first."

echo "Starting the server under scripts/run_server.sh on port ${PORT} ..."
bash scripts/run_server.sh >"$LOG" 2>&1 &
SUP=$!

for i in $(seq 1 60); do
  [ "$(code "$URL")" = "200" ] && break
  sleep 0.5
done
[ "$(code "$URL")" = "200" ] || fail "server never became healthy at ${URL}"

BOARD_ID="$(curl -s -m 5 -X POST "${BASE}/api/boards" -H 'Content-Type: application/json' \
  -d '{"name":"availability"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])' 2>/dev/null)"
[ -n "$BOARD_ID" ] || fail "could not create a board"
echo "Created board ${BOARD_ID}"

PID=""
if command -v lsof >/dev/null; then
  PID="$(lsof -ti "tcp:${PORT}" -sTCP:LISTEN 2>/dev/null | head -1)"
fi
[ -n "$PID" ] || PID="$(pgrep -f "uvicorn src.server.main:app.*--port ${PORT}" | head -1)"
[ -n "$PID" ] || fail "could not find the server process"
echo "Killing server process ${PID} (kill -9) ..."
T_KILL="$(now)"
kill -9 "$PID"

down=0
for i in $(seq 1 50); do
  if [ "$(code "$URL")" != "200" ]; then down=1; break; fi
  sleep 0.1
done
[ "$down" = "1" ] || fail "server still answered after kill -9"

for i in $(seq 1 600); do
  [ "$(code "$URL")" = "200" ] && break
  sleep 0.2
done
T_UP="$(now)"
[ "$(code "$URL")" = "200" ] || fail "server did not come back within 2 minutes"

OUT_MS=$((T_UP - T_KILL))
OUT_S="$(awk "BEGIN{printf \"%.1f\", ${OUT_MS}/1000}")"
ALLOWED="$(awk "BEGIN{printf \"%d\", (30*86400*0.01)/(${OUT_MS}/1000)}")"
echo "Outage: ${OUT_S} s (limit ${MAX_RESTART} s)"
echo "A 99% month (30 days) allows about ${ALLOWED} outages of this length."

[ "$OUT_MS" -le $((MAX_RESTART * 1000)) ] || fail "restart took ${OUT_S} s, limit is ${MAX_RESTART} s"
[ "$(code "${BASE}/api/boards/${BOARD_ID}")" = "200" ] || fail "board ${BOARD_ID} is gone after the restart"

echo "PASS: restarted in ${OUT_S} s and the board survived."
