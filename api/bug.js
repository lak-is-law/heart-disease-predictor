'use strict';
// Bug reports. Anyone can send one (rate limited, same-origin only); only admins can read them.
// Reports are stored in the database, never in the page or the repository.
const A = require('./_lib/auth');
const C = require('./_lib/crypto');
const db = require('./_lib/db');

const clean = (t, n) => String(t || '').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]+/g, ' ').trim().slice(0, n);

module.exports = A.handle(async (req, res) => {
  if (req.method === 'GET') {
    const s = await A.requireSession(req, res, { role: 'admin' });
    if (!s) return;
    const all = await db.hgetall('bugs');
    const items = Object.entries(all).map(([id, v]) => { try { return { id, ...JSON.parse(v) }; } catch { return null; } }).filter(Boolean).sort((a, b) => b.t - a.t);
    return A.json(res, 200, { count: items.length, items: items.slice(0, 200) });
  }
  if (req.method !== 'POST') return A.json(res, 405, { error: 'Method not allowed.' });
  if (!A.sameOrigin(req)) return A.json(res, 403, { error: 'Request blocked.' });
  if (await A.hit('bug-ip', A.clientIp(req), 5, 3600)) return A.json(res, 429, { error: 'Too many reports from this network. Try again later.' });
  const b = await A.readJson(req, 12_000);
  if (b.website) return A.json(res, 400, { error: 'Request blocked.' }); // honeypot
  const what = clean(b.what, 2000), area = clean(b.area, 40), email = clean(b.email, 120), page = clean(b.page, 200);
  if (what.length < 10) return A.json(res, 400, { error: 'Describe the problem in at least 10 characters.' });
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return A.json(res, 400, { error: 'Enter a valid email, or leave it empty.' });
  const sess = await A.getSession(req).catch(() => null);
  const id = C.hmacId('bug:' + Date.now() + ':' + Math.random()).slice(0, 12);
  await db.hset('bugs', id, JSON.stringify({ t: Date.now(), what, area, email, page, uid: sess ? sess.uid : null, ua: clean(req.headers['user-agent'], 160), status: 'new' }));
  if (await db.hlen('bugs') > 2000) { /* the oldest are pruned by an admin; the cap is the rate limit */ }
  A.json(res, 201, { ok: true, id });
});
