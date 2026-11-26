'use strict';
const db = require('./db');
const C = require('./crypto');
const S = require('./sync-storage');
const WINDOW = 24 * 60 * 60 * 1000;
const HISTORY = 2000;
const error = (status, message) => Object.assign(new Error(message), { status });
const keys = (s) => ['a:' + s.uid, 'sync:' + s.uid, 'sync-closed:' + s.uid, 's:' + s.hash];
const aad = (s) => 'sync:' + s.uid;
async function read(s) {
  const [status, raw, flat] = await db.eval(S.READ, keys(s));
  if (status !== 'ok') throw error(401, 'Sign in to continue.');
  const rows = {};
  for (let i = 0; i < flat.length; i += 2) rows[flat[i]] = flat[i + 1];
  const meta = raw ? C.decrypt(raw, aad(s)) : { seq: 0, changes: [], operations: {} };
  return { raw, rows, meta };
}
function decode(s, id, token) {
  const item = C.decrypt(token, `${s.uid}:${id}`);
  return { ...item, id, revision: item.revision || 1 };
}
function cursor(s, seq) { return C.encrypt({ seq }, 'cursor:' + s.uid); }
async function list(s, token) {
  const { rows, meta } = await read(s);
  let changes = null;
  if (token) {
    let parsed;
    try { parsed = C.decrypt(token, 'cursor:' + s.uid); } catch { throw error(400, 'Invalid sync cursor.'); }
    if (!Number.isSafeInteger(parsed.seq) || parsed.seq < 0 || parsed.seq > meta.seq) throw error(409, 'Sync history changed. Refresh your cloud snapshot.');
    const oldest = meta.changes.length ? meta.changes[0].seq : meta.seq + 1;
    if (parsed.seq < oldest - 1) throw error(409, 'Sync history expired. Refresh your cloud snapshot.');
    changes = new Set(meta.changes.filter((c) => c.seq > parsed.seq).map((c) => c.id));
  }
  const items = [], deleted = [], unreadable = [];
  for (const id of changes || Object.keys(rows)) {
    if (!Object.hasOwn(rows, id)) { deleted.push(id); continue; }
    try { items.push(decode(s, id, rows[id])); } catch { unreadable.push(id); }
  }
  items.sort((a, b) => b.createdAt - a.createdAt || a.id.localeCompare(b.id));
  return { items, deleted, unreadable, total: Object.keys(rows).length, cursor: cursor(s, meta.seq), full: !token };
}
async function mutate(s, { action, id, body, expectedRevision, operation }) {
  const digest = C.sha256(JSON.stringify({ action, id, body, expectedRevision }));
  const operationKey = operation ? C.sha256(operation) : null;
  const newId = id || Date.now().toString(36) + '-' + C.randomId(12);
  for (let attempt = 0; attempt < 8; attempt++) {
    const { raw, rows, meta } = await read(s);
    const now = Date.now();
    for (const [key, value] of Object.entries(meta.operations)) if (now - value.at >= WINDOW) delete meta.operations[key];
    const previous = operationKey && meta.operations[operationKey];
    if (previous) {
      if (previous.digest !== digest) throw error(409, 'This save identifier was already used for different content.');
      const item = previous.id && rows[previous.id] ? decode(s, previous.id, rows[previous.id]) : null;
      return { ok: true, item, deleted: !item, replayed: true };
    }
    if (operationKey && Object.keys(meta.operations).length >= HISTORY) throw error(429, 'Daily sync operation limit reached. Your draft has not been saved. Try again later.');
    const writes = {};
    let item = null;
    if (action === 'create') {
      if (Object.keys(rows).length >= 2000) throw error(409, 'Storage limit reached. Export or delete assessments first.');
      item = { ...body, createdAt: now, updatedAt: now, revision: 1 };
      writes[newId] = C.encrypt(item, `${s.uid}:${newId}`);
      item.id = newId;
    } else if (action === 'erase') {
      for (const rowId of Object.keys(rows)) writes[rowId] = null;
    } else {
      if (!Object.hasOwn(rows, id)) throw error(404, 'Assessment not found. It may have been deleted on another device.');
      if (action === 'update' || expectedRevision !== undefined) {
        let old;
        try { old = decode(s, id, rows[id]); } catch { throw error(409, 'This assessment could not be decrypted. Export other records and contact support.'); }
        if (old.revision !== expectedRevision) throw error(409, 'This assessment changed on another device. Refresh and review before trying again.');
        if (action === 'update') {
          item = { ...body, createdAt: old.createdAt, updatedAt: now, revision: old.revision + 1 };
          writes[id] = C.encrypt(item, `${s.uid}:${id}`);
          item.id = id;
        }
      }
      if (action === 'delete') writes[id] = null;
    }
    for (const rowId of Object.keys(writes)) meta.changes.push({ seq: ++meta.seq, id: rowId });
    meta.changes = meta.changes.slice(-HISTORY);
    if (operationKey) meta.operations[operationKey] = { at: now, digest, id: action === 'create' || action === 'update' ? newId : null };
    const result = await db.eval(S.COMMIT, keys(s), [raw, C.encrypt(meta, aad(s)), JSON.stringify(writes)]);
    if (result === 'closed') throw error(401, 'Sign in to continue.');
    if (result === 'ok') return { ok: true, item, replayed: false };
  }
  throw error(409, 'Another device is syncing. Your draft is unchanged; retry shortly.');
}
async function close(uid) { await db.eval(S.CLOSE, keys({ uid, hash: '' })); }
module.exports = { list, mutate, close };
