'use strict';
// Static checks for the public site: node --test tests/site/
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const P = path.join(__dirname, '..', '..', 'portal');
const pages = ['index', 'features', 'download', 'signin', 'signup', 'app'];

test('every page exists and has a theme toggle (workstation included)', () => {
  for (const n of pages) {
    const html = fs.readFileSync(path.join(P, n + '.html'), 'utf8');
    assert.match(html, /data-theme-toggle/, n);
    assert.match(html, /theme-init\.js/, n);
  }
});

test('internal links and assets resolve to real files', () => {
  for (const n of pages) {
    const html = fs.readFileSync(path.join(P, n + '.html'), 'utf8');
    for (const m of html.matchAll(/(?:href|src)="(\/[^"#?]*)/g)) {
      const u = m[1];
      if (u === '/' || u.startsWith('/api/')) continue;
      const ok = fs.existsSync(path.join(P, u)) || fs.existsSync(path.join(P, u + '.html'));
      assert.ok(ok, `${n}.html links to missing ${u}`);
    }
  }
});

test('sign-in and sign-up offer Google, Microsoft, X and ChatGPT', () => {
  for (const n of ['signin', 'signup']) {
    const html = fs.readFileSync(path.join(P, n + '.html'), 'utf8');
    for (const p of ['google', 'microsoft', 'x', 'openai']) assert.match(html, new RegExp(`data-provider="${p}"`), `${n} ${p}`);
  }
});

test('the home page carries no made-up reviews or unfounded claims', () => {
  const html = fs.readFileSync(path.join(P, 'index.html'), 'utf8');
  assert.match(html, /id="rev-list"/);
  for (const bad of ['FDA', 'HIPAA', 'FIPS', 'saves lives', 'clinically validated']) assert.ok(!html.includes(bad), bad);
});

test('the QR code image is present', () => {
  assert.ok(fs.statSync(path.join(P, 'img', 'qr-download.svg')).size > 1000);
});
