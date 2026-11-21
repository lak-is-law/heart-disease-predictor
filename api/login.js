'use strict';
const A = require('./_lib/auth');

module.exports = async (req, res) => {
  if (req.method !== 'POST') return A.json(res, 405, { error: 'Method not allowed.' });
  if (!A.sameOrigin(req)) return A.json(res, 403, { error: 'Request blocked.' });

  const ip = String(req.headers['x-forwarded-for'] || req.socket.remoteAddress || '').split(',')[0].trim();
  if (A.limited(ip)) return A.json(res, 429, { error: 'Too many attempts. Try again in 10 minutes.' });

  const body = await A.readJson(req);
  const email = String(body.email || '').trim().toLowerCase();
  const password = String(body.password || '');
  if (!email || !password || password.length > 200) {
    return A.json(res, 400, { error: 'Enter your email and password.' });
  }

  const ok = A.checkPassword(password, A.users()[email]);
  if (!ok) {
    A.recordFailure(ip);
    await new Promise((r) => setTimeout(r, 400));
    return A.json(res, 401, { error: 'Email or password is incorrect.' });
  }
  A.setSession(res, email);
  A.json(res, 200, { user: { email } });
};
