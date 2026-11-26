'use strict';
const A = require('./_lib/auth');
const C = require('./_lib/crypto');

module.exports = A.handle(async (req, res) => {
  if (req.method !== 'POST') return A.json(res, 405, { error: 'Method not allowed.' });
  if (!A.sameOrigin(req)) return A.json(res, 403, { error: 'Request blocked.' });

  const ip = A.clientIp(req);
  if (await A.hit('login-ip', ip, 40, 600)) return A.json(res, 429, { error: 'Too many attempts. Try again in 10 minutes.' });

  const body = await A.readJson(req);
  if (body.website) return A.json(res, 400, { error: 'Request blocked.' }); // honeypot field
  const email = A.normEmail(body.email);
  const password = typeof body.password === 'string' ? body.password : '';
  if (!email || !password || password.length > 200) return A.json(res, 400, { error: 'Enter your email and password.' });

  // Per-account lockout: 8 wrong passwords lock the account for 15 minutes.
  const lockKey = 'login-acct';
  const attempts = Number(await require('./_lib/db').get(`rl:${lockKey}:${C.hmacId(email)}`)) || 0;
  if (attempts >= 8) return A.json(res, 429, { error: 'Too many attempts for this account. Try again in 15 minutes.' });

  const user = await A.findUser(email);
  const ok = A.checkPassword(password, user && user.pw) && user && !user.disabled; // always hashes, so timing does not reveal accounts
  if (!ok) {
    await A.hit(lockKey, email, 8, 900);
    if (user) await A.audit(user.id, user.email, 'login_failed', req);
    return A.json(res, 401, { error: 'Email or password is incorrect.' });
  }
  await require('./_lib/db').del(`rl:${lockKey}:${C.hmacId(email)}`);
  const s = await A.createSession(res, user);
  await A.audit(user.id, user.email, 'login', req);
  A.json(res, 200, {
    user: { email: s.email, name: s.name, role: s.role, onboarded: Boolean(s.onboarded), onboardingSkipped: Boolean(s.onboardingSkipped), tourSeen: Boolean(s.tourSeen) },
    csrf: s.csrf, mustChange: s.mustChange,
  });
});
