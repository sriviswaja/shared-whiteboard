// TC-Perf-02 (WB-NF-002): 20 users on one board while 5 other boards are active.
// Pass: no errors or disconnects, and the TC-Perf-01 latency target still holds.
//
//   k6 run tests/load/capacity.js
//   k6 run -e SECONDS=30 tests/load/capacity.js
import { createBoard, runParticipant } from './common.js';

const SECONDS = parseInt(__ENV.SECONDS || '300', 10);
const OTHER_BOARDS = 5;
const USERS_PER_OTHER_BOARD = 2;
const maxDuration = `${SECONDS + 60}s`;

export const options = {
  scenarios: {
    busy_board: { executor: 'per-vu-iterations', exec: 'busy', vus: 20, iterations: 1, maxDuration },
    other_boards: {
      executor: 'per-vu-iterations', exec: 'others',
      vus: OTHER_BOARDS * USERS_PER_OTHER_BOARD, iterations: 1, maxDuration,
    },
  },
  thresholds: {
    'sync_latency{board:busy}': ['p(95)<=300'],
    'sync_latency{board:other}': ['p(95)<=300'],
    ops_unacked: ['count==0'],
    ws_errors: ['count==0'],
    unexpected_closes: ['count==0'],
    joins: [`count==${20 + OTHER_BOARDS * USERS_PER_OTHER_BOARD}`],
    checks: ['rate==1'],
  },
};

export function setup() {
  const busy = createBoard('TC-Perf-02 busy');
  const others = [];
  for (let i = 0; i < OTHER_BOARDS; i++) others.push(createBoard(`TC-Perf-02 other ${i + 1}`));
  return { busy, others };
}

export function busy(data) {
  runParticipant(data.busy, { name: `busy${__VU}`, seconds: SECONDS, tag: 'busy' });
}

export function others(data) {
  const board = data.others[(__VU - 1) % OTHER_BOARDS];
  runParticipant(board, { name: `other${__VU}`, seconds: SECONDS, tag: 'other' });
}
