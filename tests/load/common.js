// Shared helpers for the k6 load tests (STP section 5.1, TC-Perf-01/02, TC-Sec-04).
// Message formats: SAD section 5.2.
import http from 'k6/http';
import ws from 'k6/ws';
import { check } from 'k6';
import { Counter, Trend } from 'k6/metrics';

export const BASE = __ENV.BASE_URL || 'http://127.0.0.1:8000';
const WS_BASE = BASE.replace(/^http/, 'ws');

// Send-to-receive time of an operation, measured on one clock (all VUs run on this machine).
export const syncLatency = new Trend('sync_latency', true);
export const joins = new Counter('joins');
export const opsSent = new Counter('ops_sent');
export const opsUnacked = new Counter('ops_unacked'); // sent but never echoed back = lost
export const wsErrors = new Counter('ws_errors');
export const unexpectedCloses = new Counter('unexpected_closes');

export function createBoard(name) {
  const res = http.post(`${BASE}/api/boards`, JSON.stringify({ name }), {
    headers: { 'Content-Type': 'application/json' },
  });
  check(res, { 'board created (201)': (r) => r.status === 201 });
  return res.json('id');
}

export function socketUrl(boardId, name) {
  return `${WS_BASE}/ws/boards/${boardId}?name=${encodeURIComponent(name)}`;
}

// One well-behaved participant: joins, adds one object, then edits it opsPerSecond times a
// second for `seconds`. Every update carries its send time (`t`), so every OTHER participant
// can compute the latency when the broadcast arrives.
export function runParticipant(boardId, { name, seconds, opsPerSecond = 5, tag = 'main' }) {
  const pending = {}; // opId -> true until the server echoes our own op back
  const objectId = `obj-${name}`;
  let myId = null;
  let n = 0;
  let sending = false;
  let finishing = false;

  const res = ws.connect(socketUrl(boardId, name), {}, function (socket) {
    const send = (msg) => {
      pending[msg.opId] = true;
      opsSent.add(1);
      socket.send(JSON.stringify(msg));
    };

    socket.on('message', (raw) => {
      const m = JSON.parse(raw);
      if (m.type === 'welcome') {
        myId = m.clientId;
        joins.add(1);
        sending = true;
        send({
          type: 'op:add',
          opId: `${name}-add`,
          object: {
            id: objectId, type: 'rect', z: 0,
            props: { x: 0, y: 0, width: 40, height: 40, colour: '#d62828' },
          },
        });
        socket.setInterval(() => {
          if (!sending) return;
          n += 1;
          send({
            type: 'op:update',
            opId: `${name}-${n}`,
            objectId,
            changes: { x: n % 1000, t: Date.now() },
          });
        }, 1000 / opsPerSecond);
      } else if (m.type === 'op') {
        if (m.clientId === myId) {
          delete pending[m.opId];
        } else if (m.opType === 'update' && m.payload && m.payload.t) {
          syncLatency.add(Date.now() - m.payload.t, { board: tag });
        }
      } else if (m.type === 'error') {
        wsErrors.add(1);
      }
    });
    socket.on('error', () => wsErrors.add(1));
    socket.on('close', () => {
      if (!finishing) unexpectedCloses.add(1);
    });

    socket.setTimeout(() => { sending = false; }, seconds * 1000);
    socket.setTimeout(() => {          // short grace period so the last acks can arrive
      finishing = true;
      opsUnacked.add(Object.keys(pending).length);
      socket.close();
    }, seconds * 1000 + 1500);
  });
  check(res, { 'websocket upgrade (101)': (r) => r && r.status === 101 });
}
