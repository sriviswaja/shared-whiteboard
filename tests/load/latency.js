// TC-Perf-01 (WB-NF-001): sync latency.
// 20 virtual users on ONE board, each sending 5 operations per second.
// Pass: p95 send-to-receive <= 300 ms, nothing lost, nobody disconnected.
//
//   k6 run tests/load/latency.js                       # full 5 minute run (STP)
//   k6 run -e SECONDS=30 tests/load/latency.js         # quick check
//   k6 run -e BASE_URL=https://host tests/load/latency.js
import { createBoard, runParticipant } from './common.js';

const SECONDS = parseInt(__ENV.SECONDS || '300', 10);

export const options = {
  scenarios: {
    latency: {
      executor: 'per-vu-iterations',
      vus: 20,
      iterations: 1,
      maxDuration: `${SECONDS + 60}s`,
    },
  },
  thresholds: {
    sync_latency: ['p(95)<=300'],
    ops_unacked: ['count==0'],
    ws_errors: ['count==0'],
    unexpected_closes: ['count==0'],
    joins: ['count==20'],
    checks: ['rate==1'],
  },
};

export function setup() {
  return { board: createBoard('TC-Perf-01') };
}

export default function (data) {
  runParticipant(data.board, { name: `vu${__VU}`, seconds: SECONDS, opsPerSecond: 5 });
}
