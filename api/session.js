'use strict';
const A = require('./_lib/auth');

module.exports = A.handle(async (req, res) => {
  const s = await A.getSession(req);
  if (!s) return A.json(res, 200, { user: null });
  A.json(res, 200, { user: { email: s.email, name: s.name, role: s.role }, csrf: s.csrf, mustChange: s.mustChange });
});
