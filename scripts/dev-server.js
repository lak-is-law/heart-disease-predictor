#!/usr/bin/env node
// Local preview: serves ./portal and the ./api handlers the way Vercel does. Uses an in-memory database unless UPSTASH_* variables are set.
//   SESSION_SECRET=<32+ chars> DATA_ENCRYPTION_KEY=<base64 32 bytes> node scripts/dev-server.js
// Set MOCK_RELEASES=1 to show sample downloads without a published GitHub release.
const http = require('http');
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const types = { '.png': 'image/png', '.ico': 'image/x-icon', '.json': 'application/json', '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml' };

if (process.env.MOCK_RELEASES) {
  const real = global.fetch;
  global.fetch = async (url, opts) => {
    if (String(url).endsWith('/releases/latest')) {
      const mk = (id, name, size) => ({ id, name, size });
      return new Response(JSON.stringify({ tag_name: 'v1.0.0', assets: [
        mk(1, 'CardioSense-1.0.0-macos-arm64.dmg', 211e6), mk(2, 'CardioSense-1.0.0-macos-x64.dmg', 228e6),
        mk(3, 'CardioSense-1.0.0-windows-x64-setup.exe', 187e6), mk(4, 'CardioSense-1.0.0-windows-arm64-setup.exe', 183e6),
        mk(5, 'SHA256SUMS.txt', 600)] }), { status: 200 });
    }
    if (String(url).includes('/releases/assets/')) return new Response(null, { status: 302, headers: { location: 'http://localhost/signed' } });
    return real(url, opts);
  };
}

function createServer() {
  return http.createServer((req, res) => {
  const u = new URL(req.url, 'http://x');
  if (u.pathname === '/api/logout') {
    return require(path.join(root, 'api', 'session.js'))(req, res);
  }
  const oa = u.pathname.match(/^\/api\/oauth\/([a-z]+)(\/callback)?$/);
  if (oa) { u.searchParams.set('provider', oa[1]); u.searchParams.set('step', oa[2] ? 'callback' : 'start'); req.url = '/api/oauth?' + u.searchParams; return require(path.join(root, 'api', 'oauth.js'))(req, res); }
  const api = u.pathname.match(/^\/api\/([a-z]+)$/);
  if (api && fs.existsSync(path.join(root, 'api', api[1] + '.js'))) {
    return require(path.join(root, 'api', api[1] + '.js'))(req, res);
  }
  let p = u.pathname === '/' ? '/index.html' : u.pathname;
  if (!path.extname(p)) p += '.html';
  const file = path.join(root, 'portal', path.normalize(p));
  if (!file.startsWith(path.join(root, 'portal')) || !fs.existsSync(file)) { res.statusCode = 404; res.setHeader('Content-Type', 'text/html; charset=utf-8'); return fs.createReadStream(path.join(root, 'portal', '404.html')).pipe(res); }
  res.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
  });
}
module.exports = { createServer };

if (require.main === module) {
  createServer().listen(process.env.PORT || 3000, () => console.log('http://localhost:' + (process.env.PORT || 3000)));
}
