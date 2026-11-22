'use strict';
// A signed-in user's saved assessments. Each record is encrypted (AES-256-GCM) before it reaches the
// database, bound to the owner and record id, so a database dump on its own reveals nothing.
const A = require('./_lib/auth');
const C = require('./_lib/crypto');
const db = require('./_lib/db');
const V = require('./_lib/validate');

const MAX_PER_USER = 2000;
const key = (uid) => 'a:' + uid;

module.exports = A.handle(async (req, res) => {
  const mutating = req.method !== 'GET';
  const s = await A.requireSession(req, res, { mutating });
  if (!s) return;
  const url = new URL(req.url, 'http://x');

  if (req.method === 'GET') {
    const rows = await db.hgetall(key(s.uid));
    const items = [];
    for (const [id, token] of Object.entries(rows)) {
      try { items.push({ id, ...C.decrypt(token, `${s.uid}:${id}`) }); } catch { /* skip unreadable record */ }
    }
    items.sort((a, b) => b.createdAt - a.createdAt);
    return A.json(res, 200, { items: items.slice(0, 500), total: items.length });
  }

  if (await A.hit('write', s.uid, 120, 60)) return A.json(res, 429, { error: 'Slow down for a moment.' });

  if (req.method === 'POST') {
    const a = V.assessment(await A.readJson(req));
    if ((await db.hlen(key(s.uid))) >= MAX_PER_USER) return A.json(res, 409, { error: 'Storage limit reached. Delete some assessments first.' });
    const id = Date.now().toString(36) + '-' + C.randomId(5);
    const record = { ...a, createdAt: Date.now() };
    await db.hset(key(s.uid), id, C.encrypt(record, `${s.uid}:${id}`));
    await A.audit(s.uid, s.email, 'assessment_saved', req);
    return A.json(res, 201, { item: { id, ...record } });
  }

  if (req.method === 'DELETE') {
    if (url.searchParams.get('all') === '1') {
      await db.del(key(s.uid));
      await A.audit(s.uid, s.email, 'assessments_erased', req);
      return A.json(res, 200, { ok: true });
    }
    const id = url.searchParams.get('id') || '';
    if (!/^[a-z0-9]+-[A-Za-z0-9_-]+$/.test(id)) return A.json(res, 400, { error: 'Invalid id.' });
    const n = await db.hdel(key(s.uid), id);
    if (n) await A.audit(s.uid, s.email, 'assessment_deleted', req);
    return A.json(res, n ? 200 : 404, n ? { ok: true } : { error: 'Not found.' });
  }

  A.json(res, 405, { error: 'Method not allowed.' });
});
