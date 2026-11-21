'use strict';

const REPO = () => process.env.GITHUB_REPO || 'lak-is-law/heart-disease-predictor';
const headers = (accept) => ({
  Accept: accept,
  'User-Agent': 'cardiosense-portal',
  ...(process.env.GITHUB_TOKEN ? { Authorization: `Bearer ${process.env.GITHUB_TOKEN}` } : {}),
});

// Map a release asset file name to one of the four supported builds.
function kindOf(name) {
  const n = name.toLowerCase();
  const arm = /(arm64|aarch64|apple)/.test(n);
  if (n.endsWith('.dmg')) return arm ? 'mac-arm64' : /(x64|x86_64|intel|amd64)/.test(n) ? 'mac-x64' : null;
  if (n.endsWith('.exe')) return arm ? 'win-arm64' : /(x64|x86_64|amd64)/.test(n) ? 'win-x64' : null;
  return null;
}

let cache = { at: 0, value: null };

async function latest() {
  if (cache.value && Date.now() - cache.at < 60_000) return cache.value;
  const r = await fetch(`https://api.github.com/repos/${REPO()}/releases/latest`, {
    headers: headers('application/vnd.github+json'),
  });
  if (r.status === 404) return (cache = { at: Date.now(), value: { version: null, builds: [] } }).value;
  if (!r.ok) throw new Error(`GitHub responded ${r.status}`);
  const rel = await r.json();
  const builds = [];
  let checksums = null;
  for (const a of rel.assets || []) {
    const kind = kindOf(a.name);
    if (kind) builds.push({ id: a.id, kind, name: a.name, size: a.size });
    if (/sha256/i.test(a.name)) checksums = { id: a.id, name: a.name };
  }
  // Attach each build's SHA-256 from the release's checksums file ("<hash>  <file name>" per line).
  if (checksums) {
    try {
      const url = await signedUrl(checksums.id);
      const text = url ? await (await fetch(url)).text() : '';
      for (const line of text.split(/\r?\n/)) {
        const m = line.trim().match(/^([a-f0-9]{64})\s+\*?(.+)$/i);
        const b = m && builds.find((x) => x.name === m[2].trim());
        if (b) b.sha256 = m[1].toLowerCase();
      }
    } catch { /* checksums are optional */ }
  }
  const value = { version: String(rel.tag_name || '').replace(/^v/, ''), builds, checksums };
  cache = { at: Date.now(), value };
  return value;
}

// Resolve an asset to a short-lived signed URL (works for private repos too).
async function signedUrl(id) {
  const r = await fetch(`https://api.github.com/repos/${REPO()}/releases/assets/${id}`, {
    headers: headers('application/octet-stream'),
    redirect: 'manual',
  });
  const loc = r.headers.get('location');
  return r.status >= 300 && r.status < 400 && loc ? loc : null;
}

module.exports = { latest, signedUrl, kindOf };
