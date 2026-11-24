/* CardioSense site script: theme toggle, header account, downloads, reviews, sign-in and sign-up. No dependencies. */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var S = window.CS = { user: null, csrf: '' };

  // ---------------------------------------------------------------- theme
  function setTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    try { localStorage.setItem('cs-theme', t); } catch (e) { /* ignore */ }
    var m = document.querySelector('meta[name="theme-color"]');
    if (m) m.setAttribute('content', t === 'dark' ? '#0D0D0D' : '#FFFFFF');
  }
  function isDark() {
    var t = document.documentElement.getAttribute('data-theme');
    return t ? t === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-theme-toggle]');
    if (b) setTheme(isDark() ? 'light' : 'dark');
    var mb = e.target.closest('[data-menu-toggle]');
    if (mb) { var n = document.querySelector('.nav'); var o = n.classList.toggle('open'); mb.setAttribute('aria-expanded', o); }
  });

  // ---------------------------------------------------------------- http
  function api(method, url, body) {
    var h = { 'Content-Type': 'application/json' };
    if (method !== 'GET' && S.csrf) h['X-CSRF-Token'] = S.csrf;
    return fetch(url, { method: method, credentials: 'same-origin', headers: h, body: body ? JSON.stringify(body) : undefined })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { j.ok = r.ok; j.status = r.status; return j; }); });
  }
  S.api = api;
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function nextUrl() {
    var n = new URLSearchParams(location.search).get('next') || '';
    return /^\/[a-z0-9\-_/]*(#[a-z0-9\-_]*)?$/i.test(n) && n.slice(0, 2) !== '//' ? n : '/app';
  }

  // ---------------------------------------------------------------- header account
  function renderAccount() {
    var box = $('acct'); if (!box) return;
    box.textContent = '';
    if (S.user) {
      var d = el('a', 'link', 'Dashboard'); d.href = '/app#dashboard';
      var o = el('button', 'btn sm line', 'Sign out'); o.type = 'button';
      o.addEventListener('click', function () { api('POST', '/api/logout').then(function () { location.href = '/'; }); });
      box.append(d, o);
    } else {
      var si = el('a', 'link', 'Sign in'); si.href = '/signin';
      var su = el('a', 'btn sm', 'Get started'); su.href = '/signup';
      box.append(si, su);
    }
  }
  var hd = document.querySelector('.site-head');
  if (hd) { var sc = function () { hd.classList.toggle('scrolled', window.scrollY > 8); }; window.addEventListener('scroll', sc, { passive: true }); sc(); }
  S.ready = api('GET', '/api/session').then(function (s) {
    S.user = s.user || null; S.csrf = s.csrf || '';
    renderAccount();
    document.dispatchEvent(new CustomEvent('cs:session'));
  }).catch(function () { renderAccount(); });

  // ---------------------------------------------------------------- downloads
  var LABEL = {
    'mac-arm64': ['macOS', 'Apple silicon (M1 and later)', 'DMG'], 'mac-x64': ['macOS', 'Intel', 'DMG'],
    'win-x64': ['Windows', '64-bit Intel or AMD', 'Installer'], 'win-arm64': ['Windows', 'ARM64', 'Installer'],
  };
  function guess() {
    var ua = navigator.userAgent, p = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || '';
    if (/Mac/i.test(p + ua)) return 'mac-arm64';
    if (/Win/i.test(p + ua)) return /ARM/i.test(ua) ? 'win-arm64' : 'win-x64';
    return null;
  }
  function mb(n) { return Math.round(n / 1048576) + ' MB'; }
  function renderBuilds(box, limit) {
    return fetch('/api/releases').then(function (r) { return r.json(); }).then(function (d) {
      box.textContent = '';
      if (!d.builds || !d.builds.length) {
        box.appendChild(el('div', 'empty', d.error || 'The first installers are not published yet. You can use the workstation in your browser.'));
        return;
      }
      var g = guess();
      var list = d.builds.slice().sort(function (x, y) { return (y.kind === g) - (x.kind === g); });
      list.slice(0, limit || list.length).forEach(function (b) {
        var info = LABEL[b.kind] || [b.kind, '', ''];
        var row = el('div', 'dl-row' + (b.kind === g ? ' rec' : ''));
        var n = el('div'); n.appendChild(el('b', '', info[0] + ' ' + info[2])); n.appendChild(el('span', '', info[1])); row.appendChild(n);
        row.appendChild(el('span', 'meta', 'Version ' + d.version + ' \u00b7 ' + mb(b.size)));
        if (b.sha256) {
          var sum = el('button', 'sum', 'SHA-256 ' + b.sha256.slice(0, 12) + '\u2026'); sum.type = 'button'; sum.title = b.sha256 + ' (click to copy)';
          sum.addEventListener('click', function () { try { navigator.clipboard.writeText(b.sha256); sum.textContent = 'Copied'; setTimeout(function () { sum.textContent = 'SHA-256 ' + b.sha256.slice(0, 12) + '\u2026'; }, 1500); } catch (e) { /* ignore */ } });
          row.appendChild(sum);
        } else row.appendChild(el('span', 'meta', ''));
        var a = el('a', 'btn sm', S.user ? 'Download' : 'Sign in to download');
        a.href = S.user ? '/api/download?id=' + b.id : '/signin?next=/download';
        row.appendChild(a); box.appendChild(row);
      });
    }).catch(function () { box.textContent = ''; box.appendChild(el('div', 'empty', 'Downloads could not be loaded. Refresh to try again.')); });
  }
  var bx = $('builds');
  if (bx) S.ready.then(function () { renderBuilds(bx, +bx.getAttribute('data-limit') || 0); });

  // checksum verifier (download page)
  var vf = $('verify-file');
  if (vf) vf.addEventListener('change', function () {
    var res = $('verify-res'), f = vf.files[0]; if (!f) return;
    res.textContent = 'Reading ' + f.name + '...';
    f.arrayBuffer().then(function (buf) { return crypto.subtle.digest('SHA-256', buf); }).then(function (h) {
      var hex = Array.from(new Uint8Array(h)).map(function (b) { return b.toString(16).padStart(2, '0'); }).join('');
      res.textContent = 'SHA-256 ' + hex + '. Compare it with the value listed for your download.';
      var typed = ($('verify-expected').value || '').trim().toLowerCase();
      if (typed) { res.textContent = (typed === hex ? 'Match. ' : 'Does not match. ') + res.textContent; res.style.color = typed === hex ? 'var(--ok)' : 'var(--bad)'; }
    }).catch(function () { res.textContent = 'This file could not be read.'; });
  });

  // ---------------------------------------------------------------- reviews
  var rl = $('rev-list');
  function stars(n) { return '★★★★★'.slice(0, n) + '☆☆☆☆☆'.slice(0, 5 - n); }
  function loadReviews() {
    if (!rl) return;
    api('GET', '/api/reviews').then(function (d) {
      rl.textContent = '';
      $('rev-avg').textContent = d.count ? d.average.toFixed(1) : '-';
      $('rev-count').textContent = d.count ? d.count + (d.count === 1 ? ' review' : ' reviews') : 'No reviews yet';
      $('rev-stars').textContent = d.count ? stars(Math.round(d.average)) : '';
      (d.items || []).forEach(function (r) {
        var c = el('div', 'rev'); c.appendChild(el('div', 'stars', stars(r.rating)));
        c.appendChild(el('p', '', r.text));
        c.appendChild(el('div', 'who', r.name + ' · ' + new Date(r.t).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })));
        rl.appendChild(c);
      });
      if (!d.count) rl.appendChild(el('div', 'empty', 'Be the first to review CardioSense.'));
    });
  }
  loadReviews();
  var rf = $('rev-form');
  if (rf) {
    var rating = 0, picks = rf.querySelectorAll('.star-pick button');
    picks.forEach(function (b, i) { b.addEventListener('click', function () { rating = i + 1; picks.forEach(function (x, j) { x.classList.toggle('on', j < rating); x.setAttribute('aria-pressed', j < rating); }); }); });
    S.ready.then(function () { $('rev-gate').hidden = !!S.user; rf.hidden = !S.user; });
    rf.addEventListener('submit', function (e) {
      e.preventDefault(); var m = $('rev-msg'); m.className = 'msg'; m.textContent = '';
      if (!rating) { m.textContent = 'Choose a rating.'; return; }
      api('POST', '/api/reviews', { rating: rating, text: $('rev-text').value }).then(function (r) {
        if (!r.ok) { m.textContent = r.error || 'Could not save your review.'; return; }
        m.className = 'msg ok'; m.textContent = 'Thanks. Your review is published.'; loadReviews();
      });
    });
  }

  // ---------------------------------------------------------------- sign in / sign up
  var ERR = { cancelled: 'Sign-in was cancelled.', state: 'That sign-in link expired. Try again.', provider: 'The provider did not complete sign-in. Try again.',
    email_exists: 'An account with that email already exists. Sign in with your password instead.', disabled: 'This account is disabled.', unavailable: 'That sign-in option is not set up yet.' };
  var sp = $('socials');
  if (sp) {
    var qe = new URLSearchParams(location.search).get('error'); if (qe && $('auth-msg')) $('auth-msg').textContent = ERR[qe] || 'Sign-in failed.';
    fetch('/api/oauth?providers=1').then(function (r) { return r.json(); }).then(function (d) {
      (d.providers || []).forEach(function (p) {
        var a = sp.querySelector('[data-provider="' + p.id + '"]'); if (!a) return;
        if (p.enabled) a.href = '/api/oauth/' + p.id + '?next=' + encodeURIComponent(nextUrl());
        else { a.classList.add('off'); a.setAttribute('aria-disabled', 'true'); a.removeAttribute('href'); a.title = 'Not set up on this site yet'; }
      });
      if (sp.querySelector('.off')) { var h = el('p', 'hint', 'Dimmed options are not enabled on this site yet.'); sp.appendChild(h); }
    }).catch(function () {});
  }
  function authForm(id, url, build) {
    var f = $(id); if (!f) return;
    S.ready.then(function () { if (S.user) location.replace(nextUrl()); });
    f.addEventListener('submit', function (e) {
      e.preventDefault(); var m = $('auth-msg'); m.className = 'msg'; m.textContent = '';
      var body = build(f); if (!body) return;
      var btn = f.querySelector('button[type=submit]'); btn.disabled = true;
      api('POST', url, body).then(function (r) {
        btn.disabled = false;
        if (!r.ok) { m.textContent = r.error || 'Something went wrong. Try again.'; return; }
        m.className = 'msg ok'; m.textContent = 'Signed in. Redirecting...'; location.href = nextUrl();
      }).catch(function () { btn.disabled = false; m.textContent = 'Network error. Try again.'; });
    });
  }
  authForm('signin-form', '/api/login', function (f) { return { email: f.email.value, password: f.password.value, website: f.website.value }; });
  authForm('signup-form', '/api/signup', function (f) {
    return { name: f.name.value, email: f.email.value, password: f.password.value, website: f.website.value };
  });
})();
