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
  function closeMenu() {
    var n = document.querySelector('.nav');
    var mb = document.querySelector('[data-menu-toggle]');
    if (n) n.classList.remove('open');
    if (mb) mb.setAttribute('aria-expanded', 'false');
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-theme-toggle]');
    if (b) setTheme(isDark() ? 'light' : 'dark');
    var mb = e.target.closest('[data-menu-toggle]');
    if (mb) { var n = document.querySelector('.nav'); var o = n.classList.toggle('open'); mb.setAttribute('aria-expanded', o); return; }
    if (e.target.closest('.nav a')) { closeMenu(); return; }
    if (!e.target.closest('.site-head')) closeMenu();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeMenu(); });

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
    var choice = $('workspace');
    if (choice && choice.value) return '/pilot#' + choice.value;
    var n = new URLSearchParams(location.search).get('next') || '';
    return /^\/[a-z0-9\-_/]*(#[a-z0-9\-_]*)?$/i.test(n) && n.slice(0, 2) !== '//' ? n : '/pilot';
  }

  // ---------------------------------------------------------------- header account
  function initials(u) {
    var parts = (u.name || u.email || '?').trim().split(/\s+/);
    if (parts.length > 1) return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
    return (parts[0] || '?').charAt(0).toUpperCase();
  }
  function doSignOut() { api('POST', '/api/logout').then(function () { location.href = '/'; }); }
  function renderMobileNavAccount() {
    var nav = document.querySelector('.site-head .nav'); if (!nav) return;
    nav.querySelectorAll('.m-only').forEach(function (n) { n.remove(); });
    if (S.user) {
      var who = el('span', 'm-only m-user', S.user.name ? S.user.name + ' (' + S.user.email + ')' : S.user.email);
      var d = el('a', 'm-only', 'Dashboard'); d.href = '/dashboard';
      if (location.pathname === '/dashboard' || location.pathname === '/dashboard.html') d.setAttribute('aria-current', 'page');
      var o = el('button', 'm-only m-signout', 'Sign out'); o.type = 'button';
      o.addEventListener('click', function () { closeMenu(); doSignOut(); });
      nav.append(who, d, o);
    } else {
      var si = el('a', 'm-only', 'Sign in'); si.href = '/signin';
      var su = el('a', 'm-only', 'Create account'); su.href = '/signup';
      nav.append(si, su);
    }
  }
  function renderAccount() {
    var box = $('acct');
    if (box) {
      box.textContent = '';
      if (S.user) {
        var d = el('a', 'link', 'Dashboard'); d.href = '/dashboard';
        var o = el('button', 'btn sm line', 'Sign out'); o.type = 'button';
        o.addEventListener('click', doSignOut);
        var av = el('a', 'm-acct-av', initials(S.user)); av.href = '/dashboard';
        av.setAttribute('aria-label', 'Dashboard'); av.title = 'Dashboard';
        box.append(d, o, av);
      } else {
        var si = el('a', 'link', 'Sign in'); si.href = '/signin';
        var su = el('a', 'btn sm', 'Get started'); su.href = '/signup';
        box.append(si, su);
      }
    }
    renderMobileNavAccount();
  }
  S.setUser = function (u) { S.user = u || null; renderAccount(); };
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
  var OSICON = {
    mac: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701"/></svg>',
    win: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3 5.5l7.6-1v7H3zM11.6 4.4L21 3v8.5h-9.4zM3 12.5h7.6v7L3 18.5zM11.6 12.5H21V21l-9.4-1.3z"/></svg>'
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
        var ic = el('span', 'os-ic'); ic.innerHTML = OSICON[b.kind.indexOf('mac') === 0 ? 'mac' : 'win']; row.appendChild(ic);
        var n = el('div'); n.appendChild(el('b', '', info[0] + ' ' + info[2])); n.appendChild(el('span', '', info[1])); row.appendChild(n);
        row.appendChild(el('span', 'meta', 'Version ' + d.version + ' \u00b7 ' + mb(b.size)));
        if (b.sha256) {
          var sum = el('button', 'sum', 'SHA-256 ' + b.sha256.slice(0, 12) + '\u2026'); sum.type = 'button'; sum.title = b.sha256 + ' (click to copy)';
          sum.addEventListener('click', async function () {
            try {
              await navigator.clipboard.writeText(b.sha256);
              sum.textContent = 'Copied';
              setTimeout(function () { sum.textContent = 'SHA-256 ' + b.sha256.slice(0, 12) + '\u2026'; }, 1500);
            } catch (e) {
              sum.textContent = b.sha256;
              sum.classList.add('show-checksum');
            }
          });
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
      if (!d.ok) throw new Error('Reviews unavailable');
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
    }).catch(function () {
      $('rev-avg').textContent = '–'; $('rev-stars').textContent = '';
      $('rev-count').textContent = 'Reviews unavailable';
      rl.textContent = 'Could not load reviews. Refresh to try again.';
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
      }).catch(function () { m.textContent = 'Could not publish the review. Try again.'; });
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
        if (p.enabled) {
          const refresh = () => { a.href = '/api/oauth/' + p.id + '?next=' + encodeURIComponent(nextUrl()); };
          refresh(); $('workspace').addEventListener('change', refresh);
        }
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

/* home splash: show once per session, then fade */
(function () {
  var s = document.getElementById('splash'); if (!s) return;
  function done() { s.classList.add('done'); try { sessionStorage.setItem('cs-splash', '1'); } catch (e) { /* ignore */ } setTimeout(function () { document.documentElement.classList.remove('splash'); }, 600); }
  if (!document.documentElement.classList.contains('splash')) return;
  var t0 = Date.now(); function go() { setTimeout(done, Math.max(0, 2100 - (Date.now() - t0))); }
  if (document.readyState === 'complete') go(); else window.addEventListener('load', go);
  setTimeout(done, 4000);
})();


/* bug report form */
(function () {
  var f = document.getElementById('bug-form'); if (!f) return;
  var msg = document.getElementById('bug-msg');
  var page = (document.referrer && document.referrer.indexOf(location.origin) === 0) ? document.referrer.slice(location.origin.length) : '';
  f.addEventListener('submit', function (e) {
    e.preventDefault(); msg.className = 'msg'; msg.textContent = '';
    var what = document.getElementById('bug-what').value.trim();
    if (what.length < 10) { msg.className = 'msg bad'; msg.textContent = 'Describe the problem in at least 10 characters.'; return; }
    var btn = f.querySelector('button[type=submit]'); btn.disabled = true;
    fetch('/api/bug', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ what: what, area: document.getElementById('bug-area').value, email: document.getElementById('bug-email').value.trim(), page: page, website: f.website.value }) })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return [r.ok, j]; }); })
      .then(function (x) {
        btn.disabled = false;
        if (x[0]) { f.reset(); msg.className = 'msg ok'; msg.textContent = 'Thank you. Your report was sent.'; }
        else { msg.className = 'msg bad'; msg.textContent = x[1].error || 'Could not send the report. Try again.'; }
      }).catch(function () { btn.disabled = false; msg.className = 'msg bad'; msg.textContent = 'Could not reach the server. Try again.'; });
  });
})();


/* newsletter */
(function () {
  var f = document.getElementById('news-form');
  if (f) {
    var msg = document.getElementById('news-msg');
    f.addEventListener('submit', function (e) {
      e.preventDefault(); msg.className = 'msg'; msg.textContent = '';
      var em = document.getElementById('news-email').value.trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(em)) { msg.textContent = 'Enter a valid email address.'; return; }
      var btn = f.querySelector('button'); btn.disabled = true;
      fetch('/api/subscribe', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: em, website: f.website.value }) })
        .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return [r.ok, j]; }); })
        .then(function (x) { btn.disabled = false; if (x[0]) { f.reset(); msg.className = 'msg ok'; msg.textContent = 'You are subscribed.'; } else msg.textContent = x[1].error || 'Could not subscribe. Try again.'; })
        .catch(function () { btn.disabled = false; msg.textContent = 'Could not reach the server. Try again.'; });
    });
  }
  var ub = document.getElementById('un-btn');
  if (ub) {
    var t = new URLSearchParams(location.search).get('t') || '', um = document.getElementById('un-msg');
    ub.addEventListener('click', function () {
      if (!t) { um.className = 'msg'; um.textContent = 'This link is missing its code. Use the link from the email.'; return; }
      ub.disabled = true;
      fetch('/api/subscribe', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ unsubscribe: t }) })
        .then(function (r) { um.className = r.ok ? 'msg ok' : 'msg'; um.textContent = r.ok ? 'You have been unsubscribed.' : 'Could not unsubscribe. Try again.'; ub.disabled = false; })
        .catch(function () { um.className = 'msg'; um.textContent = 'Could not reach the server.'; ub.disabled = false; });
    });
  }
})();
