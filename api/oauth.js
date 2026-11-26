'use strict';
// Sign in with Google, Microsoft, X or OpenAI (authorization-code flow with PKCE).
//   GET /api/oauth?providers=1                       which providers are configured
//   GET /api/oauth/<provider>                        start (rewritten to ?provider=&step=start)
//   GET /api/oauth/<provider>/callback               finish (rewritten to ?provider=&step=callback)
// Credentials come from the environment, see docs/DEPLOY.md.
const A = require('./_lib/auth');
const C = require('./_lib/crypto');
const db = require('./_lib/db');

const env = (k) => process.env[k] || '';
const PROVIDERS = {
  google: {
    label: 'Google', auth: 'https://accounts.google.com/o/oauth2/v2/auth', token: 'https://oauth2.googleapis.com/token',
    userinfo: 'https://openidconnect.googleapis.com/v1/userinfo', scope: 'openid email profile',
    id: () => env('GOOGLE_CLIENT_ID'), secret: () => env('GOOGLE_CLIENT_SECRET'),
    read: (u) => ({ sub: u.sub, email: u.email, verified: u.email_verified === true, name: u.name }),
  },
  microsoft: {
    label: 'Microsoft', auth: 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
    token: 'https://login.microsoftonline.com/common/oauth2/v2.0/token', userinfo: 'https://graph.microsoft.com/oidc/userinfo',
    scope: 'openid email profile', id: () => env('MICROSOFT_CLIENT_ID'), secret: () => env('MICROSOFT_CLIENT_SECRET'),
    read: (u) => ({ sub: u.sub, email: u.email, verified: false, name: u.name }), // Microsoft does not vouch for the address
  },
  x: {
    label: 'X', auth: 'https://twitter.com/i/oauth2/authorize', token: 'https://api.twitter.com/2/oauth2/token',
    userinfo: 'https://api.twitter.com/2/users/me?user.fields=name,username', scope: 'users.read tweet.read', basic: true,
    id: () => env('X_CLIENT_ID'), secret: () => env('X_CLIENT_SECRET'),
    read: (u) => ({ sub: u.data && u.data.id, email: '', verified: false, name: u.data && (u.data.name || u.data.username) }),
  },
  // OpenAI does not publish a standard sign-in endpoint for third-party sites. If you have been given OIDC
  // endpoints for "Sign in with ChatGPT", set the OPENAI_OAUTH_* variables and this button switches on.
  openai: {
    label: 'ChatGPT', get auth() { return env('OPENAI_OAUTH_AUTH_URL'); }, get token() { return env('OPENAI_OAUTH_TOKEN_URL'); },
    get userinfo() { return env('OPENAI_OAUTH_USERINFO_URL'); }, get scope() { return env('OPENAI_OAUTH_SCOPE') || 'openid email profile'; },
    id: () => env('OPENAI_OAUTH_CLIENT_ID'), secret: () => env('OPENAI_OAUTH_CLIENT_SECRET'),
    read: (u) => ({ sub: u.sub, email: u.email, verified: u.email_verified === true, name: u.name }),
  },
};
const configured = (p) => Boolean(p.id() && p.secret() && p.auth && p.token && p.userinfo);
const STATE_COOKIE = (A.PROD ? '__Host-' : '') + 'cs_oauth';

function origin(req) {
  if (process.env.SITE_URL) return process.env.SITE_URL.replace(/\/+$/, '');
  const host = req.headers.host || '';
  return (/^(localhost|127\.)/.test(host) ? 'http://' : 'https://') + host;
}
const redirect = (res, to, headers = {}) => { res.statusCode = 302; res.setHeader('Location', to); res.setHeader('Cache-Control', 'no-store'); for (const k in headers) res.setHeader(k, headers[k]); res.end(); };
const fail = (res, code) => redirect(res, '/signin?error=' + code, { 'Set-Cookie': `${STATE_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${A.PROD ? '; Secure' : ''}` });
const safeNext = (n) => (typeof n === 'string' && /^\/[a-z0-9\-_/]*(#[a-z0-9\-_]*)?$/i.test(n) && !n.startsWith('//') ? n : '/app');

async function start(req, res, name, p, url) {
  const state = C.randomId(24), verifier = C.randomId(32);
  const challenge = require('crypto').createHash('sha256').update(verifier).digest('base64url');
  await db.set('oa:' + C.sha256(state), JSON.stringify({ provider: name, verifier, accountType: url.searchParams.get('accountType') === 'facility' ? 'facility' : 'patient', next: safeNext(url.searchParams.get('next')) }), 600);
  const q = new URLSearchParams({
    response_type: 'code', client_id: p.id(), redirect_uri: `${origin(req)}/api/oauth/${name}/callback`,
    scope: p.scope, state, code_challenge: challenge, code_challenge_method: 'S256',
  });
  redirect(res, p.auth + (p.auth.includes('?') ? '&' : '?') + q, {
    'Set-Cookie': `${STATE_COOKIE}=${state}; Path=/; HttpOnly; SameSite=Lax; Max-Age=600${A.PROD ? '; Secure' : ''}`,
  });
}

async function resolveUser(name, info, accountType) {
  const idKey = `oi:${name}:${C.sha256(String(info.sub))}`;
  const known = await db.get(idKey);
  if (known) return A.findUser(known);
  let email = A.normEmail(info.email);
  if (!A.validEmail(email)) email = `${name}.${C.sha256(String(info.sub)).slice(0, 16)}@oauth.invalid`;
  const existing = await A.findUser(email);
  if (existing) {
    if (!info.verified) return 'email_exists';        // never link to someone else's account on an unverified address
    await db.set(idKey, existing.email);
    await db.sadd('uoi:' + existing.id, idKey);
    return existing;
  }
  const u = { id: C.randomId(12), email, name: String(info.name || '').trim().slice(0, 80), role: 'user', accountType, pw: '', createdAt: Date.now(), disabled: false, mustChange: false, via: name };
  if (!(await A.insertUser(u))) return resolveUser(name, info, accountType);
  await db.set(idKey, email);
  await db.sadd('uoi:' + u.id, idKey);
  return u;
}

async function callback(req, res, name, p, url) {
  const state = url.searchParams.get('state') || '', code = url.searchParams.get('code') || '';
  if (url.searchParams.get('error') || !state || !code) return fail(res, 'cancelled');
  if (!C.safeEqual(A.cookies(req)[STATE_COOKIE] || '', state)) return fail(res, 'state');
  const raw = await db.get('oa:' + C.sha256(state));
  await db.del('oa:' + C.sha256(state));                                  // one use only
  const rec = raw ? JSON.parse(raw) : null;
  if (!rec || rec.provider !== name) return fail(res, 'state');
  const form = new URLSearchParams({ grant_type: 'authorization_code', code, redirect_uri: `${origin(req)}/api/oauth/${name}/callback`, code_verifier: rec.verifier, client_id: p.id() });
  const headers = { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' };
  if (p.basic) headers.Authorization = 'Basic ' + Buffer.from(`${p.id()}:${p.secret()}`).toString('base64'); else form.set('client_secret', p.secret());
  let info;
  try {
    const t = await (await fetch(p.token, { method: 'POST', headers, body: form })).json();
    if (!t.access_token) return fail(res, 'provider');
    const u = await (await fetch(p.userinfo, { headers: { Authorization: 'Bearer ' + t.access_token, Accept: 'application/json' } })).json();
    info = p.read(u);
  } catch { return fail(res, 'provider'); }
  if (!info || !info.sub) return fail(res, 'provider');
  const user = await resolveUser(name, info, rec.accountType);
  if (user === 'email_exists') return fail(res, 'email_exists');
  if (!user || user.disabled) return fail(res, 'disabled');
  await A.createSession(res, user);
  await A.audit(user.id, user.email, 'login_' + name, req);
  // A same-site page performs the final hop so the SameSite=Strict session cookie is sent with it.
  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Set-Cookie', [res.getHeader('Set-Cookie'), `${STATE_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${A.PROD ? '; Secure' : ''}`].flat());
  res.end(`<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=${rec.next}"><title>Signing in</title><p>Signing in. <a href="${rec.next}">Continue</a></p>`);
}

module.exports = A.handle(async (req, res) => {
  if (req.method !== 'GET') return A.json(res, 405, { error: 'Method not allowed.' });
  const url = new URL(req.url, 'http://x');
  if (url.searchParams.get('providers')) {
    return A.json(res, 200, { providers: Object.entries(PROVIDERS).map(([id, p]) => ({ id, label: p.label, enabled: configured(p) })) });
  }
  const name = url.searchParams.get('provider') || '';
  const p = Object.prototype.hasOwnProperty.call(PROVIDERS, name) ? PROVIDERS[name] : null;
  if (!p || !configured(p)) return fail(res, 'unavailable');
  if (url.searchParams.get('step') === 'callback') return callback(req, res, name, p, url);
  return start(req, res, name, p, url);
});
