'use strict';
const crypto = require('crypto');

const COOKIE = 'cs_session';
const MAX_AGE = 60 * 60 * 24 * 7; // 7 days

function secret() {
  const s = process.env.SESSION_SECRET;
  if (!s || s.length < 32) throw new Error('SESSION_SECRET must be set to at least 32 characters.');
  return s;
}

const hmac = (body) => crypto.createHmac('sha256', secret()).update(body).digest('base64url');

function sign(payload) {
  const body = Buffer.from(JSON.stringify(payload)).toString('base64url');
  return `${body}.${hmac(body)}`;
}

function verify(token) {
  if (!token || typeof token !== 'string') return null;
  const [body, sig] = token.split('.');
  if (!body || !sig) return null;
  const a = Buffer.from(sig);
  const b = Buffer.from(hmac(body));
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  try {
    const p = JSON.parse(Buffer.from(body, 'base64url').toString());
    return p && p.exp > Date.now() / 1000 && p.sub ? p : null;
  } catch {
    return null;
  }
}

function cookies(req) {
  const out = {};
  for (const part of (req.headers.cookie || '').split(';')) {
    const i = part.indexOf('=');
    if (i > 0) out[part.slice(0, i).trim()] = decodeURIComponent(part.slice(i + 1).trim());
  }
  return out;
}

function getUser(req) {
  const p = verify(cookies(req)[COOKIE]);
  return p ? { email: p.sub } : null;
}

function setSession(res, email) {
  const token = sign({ sub: email, exp: Math.floor(Date.now() / 1000) + MAX_AGE });
  res.setHeader('Set-Cookie', cookieString(token, MAX_AGE));
}

function clearSession(res) {
  res.setHeader('Set-Cookie', cookieString('', 0));
}

function cookieString(value, maxAge) {
  const secure = process.env.NODE_ENV === 'production' || process.env.VERCEL ? '; Secure' : '';
  return `${COOKIE}=${value}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAge}${secure}`;
}

// Users live in the CARDIOSENSE_USERS env var: {"email": "scrypt$N$salt$hash"}
function users() {
  try {
    return JSON.parse(process.env.CARDIOSENSE_USERS || '{}');
  } catch {
    return {};
  }
}

function hashPassword(password) {
  const N = 16384;
  const salt = crypto.randomBytes(16).toString('base64url');
  const hash = crypto.scryptSync(password, salt, 64, { N }).toString('base64url');
  return `scrypt$${N}$${salt}$${hash}`;
}

const DUMMY = hashPassword('placeholder-for-constant-time');

function checkPassword(password, stored) {
  const [, n, salt, hash] = (stored || DUMMY).split('$');
  const expected = Buffer.from(hash, 'base64url');
  const actual = crypto.scryptSync(password, salt, expected.length, { N: Number(n) });
  return Boolean(stored) && crypto.timingSafeEqual(actual, expected);
}

// Reject cross-site form posts: the Origin header must match this host.
function sameOrigin(req) {
  const origin = req.headers.origin;
  if (!origin) return true;
  try {
    return new URL(origin).host === req.headers.host;
  } catch {
    return false;
  }
}

async function readJson(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  if (typeof req.body === 'string') {
    try { return JSON.parse(req.body); } catch { return {}; }
  }
  const chunks = [];
  let size = 0;
  for await (const c of req) {
    size += c.length;
    if (size > 10_000) return {};
    chunks.push(c);
  }
  try { return JSON.parse(Buffer.concat(chunks).toString() || '{}'); } catch { return {}; }
}

function json(res, status, body) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(body));
}

// Best-effort limiter (per server instance): 8 failed attempts per 10 minutes per IP.
const failures = new Map();
function limited(ip) {
  const now = Date.now();
  const list = (failures.get(ip) || []).filter((t) => now - t < 600_000);
  failures.set(ip, list);
  return list.length >= 8;
}
function recordFailure(ip) {
  failures.set(ip, [...(failures.get(ip) || []), Date.now()]);
}

module.exports = {
  getUser, setSession, clearSession, users, hashPassword, checkPassword,
  sameOrigin, readJson, json, limited, recordFailure,
};
