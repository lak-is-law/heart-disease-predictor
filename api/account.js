'use strict';
const A = require('./_lib/auth');
const C = require('./_lib/crypto');
const db = require('./_lib/db');

module.exports = A.handle(async (req, res) => {
  const s = await A.requireSession(req, res, { mutating: req.method !== 'GET' });
  if (!s) return;

  if (req.method === 'GET') {
    const rows = (await db.range('audit:' + s.uid, 30)).map((r) => { try { return JSON.parse(r); } catch { return null; } }).filter(Boolean);
    return A.json(res, 200, { user: { email: s.email, name: s.name, role: s.role }, activity: rows, mustChange: s.mustChange });
  }
  if (req.method !== 'POST') return A.json(res, 405, { error: 'Method not allowed.' });
  const body = await A.readJson(req);

  if (body.action === 'password') {
    if (await A.hit('pwchange', s.uid, 8, 900)) return A.json(res, 429, { error: 'Too many attempts. Try again later.' });
    const user = await A.findUser(s.email);
    if (!user || user.source === 'env') return A.json(res, 400, { error: 'This account is managed outside the app. Change its password where it was created.' });
    if (!C.checkPassword(String(body.current || ''), user.pw)) return A.json(res, 401, { error: 'Current password is incorrect.' });
    const problem = C.passwordProblem(String(body.next || ''), user.email);
    if (problem) return A.json(res, 400, { error: problem });
    user.pw = C.hashPassword(body.next);
    user.mustChange = false;
    await A.saveUser(user);
    await A.endAllSessions(user.id);              // every other device signs out
    const fresh = await A.createSession(res, user);
    await A.audit(user.id, user.email, 'password_changed', req);
    return A.json(res, 200, { ok: true, csrf: fresh.csrf });
  }

  if (body.action === 'signout-all') {
    await A.endAllSessions(s.uid);
    await A.audit(s.uid, s.email, 'signout_all', req);
    await A.endSession(req, res);
    return A.json(res, 200, { ok: true });
  }

  A.json(res, 400, { error: 'Unknown action.' });
});
