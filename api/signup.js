'use strict';
const A = require('./_lib/auth');

module.exports = A.handle(async (req, res) => {
  if (req.method !== 'POST') return A.json(res, 405, { error: 'Method not allowed.' });
  if (!A.sameOrigin(req)) return A.json(res, 403, { error: 'Request blocked.' });
  if (process.env.CARDIOSENSE_SIGNUP === 'closed') return A.json(res, 403, { error: 'Sign-up is closed. Ask an administrator for an account.' });
  if (await A.hit('signup-ip', A.clientIp(req), 10, 3600)) return A.json(res, 429, { error: 'Too many sign-ups from this network. Try again later.' });

  const body = await A.readJson(req);
  if (body.website) return A.json(res, 400, { error: 'Request blocked.' }); // honeypot
  const user = await A.createUser({ email: body.email, name: body.name, role: 'clinician', password: body.password, mustChange: false });
  const s = await A.createSession(res, user);
  await A.audit(user.id, user.email, 'signup', req);
  A.json(res, 201, { user: A.publicUser(user), csrf: s.csrf });
});
