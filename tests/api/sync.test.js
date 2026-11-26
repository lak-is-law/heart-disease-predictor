'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
process.env.SESSION_SECRET = 'sync-test-secret-'.repeat(4);
process.env.DATA_ENCRYPTION_KEY = crypto.randomBytes(32).toString('base64');
delete process.env.UPSTASH_REDIS_REST_URL; delete process.env.KV_REST_API_URL;
delete process.env.VERCEL; process.env.NODE_ENV = 'test';
const db = require('../../api/_lib/db');
const sync = require('../../api/_lib/assessment-sync');
const C = require('../../api/_lib/crypto');
const S = require('../../api/_lib/sync-storage');
const body = { inputs: { age: 58 }, risk: 0.4, label: 'Synthetic', model: 'test' };
async function session(uid) { const s = { uid, hash: crypto.randomUUID() }; await db.set('s:' + s.hash, 'session', 60); return s; }
function create(s, operation, changes = {}) { return sync.mutate(s, { action: 'create', body, operation, ...changes }); }

test('simultaneous retried creates commit once and reject changed payloads', async () => {
  const s = await session('retries');
  const results = await Promise.all(Array.from({ length: 6 }, () => create(s, 'same-operation')));
  assert.equal(new Set(results.map((r) => r.item.id)).size, 1);
  assert.equal(results.filter((r) => !r.replayed).length, 1);
  assert.equal((await sync.list(s)).total, 1);
  await assert.rejects(create(s, 'same-operation', { body: { ...body, risk: 0.9 } }), { status: 409 });
  const meta = await db.get('sync:' + s.uid);
  assert.match(meta, /^v1\./); assert.ok(!meta.includes('Synthetic'));
});

test('concurrent edits enforce revisions and deltas include deletion', async () => {
  const s = await session('versions');
  const initial = await sync.list(s);
  const { item } = await create(s, 'create');
  const delta = await sync.list(s, initial.cursor);
  assert.equal(delta.items.length, 1); assert.equal(delta.full, false);
  const attempts = await Promise.allSettled([0.2, 0.8].map((risk) => sync.mutate(s, { action: 'update', id: item.id, body: { ...body, risk }, expectedRevision: 1 })));
  assert.equal(attempts.filter((r) => r.status === 'fulfilled').length, 1);
  assert.equal(attempts.find((r) => r.status === 'rejected').reason.status, 409);
  const updated = await sync.list(s, delta.cursor);
  assert.equal(updated.items[0].revision, 2);
  await assert.rejects(sync.mutate(s, { action: 'delete', id: item.id, expectedRevision: 1 }), { status: 409 });
  await sync.mutate(s, { action: 'delete', id: item.id, expectedRevision: 2 });
  assert.deepEqual((await sync.list(s, updated.cursor)).deleted, [item.id]);
  const retry = await create(s, 'create');
  assert.equal(retry.deleted, true); assert.equal(retry.item, null);
  await assert.rejects(sync.mutate(s, { action: 'update', id: item.id, body, expectedRevision: 2 }), { status: 404 });
  assert.equal((await sync.list(s)).total, 0);
});

test('cursors, records, and operations are isolated across owners', async () => {
  const a = await session('owner-a'), b = await session('owner-b');
  const { item } = await create(a, 'shared-key');
  await assert.rejects(sync.list(b, (await sync.list(a)).cursor), { status: 400 });
  await assert.rejects(sync.mutate(b, { action: 'delete', id: item.id }), { status: 404 });
  assert.equal((await sync.list(b)).total, 0);
  assert.equal((await create(b, 'shared-key')).replayed, false);
});

test('existing records beyond 500 remain readable and corrupt records are reported', async () => {
  const s = await session('legacy');
  for (let i = 0; i < 501; i++) await db.hset('a:' + s.uid, 'old-' + i, C.encrypt({ ...body, createdAt: i }, s.uid + ':old-' + i));
  await db.hset('a:' + s.uid, 'bad-record', 'broken');
  const result = await sync.list(s);
  assert.equal(result.items.length, 501); assert.equal(result.total, 502);
  assert.equal(result.items[0].revision, 1);
  assert.deepEqual(result.unreadable, ['bad-record']);
});

test('expired history requires a fresh snapshot and revoked sessions fail closed', async () => {
  const s = await session('expiry');
  const old = await sync.list(s);
  await db.set('sync:' + s.uid, C.encrypt({ seq: 3000, changes: [{ seq: 3000, id: 'gone' }], operations: {} }, 'sync:' + s.uid));
  await assert.rejects(sync.list(s, old.cursor), { status: 409 });
  assert.equal((await sync.list(s)).full, true);
  await db.del('s:' + s.hash);
  await assert.rejects(create(s, 'revoked'), { status: 401 });
});

test('account deletion closes the store before in-flight writes can recreate records', async () => {
  const s = await session('delete-race');
  await create(s, 'first');
  const keys = ['a:' + s.uid, 'sync:' + s.uid, 'sync-closed:' + s.uid, 's:' + s.hash];
  const expected = await db.get(keys[1]);
  await sync.close(s.uid);
  assert.equal(await db.eval(S.COMMIT, keys, [expected, 'new-meta', JSON.stringify({ restored: 'ciphertext' })]), 'closed');
  assert.equal(await db.get(keys[1]), null);
  assert.deepEqual(await db.hgetall(keys[0]), {});
  await assert.rejects(sync.list(s), { status: 401 });
});

test('HTTP handler enforces revision, CSRF, body limits, and retry headers', async () => {
  const A = require('../../api/_lib/auth');
  const handler = require('../../api/assessments');
  const headers = {};
  const s = await A.createSession({ setHeader: (k, v) => { headers[k] = v; } }, { id: 'http-user', email: 'http@example.org', role: 'user' });
  async function call(method, url, body, extra = {}) {
    const req = { method, url, body, headers: { host: 'localhost', origin: 'http://localhost', cookie: headers['Set-Cookie'].split(';')[0], 'x-csrf-token': s.csrf, ...extra } };
    const res = { statusCode: 200, setHeader() {}, end(text) { this.json = JSON.parse(text); } };
    await handler(req, res); return res;
  }
  const valid = { inputs: { age: 58, sex: 0, cp: 4, trestbps: 140, chol: 240, fbs: 0, restecg: 1, thalach: 120, exang: 1, oldpeak: 2.4, slope: 2, ca: 1, thal: 7 }, risk: 0.4 };
  const key = { 'idempotency-key': 'stable-operation-1234' };
  assert.equal((await call('POST', '/api/assessments', valid, { 'x-csrf-token': '' })).statusCode, 403);
  assert.equal((await call('POST', '/api/assessments', { ...valid, label: 'x'.repeat(21000) })).statusCode, 413);
  const saved = await call('POST', '/api/assessments', valid, key);
  assert.equal(saved.statusCode, 201);
  const replay = await call('POST', '/api/assessments', valid, key);
  assert.equal(replay.statusCode, 200); assert.equal(replay.json.item.id, saved.json.item.id);
  const url = '/api/assessments?id=' + saved.json.item.id;
  assert.equal((await call('PUT', url, valid)).statusCode, 428);
  assert.equal((await call('PUT', url, valid, { 'if-match': '1' })).statusCode, 200);
  assert.equal((await call('PUT', url, valid, { 'if-match': '1' })).statusCode, 409);
  assert.equal((await call('DELETE', url, undefined, { 'if-match': '1' })).statusCode, 409);
  assert.equal((await call('DELETE', url, undefined, { 'if-match': '2' })).statusCode, 200);
});
