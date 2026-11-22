'use strict';
// Storage layer. Production uses Upstash Redis over its REST API (what Vercel's "Upstash for Redis"
// and legacy "KV" integrations provide); local development and tests use an in-process store.
// Only a handful of commands are used, so both backends implement the same small surface.
const fs = require('fs');

class DbUnavailable extends Error {
  constructor(msg) { super(msg || 'Database is not configured.'); this.code = 'DB_UNAVAILABLE'; }
}

// ---------------------------------------------------------------- Upstash REST
class Upstash {
  constructor(url, token) { this.url = url.replace(/\/+$/, ''); this.token = token; }
  async cmd(...args) {
    let res;
    try {
      res = await fetch(this.url, {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + this.token, 'Content-Type': 'application/json' },
        body: JSON.stringify(args.map((a) => (typeof a === 'string' ? a : String(a)))),
      });
    } catch { throw new DbUnavailable('Database is unreachable.'); }
    const body = await res.json().catch(() => ({}));
    if (!res.ok || body.error) throw new DbUnavailable('Database request failed.');
    return body.result;
  }
}

// ---------------------------------------------------------------- in-process store
class Memory {
  constructor(file) {
    this.data = new Map(); // key -> { v, exp }
    this.file = file || null;
    if (this.file && fs.existsSync(this.file)) {
      try { for (const [k, e] of JSON.parse(fs.readFileSync(this.file, 'utf8'))) this.data.set(k, e); } catch { /* start empty */ }
    }
  }
  _save() {
    if (this.file) fs.writeFileSync(this.file, JSON.stringify([...this.data]), { mode: 0o600 });
  }
  _get(k) {
    const e = this.data.get(k);
    if (!e) return undefined;
    if (e.exp && e.exp <= Date.now()) { this.data.delete(k); return undefined; }
    return e;
  }
  async cmd(op, key, ...a) {
    op = op.toUpperCase();
    const e = this._get(key);
    const set = (v, exp) => { this.data.set(key, { v, exp: exp === undefined ? (e && e.exp) || 0 : exp }); this._save(); };
    switch (op) {
      case 'GET': return e ? e.v : null;
      case 'SET': {
        let ex = 0, nx = false;
        for (let i = 1; i < a.length; i++) {
          const o = String(a[i]).toUpperCase();
          if (o === 'EX') ex = Date.now() + Number(a[++i]) * 1000;
          else if (o === 'NX') nx = true;
        }
        if (nx && e) return null;
        set(String(a[0]), ex); return 'OK';
      }
      case 'DEL': { const had = Boolean(e); this.data.delete(key); this._save(); return had ? 1 : 0; }
      case 'INCR': { const n = (e ? Number(e.v) : 0) + 1; set(String(n)); return n; }
      case 'EXPIRE': if (!e) return 0; e.exp = Date.now() + Number(a[0]) * 1000; this._save(); return 1;
      case 'HSET': { const h = e ? e.v : {}; for (let i = 0; i < a.length; i += 2) h[a[i]] = String(a[i + 1]); set(h); return 1; }
      case 'HGET': return e && e.v[a[0]] !== undefined ? e.v[a[0]] : null;
      case 'HGETALL': return e ? Object.entries(e.v).flat() : [];
      case 'HDEL': { if (!e) return 0; let n = 0; for (const f of a) if (delete e.v[f]) n++; this._save(); return n; }
      case 'HLEN': return e ? Object.keys(e.v).length : 0;
      case 'LPUSH': { const l = e ? e.v : []; for (const x of a) l.unshift(String(x)); set(l); return l.length; }
      case 'LTRIM': { if (e) { e.v = e.v.slice(Number(a[0]), Number(a[1]) + 1); this._save(); } return 'OK'; }
      case 'LRANGE': { if (!e) return []; const s = Number(a[0]), t = Number(a[1]); return e.v.slice(s, t === -1 ? undefined : t + 1); }
      case 'SADD': { const s = e ? e.v : []; for (const x of a) if (!s.includes(String(x))) s.push(String(x)); set(s); return 1; }
      case 'SREM': { if (!e) return 0; e.v = e.v.filter((x) => !a.includes(x)); this._save(); return 1; }
      case 'SMEMBERS': return e ? [...e.v] : [];
      default: throw new Error('Unsupported command ' + op);
    }
  }
}

let backend = null;
function pick() {
  if (backend) return backend;
  const url = process.env.UPSTASH_REDIS_REST_URL || process.env.KV_REST_API_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN || process.env.KV_REST_API_TOKEN;
  if (url && token) backend = new Upstash(url, token);
  else if (process.env.NODE_ENV !== 'production' && !process.env.VERCEL) backend = new Memory(process.env.CARDIOSENSE_DEV_DB_FILE);
  else throw new DbUnavailable('No database is configured. Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN.');
  return backend;
}

const run = (...a) => pick().cmd(...a);
const asObject = (flat) => {
  const o = {};
  for (let i = 0; i < flat.length; i += 2) o[flat[i]] = flat[i + 1];
  return o;
};

module.exports = {
  DbUnavailable,
  _reset() { backend = null; },
  _Memory: Memory,
  get: (k) => run('GET', k),
  set: (k, v, ttlSeconds) => (ttlSeconds ? run('SET', k, v, 'EX', ttlSeconds) : run('SET', k, v)),
  setIfAbsent: async (k, v) => (await run('SET', k, v, 'NX')) === 'OK',
  del: (k) => run('DEL', k),
  incr: async (k, ttlSeconds) => { const n = Number(await run('INCR', k)); if (n === 1 && ttlSeconds) await run('EXPIRE', k, ttlSeconds); return n; },
  hset: (k, f, v) => run('HSET', k, f, v),
  hget: (k, f) => run('HGET', k, f),
  hgetall: async (k) => asObject((await run('HGETALL', k)) || []),
  hdel: (k, ...f) => run('HDEL', k, ...f),
  hlen: async (k) => Number(await run('HLEN', k)),
  push: async (k, v, cap) => { await run('LPUSH', k, v); if (cap) await run('LTRIM', k, 0, cap - 1); },
  range: async (k, n) => (await run('LRANGE', k, 0, n - 1)) || [],
  sadd: (k, m) => run('SADD', k, m),
  srem: (k, m) => run('SREM', k, m),
  smembers: async (k) => (await run('SMEMBERS', k)) || [],
};
