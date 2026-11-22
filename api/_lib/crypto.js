'use strict';
// Hashing, password storage and field-level encryption.
const crypto = require('crypto');

function need(name, min) {
  const v = process.env[name];
  if (!v || v.length < min) throw new Error(`${name} must be set (at least ${min} characters).`);
  return v;
}

const sha256 = (s) => crypto.createHash('sha256').update(s).digest('hex');
// Keyed hash so emails and IPs never appear in the database as plain keys.
const hmacId = (s) => crypto.createHmac('sha256', need('SESSION_SECRET', 32)).update(String(s)).digest('hex').slice(0, 40);
const randomId = (bytes = 32) => crypto.randomBytes(bytes).toString('base64url');

// ---- passwords: scrypt, parameters stored with each hash so they can be raised later
const SCRYPT = { N: 32768, r: 8, p: 1 };
function scrypt(password, salt, len, { N, r, p }) {
  return crypto.scryptSync(password.normalize('NFKC'), salt, len, { N, r, p, maxmem: 128 * N * r * 2 });
}
function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('base64url');
  const hash = scrypt(password, salt, 64, SCRYPT).toString('base64url');
  return `scrypt$${SCRYPT.N}$${SCRYPT.r}$${salt}$${hash}`;
}
const DUMMY = hashPassword('placeholder-for-constant-time');
function checkPassword(password, stored) {
  const parts = (stored || DUMMY).split('$');
  // legacy format: scrypt$N$salt$hash (r = 8)
  const [, n, r, salt, hash] = parts.length === 4 ? [parts[0], parts[1], '8', parts[2], parts[3]] : parts;
  const expected = Buffer.from(hash, 'base64url');
  const actual = scrypt(password, salt, expected.length, { N: Number(n), r: Number(r), p: 1 });
  return Boolean(stored) && crypto.timingSafeEqual(actual, expected);
}

const COMMON = new Set(['password1234', '123456789012', 'qwertyuiop12', 'iloveyou1234', 'administrator', 'cardiosense123', 'letmein123456']);
function passwordProblem(password, email) {
  if (typeof password !== 'string' || password.length < 12) return 'Use at least 12 characters.';
  if (password.length > 200) return 'Use at most 200 characters.';
  if (COMMON.has(password.toLowerCase())) return 'That password is too common.';
  if (email && password.toLowerCase().includes(String(email).split('@')[0].toLowerCase()) && String(email).split('@')[0].length > 3) return 'Do not include your email name in the password.';
  if (/^(.)\1+$/.test(password)) return 'Use a less repetitive password.';
  return null;
}

// ---- field encryption: AES-256-GCM. Token = v1.<keyId>.<iv>.<tag>.<ciphertext>
// DATA_ENCRYPTION_KEY is 32 random bytes, base64. To rotate, set the new key and move the old one
// to DATA_ENCRYPTION_KEY_PREVIOUS; records re-encrypt under the new key when next saved.
function key(b64) {
  const k = Buffer.from(b64, 'base64');
  if (k.length !== 32) throw new Error('DATA_ENCRYPTION_KEY must be 32 random bytes, base64 encoded.');
  return { id: sha256(k).slice(0, 8), k };
}
function keys() {
  const cur = key(need('DATA_ENCRYPTION_KEY', 40));
  const prev = process.env.DATA_ENCRYPTION_KEY_PREVIOUS ? [key(process.env.DATA_ENCRYPTION_KEY_PREVIOUS)] : [];
  return { cur, all: [cur, ...prev] };
}
function encrypt(obj, aad) {
  const { cur } = keys();
  const iv = crypto.randomBytes(12);
  const c = crypto.createCipheriv('aes-256-gcm', cur.k, iv);
  c.setAAD(Buffer.from(aad));
  const ct = Buffer.concat([c.update(JSON.stringify(obj), 'utf8'), c.final()]);
  return ['v1', cur.id, iv.toString('base64url'), c.getAuthTag().toString('base64url'), ct.toString('base64url')].join('.');
}
function decrypt(token, aad) {
  const [v, kid, iv, tag, ct] = String(token).split('.');
  if (v !== 'v1' || !ct) throw new Error('Unreadable record.');
  const found = keys().all.find((x) => x.id === kid);
  if (!found) throw new Error('No key for this record.');
  const d = crypto.createDecipheriv('aes-256-gcm', found.k, Buffer.from(iv, 'base64url'));
  d.setAAD(Buffer.from(aad));
  d.setAuthTag(Buffer.from(tag, 'base64url'));
  return JSON.parse(Buffer.concat([d.update(Buffer.from(ct, 'base64url')), d.final()]).toString('utf8'));
}

const safeEqual = (a, b) => {
  const x = Buffer.from(String(a)), y = Buffer.from(String(b));
  return x.length === y.length && crypto.timingSafeEqual(x, y);
};

module.exports = { sha256, hmacId, randomId, hashPassword, checkPassword, passwordProblem, encrypt, decrypt, safeEqual };
