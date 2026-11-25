'use strict';
const A = require('./_lib/auth');

module.exports = A.handle(async (req, res) => {
  if (req.method !== 'POST') return A.json(res, 405, { error: 'Method not allowed.' });
  if (!A.sameOrigin(req)) return A.json(res, 403, { error: 'Request blocked.' });
  const s = await A.getSession(req);
  if (s) await A.audit(s.uid, s.email, 'logout', req);
  await A.endSession(req, res);
  A.json(res, 200, { user: null });
});
