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
const ROLES = ['clinician', 'admin', 'user'];
const PROFILE_ROLES = [
  'Clinician / Physician', 'Medical Student / Resident', 'Researcher / Academic',
  'Data Scientist / Engineer', 'Educator / Instructor', 'Personal / Curious Learner', 'Other',
];
const EXPERIENCE_LEVELS = ['Exploring', 'Student / Trainee', 'Practicing', 'Research / Academic'];
const REFERRAL_SOURCES = [
  'Search engine', 'GitHub / Open source', 'Colleague or friend', 'University or class',
  'Social media', 'Research paper', 'AI assistant', 'Other',
];
const USE_CASES = [
  'Coronary risk estimation', 'Interactive 3D heart & ECG', 'Lab report import',
  'Selective-escalation research', 'Teaching & case studies', 'Desktop offline app',
];

// ------------------------------------------------------------------ http helpers
function json(res, status, body) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(body));
}

async function readJson(req, limit = 20_000) {
  const tooLarge = () => Object.assign(new Error('Request body is too large.'), { status: 413 });
  if (req.body && typeof req.body === 'object') {
    if (Buffer.byteLength(JSON.stringify(req.body)) > limit) throw tooLarge();
    return req.body;
  }
  if (typeof req.body === 'string') {
    if (Buffer.byteLength(req.body) > limit) throw tooLarge();
    try { return JSON.parse(req.body); } catch { return {}; }
  }
  const chunks = [];
  let size = 0;
  for await (const c of req) {
    size += c.length;
    if (size > limit) throw tooLarge();
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

async function insertUser(user) {
  if (!(await db.setIfAbsent(emailKey(user.email), JSON.stringify(user)))) return false;
  await db.sadd('users', user.email);
  return true;
}

async function createUser({ email, name, role, password, accountType, mustChange = true }) {
  email = normEmail(email);
  if (!validEmail(email)) throw Object.assign(new Error('Enter a valid email address.'), { status: 400 });
  const problem = C.passwordProblem(password, email);
  if (problem) throw Object.assign(new Error(problem), { status: 400 });
  if (await findUser(email)) throw Object.assign(new Error('An account with that email already exists.'), { status: 409 });
  const u = {
    id: C.randomId(12), email, name: String(name || '').trim().slice(0, 80), role: ROLES.includes(role) ? role : 'clinician',
    accountType, pw: C.hashPassword(password), createdAt: Date.now(), disabled: false, mustChange,
  };
  if (!(await insertUser(u))) throw Object.assign(new Error('An account with that email already exists.'), { status: 409 });
  return u;
}

const cleanStr = (v, max) => String(v == null ? '' : v).replace(/[\x00-\x1f\x7f]/g, ' ').trim().slice(0, max);

function sanitizeProfile(raw, fallbackName = '') {
  const r = raw && typeof raw === 'object' ? raw : {};
  const useCase = Array.isArray(r.useCase)
    ? Array.from(new Set(r.useCase.map((x) => cleanStr(x, 60)).filter((x) => USE_CASES.includes(x)))).slice(0, USE_CASES.length)
    : [];
  const roleType = cleanStr(r.roleType, 60);
  const experience = cleanStr(r.experience, 40);
  const referralSource = cleanStr(r.referralSource, 60);
  return {
    name: r.name !== undefined ? cleanStr(r.name, 80) : cleanStr(fallbackName, 80),
    headline: cleanStr(r.headline, 100),
    roleType: PROFILE_ROLES.includes(roleType) ? roleType : '',
    organization: cleanStr(r.organization, 100),
    country: cleanStr(r.country, 60),
    experience: EXPERIENCE_LEVELS.includes(experience) ? experience : '',
    useCase,
    referralSource: REFERRAL_SOURCES.includes(referralSource) ? referralSource : '',
    referralDetail: cleanStr(r.referralDetail, 120),
    acceptedGuidelines: Boolean(r.acceptedGuidelines),
    onboardedAt: Number(r.onboardedAt) > 0 ? Number(r.onboardedAt) : null,
    onboardingSkippedAt: Number(r.onboardingSkippedAt) > 0 ? Number(r.onboardingSkippedAt) : null,
    tourSeenAt: Number(r.tourSeenAt) > 0 ? Number(r.tourSeenAt) : null,
  };
}

async function getProfile(uid) {
  if (!uid) return null;
  const raw = await db.get('prof:' + uid);
  if (!raw) return null;
  try { return sanitizeProfile(JSON.parse(raw)); } catch { return null; }
}

async function saveProfile(uid, prof) {
  const clean = sanitizeProfile(prof);
  await db.set('prof:' + uid, JSON.stringify(clean));
  return clean;
}

const publicUser = (u, prof) => {
  const name = prof && prof.name !== undefined ? prof.name : (u.name || '');
  return {
    email: u.email,
    name,
    role: u.role,
    onboarded: Boolean(prof && prof.onboardedAt),
    onboardingSkipped: Boolean(prof && prof.onboardingSkippedAt),
    tourSeen: Boolean(prof && prof.tourSeenAt),
  };
};

// ------------------------------------------------------------------ sessions
async function createSession(res, user, profOverride) {
  const id = C.randomId(32);
  const now = Date.now();
  const prof = profOverride !== undefined ? profOverride : await getProfile(user.id);
  const name = prof && prof.name !== undefined ? prof.name : (user.name || '');
  const s = {
    uid: user.id, email: user.email, name, role: user.role, accountType: await require('./pilot').accountType(user.id,user.role,user.accountType), csrf: C.randomId(18),
    created: now, seen: now, mustChange: Boolean(user.mustChange),
    onboarded: Boolean(prof && prof.onboardedAt),
    onboardingSkipped: Boolean(prof && prof.onboardingSkippedAt),
    tourSeen: Boolean(prof && prof.tourSeenAt),
  };
  const h = C.sha256(id);
  await db.set('s:' + h, JSON.stringify(s), IDLE);
  await db.sadd('us:' + user.id, h);
  res.setHeader('Set-Cookie', cookieString(id, ABSOLUTE));
  return s;
}

async function syncSessions(uid, patch) {
  const now = Date.now();
  for (const h of await db.smembers('us:' + uid)) {
    const raw = await db.get('s:' + h);
    if (!raw) continue;
    try {
      const s = JSON.parse(raw);
      Object.assign(s, patch);
      const ttl = Math.max(60, Math.min(IDLE, Math.floor((s.created + ABSOLUTE * 1000 - now) / 1000)));
      await db.set('s:' + h, JSON.stringify(s), ttl);
    } catch { /* ignore */ }
  }
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

async function deleteUserAccount(user) {
  if (!user || user.source === 'env') {
    throw Object.assign(new Error('This bootstrap account is defined in environment variables and cannot be deleted here.'), { status: 400 });
  }
  await require('./assessment-sync').close(user.id);
  await endAllSessions(user.id);
  await require("./pilot").erase(user.id);
  for (const k of await db.smembers('uoi:' + user.id)) await db.del(k);
  await db.del('uoi:' + user.id);
  await db.del('prof:' + user.id);
  await db.del('a:' + user.id);
  await db.del('audit:' + user.id);
  await db.del('del:' + user.id);
  await db.hdel('reviews', C.hmacId('review:' + user.id));
  await db.srem('users', user.email);
  await db.del(emailKey(user.email));
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
  normEmail, validEmail, findUser, saveUser, insertUser, createUser, publicUser, emailKey,
  getProfile, saveProfile, sanitizeProfile, cleanStr, deleteUserAccount,
  PROFILE_ROLES, EXPERIENCE_LEVELS, REFERRAL_SOURCES, USE_CASES,
  cookies, PROD, createSession, syncSessions, getSession, endSession, endAllSessions, requireSession,
  hit, audit, ROLES,
  hashPassword: C.hashPassword, checkPassword: C.checkPassword,
};
