'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { spawn, spawnSync, execFile } = require('node:child_process');
const { promisify } = require('node:util');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const S = require('../../api/_lib/sync-storage');
const exec = promisify(execFile);
const available = spawnSync('redis-server', ['--version']).status === 0 && spawnSync('redis-cli', ['--version']).status === 0;

test('real Redis: atomic compare-and-set, snapshot, deletion, and session gates', { skip: !available, timeout: 15000 }, async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cs-sync-'));
  const socket = path.join(dir, 'redis.sock');
  const server = spawn('redis-server', ['--port', '0', '--unixsocket', socket, '--save', '', '--appendonly', 'no'], { stdio: ['ignore', 'pipe', 'pipe'] });
  try {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Redis startup timeout')), 5000);
      let output = '';
      server.stdout.on('data', (chunk) => { output += chunk; if (/ready to accept connections/i.test(output)) { clearTimeout(timer); resolve(); } });
      server.once('error', (e) => { clearTimeout(timer); reject(e); });
      server.once('exit', (code) => { clearTimeout(timer); reject(new Error('Redis exited: ' + code + ' ' + output)); });
    });
    const cmd = async (...args) => JSON.parse((await exec('redis-cli', ['-s', socket, '--json', ...args.map(String)])).stdout);
    const keys = ['records', 'meta', 'closed', 'session'];
    const evaluate = (script, args = []) => cmd('EVAL', script, 4, ...keys, ...args);
    await cmd('SET', 'session', 'live');
    assert.deepEqual(await evaluate(S.READ), ['ok', '', []]);
    const outcomes = await Promise.all(['one', 'two'].map((value) => evaluate(S.COMMIT, ['', value, JSON.stringify({ record: value })])));
    assert.deepEqual(outcomes.sort(), ['conflict', 'ok']);
    const [status, meta, rows] = await evaluate(S.READ);
    assert.equal(status, 'ok'); assert.deepEqual(rows, ['record', meta]);
    assert.equal(await evaluate(S.COMMIT, [meta, 'deleted', JSON.stringify({ record: null })]), 'ok');
    assert.deepEqual(await evaluate(S.READ), ['ok', 'deleted', []]);
    await cmd('DEL', 'session');
    assert.equal(await evaluate(S.COMMIT, ['deleted', 'bad', '{}']), 'closed');
    await cmd('SET', 'session', 'live');
    await evaluate(S.CLOSE);
    assert.deepEqual(await evaluate(S.READ), ['closed']);
    assert.equal(await cmd('EXISTS', 'meta'), 0);
    assert.equal(await evaluate(S.COMMIT, ['', 'restored', '{}']), 'closed');
  } finally {
    server.kill('SIGTERM');
    if (server.exitCode === null) await new Promise((resolve) => server.once('exit', resolve));
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
