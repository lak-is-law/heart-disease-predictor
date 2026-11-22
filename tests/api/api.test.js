'use strict';
// API tests run against the real handlers with the in-process store: node --test tests/api/
const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('crypto');

process.env.SESSION_SECRET = 'test-secret-'.repeat(4);
process.env.DATA_ENCRYPTION_KEY = crypto.randomBytes(32).toString('base64');
delete process.env.UPSTASH_REDIS_REST_URL; delete process.env.KV_REST_API_URL;
const { hashPassword } = require('../../api/_lib/crypto');
process.env.CARDIOSENSE_USERS = JSON.stringify({
  'admin@example.org': { hash: hashPassword('admin password 123'), role: 'admin', name: 'Admin' },
});
const { createServer } = require('../../scripts/dev-server');
const db = require('../../api/_lib/db');

let base, server;
test.before(async () => {
  server = createServer();
  await new Promise((r) => server.listen(0, r));
  base = 'http://127.0.0.1:' + server.address().port;
});
test.after(() => server.close());

class Client {
  constructor() { this.cookie = ''; this.csrf = ''; }
  async call(method, path, body, headers = {}) {
    const res = await fetch(base + path, {
      method, redirect: 'manual',
      headers: { 'Content-Type': 'application/json', Origin: base, ...(this.cookie ? { Cookie: this.cookie } : {}), ...(this.csrf ? { 'X-CSRF-Token': this.csrf } : {}), ...headers },
      body: body ? JSON.stringify(body) : undefined,
    });
    const set = res.headers.get('set-cookie');
    if (set) this.cookie = set.split(';')[0].endsWith('=') ? '' : set.split(';')[0];
    const text = await res.text();
    let json = {}; try { json = JSON.parse(text); } catch { /* not json */ }
    return { status: res.status, json, headers: res.headers };
  }
  async login(email, password) {
    const r = await this.call('POST', '/api/login', { email, password });
    if (r.json.csrf) this.csrf = r.json.csrf;
    return r;
  }
}

const GOOD = { age: 58, sex: 0, cp: 4, trestbps: 140, chol: 240, fbs: 0, restecg: 1, thalach: 120, exang: 1, oldpeak: 2.4, slope: 2, ca: 1, thal: 7 };

test('anonymous requests are rejected', async () => {
  const c = new Client();
  assert.equal((await c.call('GET', '/api/assessments')).status, 401);
  assert.equal((await c.call('GET', '/api/releases')).status, 401);
  assert.equal((await c.call('GET', '/api/session')).json.user, null);
  const dl = await c.call('GET', '/api/download?id=1');
  assert.equal(dl.status, 302);
});

test('wrong password fails and says nothing about whether the account exists', async () => {
  const c = new Client();
  const a = await c.login('admin@example.org', 'nope nope nope');
  const b = await c.login('ghost@example.org', 'nope nope nope');
  assert.equal(a.status, 401); assert.equal(b.status, 401);
  assert.equal(a.json.error, b.json.error);
});

test('login sets a hardened cookie and logout really ends the session', async () => {
  const c = new Client();
  const r = await c.login('admin@example.org', 'admin password 123');
  assert.equal(r.status, 200);
  assert.equal(r.json.user.role, 'admin');
  const cookie = r.headers.get('set-cookie');
  assert.match(cookie, /HttpOnly/); assert.match(cookie, /SameSite=Strict/);
  const stolen = c.cookie;
  assert.equal((await c.call('GET', '/api/session')).json.user.email, 'admin@example.org');
  assert.equal((await c.call('POST', '/api/logout')).status, 200);
  // the old cookie must be dead on the server, not just cleared in the browser
  const replay = new Client(); replay.cookie = stolen;
  assert.equal((await replay.call('GET', '/api/session')).json.user, null);
});

test('mutations need the same origin and the CSRF token', async () => {
  const c = new Client();
  await c.login('admin@example.org', 'admin password 123');
  const noToken = await c.call('POST', '/api/assessments', { inputs: GOOD, risk: 0.5 }, { 'X-CSRF-Token': '' });
  assert.equal(noToken.status, 403);
  const foreign = await c.call('POST', '/api/assessments', { inputs: GOOD, risk: 0.5 }, { Origin: 'https://evil.example' });
  assert.equal(foreign.status, 403);
  const login = await c.call('POST', '/api/login', { email: 'admin@example.org', password: 'admin password 123' }, { Origin: 'https://evil.example' });
  assert.equal(login.status, 403);
});

test('assessments: validate, store encrypted, list, delete, and stay private per user', async () => {
  const admin = new Client();
  await admin.login('admin@example.org', 'admin password 123');
  const bad = await admin.call('POST', '/api/assessments', { inputs: { ...GOOD, age: 5 }, risk: 0.5 });
  assert.equal(bad.status, 400);
  assert.equal((await admin.call('POST', '/api/assessments', { inputs: GOOD, risk: 0.5, name: 'Jane Doe' })).status, 400);
  assert.equal((await admin.call('POST', '/api/assessments', { inputs: GOOD, risk: 0.5, label: 'Jane Doe <script>' })).status, 400);

  const ok = await admin.call('POST', '/api/assessments', { inputs: GOOD, risk: 0.713, label: 'Case 7' });
  assert.equal(ok.status, 201);
  const list = await admin.call('GET', '/api/assessments');
  assert.equal(list.json.items.length, 1);
  assert.equal(list.json.items[0].label, 'Case 7');
  assert.equal(list.json.items[0].inputs.chol, 240);

  // what is in the database is ciphertext only
  const uid = (await require('../../api/_lib/auth').findUser('admin@example.org')).id;
  const raw = Object.values(await db.hgetall('a:' + uid))[0];
  assert.match(raw, /^v1\./);
  assert.ok(!raw.includes('Case 7') && !raw.includes('240'));

  // a second user cannot see it
  const created = await admin.call('POST', '/api/admin', { action: 'create', email: 'dr.lee@example.org', name: 'Dr Lee', role: 'clinician' });
  assert.equal(created.status, 201);
  const lee = new Client();
  const li = await lee.login('dr.lee@example.org', created.json.temporaryPassword);
  assert.equal(li.json.mustChange, true);
  assert.equal((await lee.call('GET', '/api/assessments')).json.items.length, 0);
  assert.equal((await lee.call('GET', '/api/admin')).status, 403);

  const id = list.json.items[0].id;
  assert.equal((await lee.call('DELETE', '/api/assessments?id=' + id)).status, 404);
  assert.equal((await admin.call('DELETE', '/api/assessments?id=' + id)).status, 200);
  assert.equal((await admin.call('GET', '/api/assessments')).json.items.length, 0);
});

test('tampered or swapped ciphertext is not returned', async () => {
  const admin = new Client();
  await admin.login('admin@example.org', 'admin password 123');
  await admin.call('DELETE', '/api/assessments?all=1');
  await admin.call('POST', '/api/assessments', { inputs: GOOD, risk: 0.2 });
  const uid = (await require('../../api/_lib/auth').findUser('admin@example.org')).id;
  const rows = await db.hgetall('a:' + uid);
  const [id, token] = Object.entries(rows)[0];
  await db.hset('a:' + uid, 'x1-moved', token);          // same ciphertext under a different id
  const items = (await admin.call('GET', '/api/assessments')).json.items;
  assert.equal(items.length, 1);
  assert.equal(items[0].id, id);
});

test('account lockout after repeated failures', async () => {
  const admin = new Client();
  await admin.login('admin@example.org', 'admin password 123');
  const created = await admin.call('POST', '/api/admin', { action: 'create', email: 'locked@example.org', role: 'clinician' });
  const c = new Client();
  for (let i = 0; i < 8; i++) await c.login('locked@example.org', 'wrong password ' + i);
  const r = await c.login('locked@example.org', created.json.temporaryPassword);
  assert.equal(r.status, 429);
});

test('password change signs out other sessions and enforces the policy', async () => {
  const admin = new Client();
  await admin.login('admin@example.org', 'admin password 123');
  const created = await admin.call('POST', '/api/admin', { action: 'create', email: 'pw@example.org', role: 'clinician' });
  const a = new Client(), b = new Client();
  await a.login('pw@example.org', created.json.temporaryPassword);
  await b.login('pw@example.org', created.json.temporaryPassword);
  assert.equal((await a.call('POST', '/api/account', { action: 'password', current: created.json.temporaryPassword, next: 'short' })).status, 400);
  const ch = await a.call('POST', '/api/account', { action: 'password', current: created.json.temporaryPassword, next: 'a much better passphrase' });
  assert.equal(ch.status, 200);
  assert.equal((await b.call('GET', '/api/session')).json.user, null);
  assert.equal((await new Client().login('pw@example.org', 'a much better passphrase')).status, 200);
});

test('disabling an account ends its sessions and blocks sign-in', async () => {
  const admin = new Client();
  await admin.login('admin@example.org', 'admin password 123');
  const created = await admin.call('POST', '/api/admin', { action: 'create', email: 'gone@example.org', role: 'clinician' });
  const u = new Client();
  await u.login('gone@example.org', created.json.temporaryPassword);
  assert.equal((await admin.call('POST', '/api/admin', { action: 'disable', email: 'gone@example.org' })).status, 200);
  assert.equal((await u.call('GET', '/api/session')).json.user, null);
  assert.equal((await new Client().login('gone@example.org', created.json.temporaryPassword)).status, 401);
});

test('admin cannot lock themselves out', async () => {
  const admin = new Client();
  await admin.login('admin@example.org', 'admin password 123');
  assert.equal((await admin.call('POST', '/api/admin', { action: 'disable', email: 'admin@example.org' })).status, 400);
});

test('without a database in production the API fails closed', async () => {
  const keep = process.env.VERCEL;
  process.env.VERCEL = '1'; db._reset();
  const r = await new Client().call('POST', '/api/login', { email: 'a@b.co', password: 'x' });
  assert.equal(r.status, 503);
  if (keep === undefined) delete process.env.VERCEL; else process.env.VERCEL = keep;
  db._reset();
});

test('Upstash REST backend speaks the expected protocol', async () => {
  const http = require('http');
  const engine = new db._Memory();
  const seen = [];
  const fake = http.createServer((q, s) => {
    let b = ''; q.on('data', (d) => (b += d)); q.on('end', async () => {
      const cmd = JSON.parse(b); seen.push(q.headers.authorization);
      assert.ok(cmd.every((x) => typeof x === 'string'));
      s.setHeader('Content-Type', 'application/json');
      s.end(JSON.stringify({ result: await engine.cmd(...cmd) }));
    });
  });
  await new Promise((r) => fake.listen(0, r));
  process.env.UPSTASH_REDIS_REST_URL = 'http://127.0.0.1:' + fake.address().port;
  process.env.UPSTASH_REDIS_REST_TOKEN = 'tok';
  db._reset();
  try {
    const c = new Client();
    assert.equal((await c.login('admin@example.org', 'admin password 123')).status, 200);
    assert.equal((await c.call('POST', '/api/assessments', { inputs: GOOD, risk: 0.4, label: 'remote' })).status, 201);
    assert.equal((await c.call('GET', '/api/assessments')).json.items[0].label, 'remote');
    assert.ok(seen.every((a) => a === 'Bearer tok'));
  } finally {
    delete process.env.UPSTASH_REDIS_REST_URL; delete process.env.UPSTASH_REDIS_REST_TOKEN;
    db._reset(); fake.close();
  }
});
