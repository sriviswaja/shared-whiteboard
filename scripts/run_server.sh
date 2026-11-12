#!/usr/bin/env bash
# Keeps the server running: if it exits for any reason it is started again
# after 1 second (WB-NF-003). Stop it with Ctrl+C.
# Run from the repo root with the virtualenv active:  bash scripts/run_server.sh
# Options (environment variables): HOST (default 0.0.0.0), PORT (default 8000)
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
child=""
trap 'kill "$child" 2>/dev/null; exit 0' INT TERM
while true; do
  uvicorn src.server.main:app --host "$HOST" --port "$PORT" &
  child=$!
  wait "$child"
  echo "server exited (code $?), restarting in 1 s" >&2
  sleep 1
done
