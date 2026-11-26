'use strict';
// Account administration. There is no public sign-up: an admin creates accounts, which start with
// a temporary password the person must change at first sign-in.
const A = require('./_lib/auth');
const C = require('./_lib/crypto');
const db = require('./_lib/db');

module.exports = A.handle(async (req, res) => {
  const s = await A.requireSession(req, res, { mutating: req.method !== 'GET', role: 'admin' });
  if (!s) return;

  if (req.method === 'GET') {
    const emails = await db.smembers('users');
    const users = [];
    const referralCounts = {};
    for (const e of emails) {
      const u = await A.findUser(e);
      if (u) {
        const prof = await A.getProfile(u.id);
        const ref = (prof && prof.referralSource) || '';
        if (ref) referralCounts[ref] = (referralCounts[ref] || 0) + 1;
        users.push({
          email: u.email,
          name: (prof && prof.name) || u.name || '',
          role: u.role,
          disabled: Boolean(u.disabled),
          createdAt: u.createdAt,
          onboarded: Boolean(prof && prof.onboardedAt),
          roleType: (prof && prof.roleType) || '',
          referralSource: ref,
          organization: (prof && prof.organization) || '',
          country: (prof && prof.country) || '',
        });
      }
    }
    const events = (await db.range('audit:all', 50)).map((r) => { try { return JSON.parse(r); } catch { return null; } }).filter(Boolean);
    return A.json(res, 200, { users, events, referralCounts });
  }
  if (req.method !== 'POST') return A.json(res, 405, { error: 'Method not allowed.' });
  if (await A.hit('admin', s.uid, 60, 60)) return A.json(res, 429, { error: 'Slow down for a moment.' });
  const body = await A.readJson(req);

  if (body.action === 'create') {
    const temp = C.randomId(12); // shown once; 16 URL-safe characters
    const u = await A.createUser({ email: body.email, name: body.name, role: body.role, password: temp });
    await A.audit(s.uid, s.email, 'user_created', req, u.email);
    return A.json(res, 201, { user: A.publicUser(u), temporaryPassword: temp });
  }

  const email = A.normEmail(body.email);
  const u = await A.findUser(email);
  if (!u) return A.json(res, 404, { error: 'No such account.' });
  if (u.source === 'env') return A.json(res, 400, { error: 'This account is defined in the environment and cannot be changed here.' });
  if (u.email === s.email && (body.action === 'disable' || body.action === 'role')) return A.json(res, 400, { error: 'You cannot change your own access.' });

  if (body.action === 'disable' || body.action === 'enable') {
    u.disabled = body.action === 'disable';
    await A.saveUser(u);
    if (u.disabled) await A.endAllSessions(u.id);
    await A.audit(s.uid, s.email, 'user_' + body.action + 'd', req, u.email);
    return A.json(res, 200, { ok: true });
  }
  if (body.action === 'role') {
    if (!A.ROLES.includes(body.role)) return A.json(res, 400, { error: 'Unknown role.' });
    u.role = body.role;
    await A.saveUser(u);
    await A.endAllSessions(u.id);
    await A.audit(s.uid, s.email, 'user_role_changed', req, u.email);
    return A.json(res, 200, { ok: true });
  }
  if (body.action === 'reset') {
    const temp = C.randomId(12);
    u.pw = C.hashPassword(temp);
    u.mustChange = true;
    await A.saveUser(u);
    await A.endAllSessions(u.id);
    await A.audit(s.uid, s.email, 'user_password_reset', req, u.email);
    return A.json(res, 200, { temporaryPassword: temp });
  }
  A.json(res, 400, { error: 'Unknown action.' });
});
