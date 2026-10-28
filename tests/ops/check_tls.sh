#!/usr/bin/env bash
# TC-Sec-01 (WB-SR-001): TLS only. Run against the DEPLOYED host, not localhost.
# Usage: bash tests/ops/check_tls.sh whiteboard.example.com
# Needs: openssl, curl. Exit code 0 = all checks passed.
set -u
HOST="${1:?usage: check_tls.sh <host>}"
fail=0

pass() { echo "PASS: $1"; }
bad()  { echo "FAIL: $1"; fail=1; }

# 1. TLS 1.2 and 1.3 are offered
accepted=0
for v in tls1_2 tls1_3; do
  if openssl s_client -connect "$HOST:443" -servername "$HOST" "-$v" </dev/null >/dev/null 2>&1; then
    pass "$v accepted"; accepted=$((accepted + 1))
  else
    bad "$v not accepted"
  fi
done
if [[ $accepted -eq 0 ]]; then
  echo "ABORT: could not complete a TLS handshake with $HOST:443 (wrong host, or not reachable?)"
  exit 2
fi

# 2. Old protocol versions are refused
for v in tls1 tls1_1; do
  if openssl s_client -connect "$HOST:443" -servername "$HOST" "-$v" </dev/null >/dev/null 2>&1; then
    bad "$v is still accepted (must be refused)"
  else
    pass "$v refused"
  fi
done

# 3. Plain HTTP redirects to HTTPS
code=$(curl -s -o /dev/null -m 15 -w '%{http_code}' "http://$HOST/healthz")
loc=$(curl -s -o /dev/null -m 15 -w '%{redirect_url}' "http://$HOST/healthz")
if [[ "$code" =~ ^30[12378]$ && "$loc" == https://* ]]; then
  pass "http:// redirects to https:// ($code)"
else
  bad "http:// did not redirect to https:// (status $code, location '$loc')"
fi

# 4. ws:// (unencrypted WebSocket) is not accepted: anything but 101 Switching Protocols
code=$(curl -s -o /dev/null -m 15 -w '%{http_code}' \
  -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: x3JJHMbDL1EzLkh9GBhXDw==" \
  "http://$HOST/ws/boards/0000")
if [[ "$code" == "101" ]]; then
  bad "ws:// upgrade was accepted (status 101)"
else
  pass "ws:// not upgraded (status $code)"
fi

exit $fail