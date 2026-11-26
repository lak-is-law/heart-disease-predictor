'use strict';
const db = require('./db');
const C = require('./crypto');


// One invited clinic per pilot installation. All membership and visit transitions
// share a compare-and-set boundary so removal or withdrawal wins over stale updates.
const key = 'rehearsal:clinic:v1';
const empty = () => ({ clinic: null, members: {}, visits: {}, library: [] });
function fail(status, message) { throw Object.assign(new Error(message), { status }); }
function field(value, max, required = false) {
  if (value == null && !required) return '';
  if (typeof value !== 'string' || value.length > max || (required && !value.trim())) fail(400, 'Check the required fields and text length.');
  return value.trim();
}
function summary(b) {
  return { question: field(b.question, 800, true), medicines: field(b.medicines, 500), readings: field(b.readings, 500) };
}
async function change(fn) {
  for (let i = 0; i < 8; i++) {
    const raw = await db.get(key);
    const state = raw ? C.decrypt(raw, key) : empty();
    const result = await fn(state);
    if (await db.compareAndSet(key, raw, C.encrypt(state, key))) return result;
  }
  fail(409, 'The workspace changed. Refresh and try again.');
}
async function load() {
  const raw = await db.get(key);
  return raw ? C.decrypt(raw, key) : empty();
}
const code = uid => C.hmacId('rehearsal:' + uid);
const draftKey = uid => 'rehearsal:draft:' + uid;
// The account type is assigned once. Membership remains independently revocable.
const typeKey = accountCode => 'account-type:' + accountCode;
async function accountType(uid, role, assigned) {
  const id = code(uid);
  const key = typeKey(id);
  const existing = await db.get(key);
  if (existing) return existing;
  let type = assigned;
  if (!type) {
    const prior = await db.get('workspace:' + uid);
    const clinic = await load();
    type = role === 'admin' || clinic.members[id] || prior === 'facility' ? 'facility' : 'patient';
  }
  if (await db.setIfAbsent(key, type)) return type;
  return db.get(key);
}
async function erase(uid) {
  const id = code(uid);
  await db.del('rehearsal:account:' + id);
  await db.del(typeKey(id));
  await db.del(draftKey(uid));
  await db.del('workspace:' + uid);
  if (await db.get(key)) await change(s => {
    delete s.members[id];
    for (const [k,v] of Object.entries(s.visits)) if (v.patient === id) delete s.visits[k];
  });
}
module.exports = { accountType, typeKey, load, change, erase, summary, field, fail, code, draftKey };
