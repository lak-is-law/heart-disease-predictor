'use strict';
const A = require('./_lib/auth');

module.exports = A.handle(async (req, res) => {
  const u = new URL(req.url, 'http://x');
  const isLogout = u.pathname.endsWith('/logout');

  if (isLogout || req.method === 'POST') {
    if (req.method !== 'POST') return A.json(res, 405, { error: 'Method not allowed.' });
    if (!A.sameOrigin(req)) return A.json(res, 403, { error: 'Request blocked.' });
    const s = await A.getSession(req);
    if (s) await A.audit(s.uid, s.email, 'logout', req);
    await A.endSession(req, res);
    return A.json(res, 200, { user: null });
  }

  const s = await A.getSession(req);
  if (!s) return A.json(res, 200, { user: null });
  A.json(res, 200, { user: { email: s.email, name: s.name, role: s.role }, csrf: s.csrf, mustChange: s.mustChange });
});
