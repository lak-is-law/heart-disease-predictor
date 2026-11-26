'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { create } = require('../../portal/sync-client');
const snapshot = (items = []) => ({ full: true, items, deleted: [], unreadable: [], cursor: 'cursor' });

test('double-click and retry after a lost response reuse one operation key', async () => {
  const calls = []; let online = false;
  const client = create({ identity: () => 'a', request: async (method, path, body, headers) => {
    calls.push(headers['Idempotency-Key']);
    if (!online) throw new Error('Offline');
    return { item: { ...body, id: 'record', createdAt: 1 } };
  } });
  const first = client.save({ risk: 0.5 });
  const double = client.save({ risk: 0.5 });
  assert.equal(first, double);
  await assert.rejects(first, /Offline/);
  assert.equal(client.hasPending(), true);
  online = true;
  await client.retry(false);
  assert.equal(new Set(calls).size, 1);
  assert.equal(client.hasPending(), false);
  assert.equal(client.snapshot().length, 1);
});

test('account switches discard the old pending upload and late response', async () => {
  let owner = 'a', resolve;
  const calls = [];
  const client = create({ identity: () => owner, request: async (method) => {
    calls.push(method);
    return new Promise((r) => { resolve = r; });
  } });
  const request = client.save({ risk: 0.5 });
  await new Promise(setImmediate);
  owner = 'b';
  assert.deepEqual(client.snapshot(), []);
  resolve({ item: { id: 'private-a' } });
  await assert.rejects(request, /session changed/);
  assert.deepEqual(client.snapshot(), []);
  assert.equal(client.hasPending(), false);
  await client.retry(false);
  assert.equal(calls.length, 1);
});

test('unchanged polls preserve rendering and expired cursors rebuild the snapshot', async () => {
  let calls = 0, renders = 0;
  const item = { id: 'one', createdAt: 1 };
  const client = create({ identity: () => 'a', onChange: () => renders++, request: async () => {
    calls++;
    if (calls === 1) return snapshot([item]);
    if (calls === 2) return { ...snapshot(), full: false };
    if (calls === 3) throw Object.assign(new Error('expired'), { status: 409 });
    return snapshot([]);
  } });
  await client.refresh();
  const afterFirst = renders;
  await client.refresh();
  assert.equal(renders, afterFirst);
  await client.refresh();
  assert.equal(calls, 4); assert.deepEqual(client.snapshot(), []);
});

test('a changed pending draft cannot overwrite the original and 401 is not automatically retried', async () => {
  let calls = 0;
  const client = create({ identity: () => 'a', request: async () => { calls++; throw Object.assign(new Error('Sign in'), { status: 401 }); } });
  await assert.rejects(client.save({ risk: 0.1 }));
  await assert.rejects(client.save({ risk: 0.8 }), /different save/);
  await client.retry(true);
  assert.equal(calls, 1);
});
