'use strict';
// Accounts, server-side sessions, CSRF protection, rate limits and audit trail.
//
// Sessions are random 256-bit ids kept in the database (only a SHA-256 of the id is stored), so a
// sign-out really ends the session and an admin can revoke every session for a user.
// The cookie is HttpOnly, SameSite=Strict and, in production, Secure with the __Host- prefix.
const db = require('./db');
const C = require('./crypto');

const PROD = process.env.NODE_ENV === 'production' || Boolean(process.env.VERCEL);
const COOKIE = PROD ? '__Host-cs_session' : 'cs_session';
const IDLE = 60 * 60 * 12;          // a session ends after 12 hours without use
const ABSOLUTE = 60 * 60 * 24 * 7;  // and never lasts longer than 7 days
const ROLES = ['clinician', 'admin'];

// ------------------------------------------------------------------ http helpers
function json(res, status, body) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(body));
}

async function readJson(req, limit = 20_000) {
  if (req.body && typeof req.body === 'object') return req.body;
  if (typeof req.body === 'string') { try { return JSON.parse(req.body); } catch { return {}; } }
  const chunks = [];
  let size = 0;
  for await (const c of req) {
    size += c.length;
    if (size > limit) return {};
    chunks.push(c);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString() || '{}'); } catch { return {}; }
}

function cookies(req) {
  const out = {};
  for (const part of (req.headers.cookie || '').split(';')) {
    const i = part.indexOf('=');
    if (i > 0) { try { out[part.slice(0, i).trim()] = decodeURIComponent(part.slice(i + 1).trim()); } catch { /* ignore */ } }
  }
  return out;
}

function clientIp(req) {
  return String(req.headers['x-vercel-forwarded-for'] || req.headers['x-real-ip'] || req.headers['x-forwarded-for'] || (req.socket && req.socket.remoteAddress) || '')
    .split(',')[0].trim();
}

// State-changing requests must come from this site: Origin (or Sec-Fetch-Site) has to match.
function sameOrigin(req) {
  const origin = req.headers.origin;
  if (origin) {
    try { return new URL(origin).host === req.headers.host; } catch { return false; }
  }
  const site = req.headers['sec-fetch-site'];
  return site === 'same-origin' || site === 'none';
}

function cookieString(value, maxAge) {
  return `${COOKIE}=${value}; Path=/; HttpOnly; SameSite=Strict; Max-Age=${maxAge}${PROD ? '; Secure' : ''}`;
}

// ------------------------------------------------------------------ users
const emailKey = (email) => 'u:' + C.hmacId(email.trim().toLowerCase());
const normEmail = (e) => String(e || '').trim().toLowerCase();
const validEmail = (e) => e.length <= 120 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(e);

// Accounts defined in CARDIOSENSE_USERS still work as a bootstrap path:
//   {"you@example.com": "scrypt$..."}  or  {"you@example.com": {"hash": "scrypt$...", "role": "admin", "name": "You"}}
function envUser(email) {
  let all;
  try { all = JSON.parse(process.env.CARDIOSENSE_USERS || '{}'); } catch { return null; }
  const e = all[email];
  if (!e) return null;
  const o = typeof e === 'string' ? { hash: e } : e;
  return {
    id: C.hmacId('env:' + email), email, name: o.name || '', role: ROLES.includes(o.role) ? o.role : 'clinician',
    pw: o.hash, createdAt: 0, disabled: false, source: 'env',
  };
}

async function findUser(email) {
  email = normEmail(email);
  if (!email) return null;
  const raw = await db.get(emailKey(email));
  if (raw) { try { return JSON.parse(raw); } catch { return null; } }
  return envUser(email);
}

async function saveUser(u) {
  await db.set(emailKey(u.email), JSON.stringify(u));
  await db.sadd('users', u.email);
}

async function createUser({ email, name, role, password, mustChange = true }) {
  email = normEmail(email);
  if (!validEmail(email)) throw Object.assign(new Error('Enter a valid email address.'), { status: 400 });
  const problem = C.passwordProblem(password, email);
  if (problem) throw Object.assign(new Error(problem), { status: 400 });
  if (await findUser(email)) throw Object.assign(new Error('An account with that email already exists.'), { status: 409 });
  const u = {
    id: C.randomId(12), email, name: String(name || '').trim().slice(0, 80), role: ROLES.includes(role) ? role : 'clinician',
    pw: C.hashPassword(password), createdAt: Date.now(), disabled: false, mustChange,
  };
  await saveUser(u);
  return u;
}

const publicUser = (u) => ({ email: u.email, name: u.name || '', role: u.role });

// ------------------------------------------------------------------ sessions
async function createSession(res, user) {
  const id = C.randomId(32);
  const now = Date.now();
  const s = { uid: user.id, email: user.email, name: user.name || '', role: user.role, csrf: C.randomId(18), created: now, seen: now, mustChange: Boolean(user.mustChange) };
  const h = C.sha256(id);
  await db.set('s:' + h, JSON.stringify(s), IDLE);
  await db.sadd('us:' + user.id, h);
  res.setHeader('Set-Cookie', cookieString(id, ABSOLUTE));
  return s;
}

async function getSession(req) {
  const id = cookies(req)[COOKIE];
  if (!id || id.length < 30 || id.length > 100) return null;
  const h = C.sha256(id);
  const raw = await db.get('s:' + h);
  if (!raw) return null;
  let s;
  try { s = JSON.parse(raw); } catch { return null; }
  const now = Date.now();
  if (now - s.created > ABSOLUTE * 1000) { await db.del('s:' + h); return null; }
  if (now - s.seen > 10 * 60 * 1000) {            // slide the idle window, at most every ten minutes
    s.seen = now;
    await db.set('s:' + h, JSON.stringify(s), Math.min(IDLE, Math.floor((s.created + ABSOLUTE * 1000 - now) / 1000)));
  }
  s.hash = h;
  return s;
}

async function endSession(req, res) {
  const id = cookies(req)[COOKIE];
  if (id) {
    const h = C.sha256(id);
    const raw = await db.get('s:' + h);
    await db.del('s:' + h);
    if (raw) { try { await db.srem('us:' + JSON.parse(raw).uid, h); } catch { /* ignore */ } }
  }
  res.setHeader('Set-Cookie', cookieString('', 0));
}

async function endAllSessions(uid) {
  for (const h of await db.smembers('us:' + uid)) await db.del('s:' + h);
  await db.del('us:' + uid);
}

// Gate for API routes. Returns the session, or answers the request and returns null.
async function requireSession(req, res, { mutating = false, role = null } = {}) {
  const s = await getSession(req);
  if (!s) { json(res, 401, { error: 'Sign in to continue.' }); return null; }
  if (mutating) {
    if (!sameOrigin(req)) { json(res, 403, { error: 'Request blocked.' }); return null; }
    if (!C.safeEqual(req.headers['x-csrf-token'] || '', s.csrf)) { json(res, 403, { error: 'Your session needs a refresh. Reload the page.' }); return null; }
  }
  if (role && s.role !== role) { json(res, 403, { error: 'You do not have access to this.' }); return null; }
  return s;
}

// ------------------------------------------------------------------ rate limits
// Fixed windows kept in the database so every serverless instance sees the same counts.
async function hit(name, id, limit, windowSeconds) {
  const n = await db.incr(`rl:${name}:${C.hmacId(id)}`, windowSeconds);
  return n > limit;
}

// ------------------------------------------------------------------ audit trail
async function audit(uid, email, ev, req, extra) {
  const row = JSON.stringify({ t: Date.now(), ev, ip: req ? C.hmacId(clientIp(req)).slice(0, 8) : '', ...(extra ? { x: String(extra).slice(0, 80) } : {}) });
  try {
    await db.push('audit:' + uid, row, 200);
    await db.push('audit:all', JSON.stringify({ ...JSON.parse(row), u: email }), 1000);
  } catch { /* the audit trail must never block the request */ }
}

// Wrap a handler so storage and unexpected errors become clean JSON responses.
function handle(fn) {
  return async (req, res) => {
    try { await fn(req, res); } catch (e) {
      if (res.headersSent) return;
      if (e && e.status) return json(res, e.status, { error: e.message });
      if (e && e.code === 'DB_UNAVAILABLE') return json(res, 503, { error: 'The service is not available right now. Try again shortly.' });
      console.error('api error:', e && e.message);
      json(res, 500, { error: 'Something went wrong. Try again.' });
    }
  };
}

module.exports = {
  json, readJson, clientIp, sameOrigin, handle,
  normEmail, validEmail, findUser, saveUser, createUser, publicUser, emailKey,
  cookies, PROD, createSession, getSession, endSession, endAllSessions, requireSession,
  hit, audit, ROLES,
  hashPassword: C.hashPassword, checkPassword: C.checkPassword,
};
