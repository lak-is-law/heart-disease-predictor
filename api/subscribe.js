'use strict';
// Newsletter list. Subscribing and unsubscribing are public (rate limited, same-origin); only admins can read the list.
// The response never says whether an address was already on the list.
const A = require('./_lib/auth');
const C = require('./_lib/crypto');
const db = require('./_lib/db');

module.exports = A.handle(async (req, res) => {
  if (req.method === 'GET') {
    const s = await A.requireSession(req, res, { role: 'admin' });
    if (!s) return;
    const all = await db.hgetall('subs');
    const items = Object.values(all).map((v) => { try { const o = JSON.parse(v); return { email: o.email, t: o.t }; } catch { return null; } }).filter(Boolean).sort((a, b) => b.t - a.t);
    return A.json(res, 200, { count: items.length, items });
  }
  if (req.method !== 'POST') return A.json(res, 405, { error: 'Method not allowed.' });
  if (!A.sameOrigin(req)) return A.json(res, 403, { error: 'Request blocked.' });
  if (await A.hit('sub-ip', A.clientIp(req), 8, 3600)) return A.json(res, 429, { error: 'Too many attempts. Try again later.' });
  const b = await A.readJson(req, 2_000);
  if (b.website) return A.json(res, 400, { error: 'Request blocked.' }); // honeypot
  if (b.unsubscribe) {
    const id = await db.hget('sub-tokens', String(b.unsubscribe).slice(0, 80));
    if (id) { await db.hdel('subs', id); await db.hdel('sub-tokens', String(b.unsubscribe).slice(0, 80)); }
    return A.json(res, 200, { ok: true });
  }
  const email = String(b.email || '').trim().toLowerCase().slice(0, 120);
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) return A.json(res, 400, { error: 'Enter a valid email address.' });
  const id = C.hmacId('sub:' + email).slice(0, 24);
  if (!(await db.hget('subs', id))) {
    const token = C.randomId();
    await db.hset('subs', id, JSON.stringify({ email, t: Date.now(), token }));
    await db.hset('sub-tokens', token, id);
  }
  A.json(res, 201, { ok: true });
});
