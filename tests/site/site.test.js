'use strict';
// Static checks for the public site: node --test tests/site/
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const P = path.join(__dirname, '..', '..', 'portal');
const pages = ['index', 'features', 'download', 'signin', 'signup', 'app', '404'];

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

test('404 page exists and marketing pages load the help chat', () => {
  assert.ok(fs.existsSync(path.join(P, '404.html')));
  for (const n of ['index', 'features', 'download', 'signin', 'signup', '404']) {
    const html = fs.readFileSync(path.join(P, n + '.html'), 'utf8');
    assert.match(html, /\/chat\.js/, n); assert.match(html, /\/chat\.css/, n);
  }
});

test('help chat answers in English and Hindi and handles emergencies', () => {
  global.window = {}; global.document = undefined;
  delete require.cache[require.resolve(path.join(P, 'chat.js'))];
  require(path.join(P, 'chat.js'));
  const C = global.window.CSChat;
  assert.match(C.reply('Is it a medical device?', 'en').text, /not a medical device/);
  assert.match(C.reply('क्या यह मेडिकल डिवाइस है?', 'hi').text, /नहीं/);
  assert.match(C.reply('how do I download for windows', 'en').text, /SHA-256/);
  const e = C.reply('I have chest pain', 'en'); assert.ok(e.warn); assert.match(e.text, /112/);
  assert.match(C.reply('xyzzy', 'en').text, /could not find/);
  assert.match(C.reply('Do I have heart disease?', 'en').text, /cannot give medical advice/);
});
