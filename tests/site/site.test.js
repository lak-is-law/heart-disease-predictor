'use strict';
// Static checks for the public site: node --test tests/site/
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const P = path.join(__dirname, '..', '..', 'portal');
const pages = ['index', 'about', 'features', 'download', 'signin', 'signup', 'app', '404', 'dashboard', 'report', 'unsubscribe', 'privacy', 'terms', 'research'];

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

test('mobile post-login navigation, dashboard tables, and portal markup stay consistent', () => {
  const siteJs = fs.readFileSync(path.join(P, 'site.js'), 'utf8');
  assert.match(siteJs, /renderMobileNavAccount/);
  assert.match(siteJs, /m-acct-av/);
  const dashJs = fs.readFileSync(path.join(P, 'dashboard.js'), 'utf8');
  assert.match(dashJs, /data-label/);
  const appHtml = fs.readFileSync(path.join(P, 'app.html'), 'utf8');
  assert.match(appHtml, /safety-net-slider/);
  assert.equal((appHtml.match(/<nav(?:\s|>)/g) || []).length, (appHtml.match(/<\/nav>/g) || []).length);
  assert.equal((appHtml.match(/<button(?:\s|>)/g) || []).length, (appHtml.match(/<\/button>/g) || []).length);
  const featHtml = fs.readFileSync(path.join(P, 'features.html'), 'utf8');
  assert.match(featHtml, /href="\/research"/);
  for (const n of ['signin', 'signup']) {
    const authHtml = fs.readFileSync(path.join(P, n + '.html'), 'utf8');
    assert.ok(!authHtml.includes('href="/#reviews" aria-current="page"'), n);
  }
  for (const css of ['site.css', 'styles.css', 'theme.css', 'chat.css', 'hero.css', 'app-light.css']) {
    const s = fs.readFileSync(path.join(P, css), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
    let d = 0;
    for (const ch of s) { if (ch === '{') d++; else if (ch === '}') d--; assert.ok(d >= 0, css); }
    assert.equal(d, 0, css);
  }
});

test('dashboard profile editing, arrow tutorial and delete account assets are wired', () => {
  const dashHtml = fs.readFileSync(path.join(P, 'dashboard.html'), 'utf8');
  for (const id of ['profile-form', 'prof-name', 'prof-role', 'prof-ref', 'dash-onboard-banner', 'dash-tour-btn', 'dash-delete-panel', 'delete-req-form', 'delete-confirm-form', 'del-phrase', 'del-yes']) {
    assert.match(dashHtml, new RegExp(`id="${id}"`), id);
  }
  const obJs = fs.readFileSync(path.join(P, 'onboarding.js'), 'utf8');
  assert.match(obJs, /How did you hear about us/);
  assert.match(obJs, /CSOnboard/);
  const tutJs = fs.readFileSync(path.join(P, 'tutorial.js'), 'utf8');
  assert.match(tutJs, /CSTutorial/);
  assert.match(tutJs, /cs-tut-arrow/);
});

test('deployment stays within the existing 12-function budget', () => {
  const root = path.join(P, '..');
  assert.ok(fs.readdirSync(path.join(root, 'api')).filter(name => name.endsWith('.js')).length <= 12);
  const config = JSON.parse(fs.readFileSync(path.join(root, 'vercel.json'), 'utf8'));
  assert.ok(config.rewrites.some(rule => rule.source === '/api/pilot' && rule.destination === '/api/account?route=pilot'));
});
