'use strict';
// Reviews written by signed-in users. Nothing is seeded: the list is empty until people post.
const A = require('./_lib/auth');
const C = require('./_lib/crypto');
const db = require('./_lib/db');

const clean = (t) => String(t || '').replace(/[\u0000-\u001f\u007f]+/g, ' ').replace(/\s+/g, ' ').trim();
function shortName(s) {
  const n = clean(s.name) || 'CardioSense user';
  const parts = n.split(' ');
  return parts.length > 1 ? `${parts[0]} ${parts[parts.length - 1][0]}.` : parts[0].slice(0, 30);
}

module.exports = A.handle(async (req, res) => {
  if (req.method === 'GET') {
    const all = await db.hgetall('reviews');
    const items = Object.entries(all).map(([id, v]) => { try { return { id, ...JSON.parse(v) }; } catch { return null; } }).filter(Boolean)
      .sort((a, b) => b.t - a.t);
    const avg = items.length ? items.reduce((n, r) => n + r.rating, 0) / items.length : 0;
    return A.json(res, 200, { count: items.length, average: Math.round(avg * 10) / 10, items: items.slice(0, 30) });
  }
  const s = await A.requireSession(req, res, { mutating: true });
  if (!s) return;
  const id = C.hmacId('review:' + s.uid);
  if (req.method === 'POST') {
    if (await A.hit('review', s.uid, 10, 86400)) return A.json(res, 429, { error: 'Too many edits today. Try again tomorrow.' });
    const b = await A.readJson(req);
    const rating = Number(b.rating), text = clean(b.text);
    if (!Number.isInteger(rating) || rating < 1 || rating > 5) return A.json(res, 400, { error: 'Choose a rating from 1 to 5.' });
    if (text.length < 10 || text.length > 500) return A.json(res, 400, { error: 'Write between 10 and 500 characters.' });
    const item = { name: shortName(s), rating, text, t: Date.now() };
    await db.hset('reviews', id, JSON.stringify(item));
    await A.audit(s.uid, s.email, 'review_saved', req);
    return A.json(res, 200, { item: { id, ...item } });
  }
  if (req.method === 'DELETE') {
    const target = new URL(req.url, 'http://x').searchParams.get('id') || id;
    if (target !== id && s.role !== 'admin') return A.json(res, 403, { error: 'You do not have access to this.' });
    await db.hdel('reviews', target);
    return A.json(res, 200, { ok: true });
  }
  A.json(res, 405, { error: 'Method not allowed.' });
});
