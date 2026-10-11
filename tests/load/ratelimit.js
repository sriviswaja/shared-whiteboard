// TC-Sec-04 (WB-SR-004): rate limiting.
// One client floods 500 messages a second for 10 s while others work normally.
// Pass: the flooder is throttled to about 60 a second and gets error 4290 (and is
// disconnected if it keeps going); everyone else keeps p95 latency <= 300 ms.
//
//   k6 run tests/load/ratelimit.js
import ws from 'k6/ws';
import { check } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { createBoard, runParticipant, socketUrl } from './common.js';

const FLOOD_SECONDS = 10;
const NORMAL_USERS = 4;
const FLOOD_PER_SECOND = 500;

const flooderGot4290 = new Rate('flooder_got_4290');
const flooderClosed4290 = new Rate('flooder_closed_4290');
const flooderPongs = new Trend('flooder_pongs'); // replies the flooder actually got

export const options = {
  scenarios: {
    flooder: { executor: 'per-vu-iterations', exec: 'flooder', vus: 1, iterations: 1, maxDuration: '60s' },
    normal: {
      executor: 'per-vu-iterations', exec: 'normal', vus: NORMAL_USERS, iterations: 1, maxDuration: '90s',
    },
  },
  thresholds: {
    'sync_latency{board:normal}': ['p(95)<=300'],
    flooder_got_4290: ['rate==1'],
    flooder_closed_4290: ['rate==1'],
    // 500/s for up to 10 s would be 5000 replies; throttling must keep this far below that
    // (first-second burst of 60 plus a little refill before the 4290 disconnect).
    flooder_pongs: ['max<=150'],
    ops_unacked: ['count==0'],
    unexpected_closes: ['count==0'],
    checks: ['rate==1'],
  },
};

export function setup() {
  return { board: createBoard('TC-Sec-04') };
}

export function normal(data) {
  runParticipant(data.board, { name: `normal${__VU}`, seconds: FLOOD_SECONDS + 5, tag: 'normal' });
}

export function flooder(data) {
  let pongs = 0;
  let got4290 = false;
  let closeCode = null;
  ws.connect(socketUrl(data.board, 'flooder'), {}, function (socket) {
    socket.on('open', () => {
      socket.setInterval(() => {
        for (let i = 0; i < FLOOD_PER_SECOND / 100; i++) socket.send('{"type":"ping"}');
      }, 10); // 5 messages every 10 ms = 500 a second
    });
    socket.on('message', (raw) => {
      const m = JSON.parse(raw);
      if (m.type === 'pong') pongs += 1;
      if (m.type === 'error' && m.code === 4290) got4290 = true;
    });
    socket.on('close', (code) => { closeCode = code; });
    socket.setTimeout(() => socket.close(), FLOOD_SECONDS * 1000);
  });
  flooderPongs.add(pongs);
  flooderGot4290.add(got4290);
  flooderClosed4290.add(closeCode === 4290);
  check(null, { 'flooder was throttled well below 500/s': () => pongs <= 150 });
}
