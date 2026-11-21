'use strict';
const A = require('./_lib/auth');

module.exports = (req, res) => {
  if (req.method !== 'POST') return A.json(res, 405, { error: 'Method not allowed.' });
  if (!A.sameOrigin(req)) return A.json(res, 403, { error: 'Request blocked.' });
  A.clearSession(res);
  A.json(res, 200, { user: null });
};
