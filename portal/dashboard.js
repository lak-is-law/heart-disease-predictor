/* CardioSense dashboard: saved assessments, account and (for admins) people.
   Talks to /api/assessments, /api/account and /api/admin. All text is inserted with textContent. */
(function () {
  'use strict';

  var FIELDS = ['age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 'restecg', 'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal'];
  var EVENTS = {
    login: 'Signed in', logout: 'Signed out', login_failed: 'Failed sign-in attempt', assessment_saved: 'Saved an assessment',
    assessment_deleted: 'Deleted an assessment', assessments_erased: 'Erased all assessments', password_changed: 'Changed password',
    signout_all: 'Signed out everywhere', download: 'Downloaded the app', user_created: 'Created an account', user_disabled: 'Disabled an account',
    user_enabled: 'Enabled an account', user_role_changed: 'Changed a role', signup: 'Created the account', oauth_login: 'Signed in with a provider', review_saved: 'Saved a review', user_password_reset: 'Reset a password'
  };
  var items = [];
  var shown = 15;
  var $ = function (id) { return document.getElementById(id); };

  function state() { return window.csState ? window.csState() : (window.CS ? { user: window.CS.user, csrf: window.CS.csrf } : { user: null, csrf: '' }); }

  async function api(method, path, body) {
    var r = await fetch(path, {
      method: method, credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state().csrf },
      body: body ? JSON.stringify(body) : undefined
    });
    var j = await r.json().catch(function () { return {}; });
    if (r.status === 401) { if (window.csSessionLost) window.csSessionLost(); else if ($('dash-hero')) location.replace('/signin?next=/dashboard'); }
    if (!r.ok) { var e = new Error(j.error || 'Something went wrong. Try again.'); e.status = r.status; throw e; }
    return j;
  }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function clear(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function say(text, bad) {
    var m = $('dash-msg');
    if (!m) return;
    m.textContent = text || '';
    m.classList.toggle('is-bad', Boolean(bad));
    if (text) { clearTimeout(say.t); say.t = setTimeout(function () { m.textContent = ''; }, 5000); }
  }

  function band(p) { return p < 0.33 ? 'Low' : (p < 0.66 ? 'Moderate' : 'High'); }
  function label(p) { return p < 0.33 ? 'Lower' : (p < 0.66 ? 'Intermediate' : 'Higher'); }
  function pct(p) { return (p * 100).toFixed(0) + '%'; }
  function when(t) {
    var d = new Date(t);
    return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) + ', ' +
      d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  }

  // ------------------------------------------------------------ cockpit bridge
  function readCockpit() {
    var inputs = {};
    for (var i = 0; i < FIELDS.length; i++) {
      var node = $('inp-' + FIELDS[i]);
      if (!node) throw new Error('The workstation is not ready yet.');
      if (node.value === '') throw new Error('Select the vessel count and thallium result before saving.');
      inputs[FIELDS[i]] = Number(node.value);
    }
    var risk = typeof pTargetRisk === 'number' ? pTargetRisk : NaN;
    if (!isFinite(risk)) throw new Error('No risk estimate to save yet.');
    return { inputs: inputs, risk: Math.min(1, Math.max(0, risk)), model: 'cleveland-lr' };
  }

  async function saveCurrent() {
    if (!state().user) { if (window.openAuthModal) openAuthModal(); return; }
    var btn = $('dash-save');
    try {
      var body = readCockpit();
      var ref = $('dash-ref');
      body.label = ref ? ref.value.trim() : (window.csAskRef ? window.csAskRef() : '');
      if (btn) btn.disabled = true;
      var j = await api('POST', '/api/assessments', body);
      items.unshift(j.item);
      if (ref) ref.value = '';
      render();
      say('Saved. Risk ' + pct(j.item.risk) + ', ' + label(j.item.risk).toLowerCase() + ' estimate.');
      if (window.showToast) showToast('Saved to your dashboard');
    } catch (e) {
      say(e.message, true);
      if (window.showToast) showToast(e.message);
    } finally { if (btn) btn.disabled = false; }
  }

  function openInWorkstation(a) {
    if (!$('live-workstation')) {
      try { sessionStorage.setItem('cs-open', JSON.stringify(a.inputs)); } catch (e) { /* ignore */ }
      location.href = '/app'; return;
    }
    FIELDS.forEach(function (f) {
      var node = $('inp-' + f);
      if (node) node.value = String(a.inputs[f]);
    });
    if (window.updatePortalPrediction) updatePortalPrediction();
    var ws = $('live-workstation');
    if (ws) ws.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // ------------------------------------------------------------ rendering
  function renderStats() {
    var box = $('dash-stats');
    clear(box);
    var n = items.length;
    var avg = n ? items.reduce(function (s, a) { return s + a.risk; }, 0) / n : 0;
    var recent = items.filter(function (a) { return Date.now() - a.createdAt < 30 * 864e5; }).length;
    [['Saved', String(n)], ['Average risk', n ? pct(avg) : '-'], ['Last 30 days', String(recent)]]
      .forEach(function (s) {
        var t = el('div', 'hx-stat');
        t.appendChild(el('div', 'hx-stat-v', s[1]));
        t.appendChild(el('div', 'hx-stat-l', s[0]));
        box.appendChild(t);
      });
  }

  function renderTrend() {
    var svg = $('dash-trend'), empty = $('dash-trend-empty');
    var NS = 'http://www.w3.org/2000/svg';
    clear(svg);
    var pts = items.slice(0, 40).reverse();
    empty.hidden = pts.length >= 2;
    svg.style.display = pts.length >= 2 ? '' : 'none';
    if (pts.length < 2) return;
    var W = 600, H = 180, L = 34, R = 10, T = 10, B = 20;
    function y(p) { return T + (1 - p) * (H - T - B); }
    function x(i) { return L + i * (W - L - R) / (pts.length - 1); }
    [0, 0.33, 0.66, 1].forEach(function (g) {
      var ln = document.createElementNS(NS, 'line');
      ln.setAttribute('x1', L); ln.setAttribute('x2', W - R); ln.setAttribute('y1', y(g)); ln.setAttribute('y2', y(g));
      ln.setAttribute('class', 'hx-grid-line');
      svg.appendChild(ln);
      var t = document.createElementNS(NS, 'text');
      t.setAttribute('x', 0); t.setAttribute('y', y(g) + 4); t.setAttribute('class', 'hx-axis');
      t.textContent = Math.round(g * 100) + '%';
      svg.appendChild(t);
    });
    var path = document.createElementNS(NS, 'polyline');
    path.setAttribute('points', pts.map(function (a, i) { return x(i) + ',' + y(a.risk); }).join(' '));
    path.setAttribute('class', 'hx-line');
    svg.appendChild(path);
    pts.forEach(function (a, i) {
      var c = document.createElementNS(NS, 'circle');
      c.setAttribute('cx', x(i)); c.setAttribute('cy', y(a.risk)); c.setAttribute('r', 3.5);
      c.setAttribute('class', 'hx-dot ' + band(a.risk).toLowerCase());
      var tt = document.createElementNS(NS, 'title');
      tt.textContent = (a.label || 'Assessment') + ': ' + pct(a.risk) + ', ' + when(a.createdAt);
      c.appendChild(tt);
      svg.appendChild(c);
    });
  }

  function renderBands() {
    var box = $('dash-bands');
    clear(box);
    var counts = { Low: 0, Moderate: 0, High: 0 };
    items.forEach(function (a) { counts[band(a.risk)]++; });
    ['Low', 'Moderate', 'High'].forEach(function (b) {
      var row = el('div', 'hx-band');
      row.appendChild(el('span', 'hx-band-l', {Low:'Lower',Moderate:'Intermediate',High:'Higher'}[b]));
      var track = el('span', 'hx-band-track');
      var fill = el('span', 'hx-band-fill ' + b.toLowerCase());
      fill.style.width = items.length ? (counts[b] / items.length * 100) + '%' : '0%';
      track.appendChild(fill);
      row.appendChild(track);
      row.appendChild(el('span', 'hx-band-n', String(counts[b])));
      box.appendChild(row);
    });
  }

  function renderTable() {
    var body = $('dash-rows');
    clear(body);
    $('dash-empty').hidden = items.length > 0;
    $('dash-table').hidden = items.length === 0;
    $('dash-export').disabled = items.length === 0;
    items.slice(0, shown).forEach(function (a) {
      var tr = el('tr');
      tr.appendChild(el('td', 'hx-ref', a.label || 'Untitled'));
      tr.appendChild(el('td', '', when(a.createdAt)));
      tr.appendChild(el('td', '', a.inputs.age + ', ' + (a.inputs.sex === 1 ? 'male' : 'female')));
      tr.appendChild(el('td', 'hx-num', pct(a.risk)));
      var b = el('td'); b.appendChild(el('span', 'hx-chip ' + band(a.risk).toLowerCase(), label(a.risk))); tr.appendChild(b);
      var act = el('td', 'hx-actions-cell');
      var open = el('button', 'hx-linkbtn', 'Open'); open.type = 'button';
      open.setAttribute('aria-label', 'Open ' + (a.label || 'assessment') + ' in the workstation');
      open.addEventListener('click', function () { openInWorkstation(a); });
      var del = el('button', 'hx-linkbtn is-danger', 'Delete'); del.type = 'button';
      del.setAttribute('aria-label', 'Delete ' + (a.label || 'assessment'));
      del.addEventListener('click', function () { remove(a, del); });
      act.appendChild(open); act.appendChild(del); tr.appendChild(act);
      body.appendChild(tr);
    });
    $('dash-more').hidden = items.length <= shown;
  }

  function render() {
    var u = state().user;
    $('dash-sub').textContent = items.length
      ? items.length + ' saved ' + (items.length === 1 ? 'assessment' : 'assessments') + '. Stored encrypted. Use synthetic or de-identified data only.'
      : 'Your saved assessments appear here. Stored encrypted. Use synthetic or de-identified data only.';
    renderStats(); renderTrend(); renderBands(); renderTable(); renderHero();
    var line = $('acct-line');
    if (u && line) line.textContent = u.email + (u.name ? ', ' + u.name : '') + ', ' + (u.role === 'admin' ? 'admin' : 'clinician');
  }

  function firstName(u) {
    var n = (u.name || '').trim().split(/\s+/)[0];
    if (!n) n = String(u.email || '').split('@')[0].replace(/[._\-+0-9]+/g, ' ').trim().split(' ')[0];
    return n ? n.charAt(0).toUpperCase() + n.slice(1) : 'there';
  }
  function renderHero() {
    var u = state().user, hi = $('dash-hi');
    if (!u || !hi) return;
    var nm = firstName(u);
    hi.textContent = 'Hi, ' + nm;
    var parts = (u.name || nm).trim().split(/\s+/);
    $('dash-avatar').textContent = ((parts[0] || '?').charAt(0) + (parts.length > 1 ? parts[parts.length - 1].charAt(0) : '')).toUpperCase();
    var intro = $('dash-intro'), n = items.length;
    if (!n) intro.textContent = 'Welcome to CardioSense. Nothing is saved yet. Open the workstation, set up a synthetic or de-identified case and choose Save to dashboard. Your report will build up below.';
    else {
      var avg = items.reduce(function (s, a) { return s + a.risk; }, 0) / n;
      intro.textContent = 'You have ' + n + ' saved ' + (n === 1 ? 'assessment' : 'assessments') + ', the latest on ' + when(items[0].createdAt) + '. The average estimated risk across them is ' + pct(avg) + '. Scroll to see your report.';
    }
  }

  function armed(btn, label, run) {          // two-step confirm without browser dialogs
    if (btn.dataset.armed) { clearTimeout(btn._t); delete btn.dataset.armed; btn.textContent = btn.dataset.label; run(); return; }
    btn.dataset.label = btn.textContent; btn.dataset.armed = '1'; btn.textContent = label;
    btn._t = setTimeout(function () { delete btn.dataset.armed; btn.textContent = btn.dataset.label; }, 4000);
  }

  function remove(a, btn) {
    armed(btn, 'Confirm delete', async function () {
      try {
        await api('DELETE', '/api/assessments?id=' + encodeURIComponent(a.id));
        items = items.filter(function (x) { return x.id !== a.id; });
        render(); say('Deleted.');
      } catch (e) { say(e.message, true); }
    });
  }

  function exportCsv() {
    var head = ['id', 'saved_at', 'reference', 'model'].concat(FIELDS, ['risk']);
    function cell(v) {
      var s = String(v == null ? '' : v);
      if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;            // stop spreadsheet formula injection
      return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    }
    var rows = items.map(function (a) {
      return [a.id, new Date(a.createdAt).toISOString(), a.label, a.model].concat(FIELDS.map(function (f) { return a.inputs[f]; }), [a.risk]).map(cell).join(',');
    });
    var blob = new Blob([head.join(',') + '\n' + rows.join('\n') + '\n'], { type: 'text/csv' });
    var a = el('a'); a.href = URL.createObjectURL(blob); a.download = 'cardiosense-assessments.csv';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  // ------------------------------------------------------------ account
  async function loadAccount() {
    try {
      var j = await api('GET', '/api/account');
      var ul = $('acct-activity'); clear(ul);
      if (!j.activity.length) ul.appendChild(el('li', 'hx-empty', 'No activity yet.'));
      j.activity.slice(0, 12).forEach(function (r) {
        var li = el('li');
        li.appendChild(el('span', '', EVENTS[r.ev] || r.ev));
        li.appendChild(el('time', '', when(r.t)));
        ul.appendChild(li);
      });
      $('dash-must-change').hidden = !j.mustChange;
      if (j.mustChange && !loadAccount.nudged) { loadAccount.nudged = true; var a = $('dash-account'); if (a) a.scrollIntoView({ behavior: 'smooth' }); }
    } catch (e) { /* shown elsewhere */ }
  }

  async function changePassword(ev) {
    ev.preventDefault();
    var err = $('pw-error'); err.textContent = '';
    var cur = $('pw-current').value, next = $('pw-next').value;
    if (!cur || !next) { err.textContent = 'Enter your current and new password.'; return; }
    try {
      var j = await api('POST', '/api/account', { action: 'password', current: cur, next: next });
      if (window.csSetCsrf) csSetCsrf(j.csrf); else if (window.CS) CS.csrf = j.csrf;
      $('pw-current').value = ''; $('pw-next').value = '';
      $('dash-must-change').hidden = true;
      say('Password changed. Your other devices were signed out.');
      loadAccount();
    } catch (e) { err.textContent = e.message; }
  }

  async function signOutEverywhere() {
    try { await api('POST', '/api/account', { action: 'signout-all' }); } catch (e) { say(e.message, true); return; }
    if (window.csSessionLost) csSessionLost(); else location.href = '/signin';
    if (window.showToast) showToast('Signed out on all devices');
  }

  async function erase() {
    try { await api('DELETE', '/api/assessments?all=1'); items = []; render(); say('All assessments erased.'); } catch (e) { say(e.message, true); }
  }

  // ------------------------------------------------------------ admin
  async function loadAdmin() {
    var panel = $('dash-admin');
    var u = state().user;
    panel.hidden = !(u && u.role === 'admin');
    if (panel.hidden) return;
    try {
      var j = await api('GET', '/api/admin');
      var body = $('admin-rows'); clear(body);
      j.users.forEach(function (p) {
        var tr = el('tr');
        tr.appendChild(el('td', '', p.email + (p.name ? ' (' + p.name + ')' : '')));
        tr.appendChild(el('td', '', p.role));
        var st = el('td'); st.appendChild(el('span', 'hx-chip ' + (p.disabled ? 'high' : 'low'), p.disabled ? 'Disabled' : 'Active')); tr.appendChild(st);
        var act = el('td', 'hx-actions-cell');
        if (p.email !== state().user.email) {
          var tog = el('button', 'hx-linkbtn', p.disabled ? 'Enable' : 'Disable'); tog.type = 'button';
          tog.addEventListener('click', async function () { try { await api('POST', '/api/admin', { action: p.disabled ? 'enable' : 'disable', email: p.email }); loadAdmin(); } catch (e) { say(e.message, true); } });
          var rs = el('button', 'hx-linkbtn', 'Reset password'); rs.type = 'button';
          rs.addEventListener('click', async function () { try { var r = await api('POST', '/api/admin', { action: 'reset', email: p.email }); secret(p.email, r.temporaryPassword); } catch (e) { say(e.message, true); } });
          act.appendChild(tog); act.appendChild(rs);
        }
        tr.appendChild(act); body.appendChild(tr);
      });
      var ev = $('admin-events'); clear(ev);
      j.events.slice(0, 15).forEach(function (r) {
        var li = el('li');
        li.appendChild(el('span', '', (r.u || '') + ': ' + (EVENTS[r.ev] || r.ev) + (r.x ? ' (' + r.x + ')' : '')));
        li.appendChild(el('time', '', when(r.t)));
        ev.appendChild(li);
      });
      var sl = $('sub-line');
      if (sl) {
        var sj = await api('GET', '/api/subscribe'); sl.textContent = sj.count + (sj.count === 1 ? ' address' : ' addresses') + ', none confirmed. Anyone can type any address, so do not email this list until a confirmation step exists.';
        var se = $('sub-export'); se.hidden = !sj.count;
        se.onclick = function () {
          var blob = new Blob(['email,subscribed,confirmed\n' + sj.items.map(function (i) { return i.email + ',' + new Date(i.t).toISOString() + ',' + (i.confirmed ? 'yes' : 'no'); }).join('\n') + '\n'], { type: 'text/csv' });
          var a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'subscribers.csv'; document.body.appendChild(a); a.click(); a.remove();
        };
      }
      var bl = $('bug-rows');
      if (bl) {
        var bj = await api('GET', '/api/bug'); clear(bl);
        if (!bj.items.length) bl.appendChild(el('li', 'hx-empty', 'No bug reports.'));
        bj.items.slice(0, 20).forEach(function (r) {
          var li = el('li'); var b = el('b', '', (r.area || 'General') + (r.page ? ' on ' + r.page : '') + (r.email ? ' (' + r.email + ')' : ''));
          li.appendChild(b); li.appendChild(el('span', '', r.what)); li.appendChild(el('time', '', when(r.t))); bl.appendChild(li);
        });
      }
    } catch (e) { /* ignore */ }
  }

  function secret(email, pw) {
    var box = $('nu-secret'); clear(box); box.hidden = false;
    box.appendChild(el('span', '', 'Temporary password for ' + email + ': '));
    box.appendChild(el('code', '', pw));
    var cp = el('button', 'hx-linkbtn', 'Copy'); cp.type = 'button';
    cp.addEventListener('click', function () { if (navigator.clipboard) navigator.clipboard.writeText(pw).then(function () { cp.textContent = 'Copied'; }); });
    box.appendChild(cp);
    box.appendChild(el('span', 'hx-hint', ' It is shown once.'));
  }

  async function createUser(ev) {
    ev.preventDefault();
    var err = $('nu-error'); err.textContent = '';
    try {
      var j = await api('POST', '/api/admin', { action: 'create', email: $('nu-email').value, name: $('nu-name').value, role: $('nu-role').value });
      secret(j.user.email, j.temporaryPassword);
      $('nu-email').value = ''; $('nu-name').value = '';
      loadAdmin();
    } catch (e) { err.textContent = e.message; }
  }

  // ------------------------------------------------------------ session hooks
  async function refresh() {
    var u = state().user, sec = $('dashboard'), av = $('dock-avatar');
    if (!u && !sec) return;
    if (av) av.textContent = u ? (u.name || u.email).trim().slice(0, 1).toUpperCase() : 'In';
    if (!sec) { if (u) { try { items = (await api('GET', '/api/assessments')).items || []; } catch (e) { items = []; } } return; }
    if (!u) { items = []; if ($('dash-hero')) return; sec.hidden = true; return; }
    try {
      var j = await api('GET', '/api/assessments');
      items = j.items || [];
    } catch (e) { items = []; say(e.message, true); }
    render(); loadAccount(); loadAdmin();
  }

  function open() {
    if (!state().user) { if (window.openAuthModal) openAuthModal(); return; }
    var s = $('dash-hero');
    if (s) s.scrollIntoView({ behavior: 'smooth', block: 'start' }); else location.href = '/dashboard';
  }

  function init() {
    var on = function (id, ev, fn) { var n = $(id); if (n) n.addEventListener(ev, fn); };
    on('dash-save', 'click', saveCurrent);
    on('dash-export', 'click', exportCsv);
    on('dash-more', 'click', function () { shown += 15; renderTable(); });
    on('dash-erase', 'click', function (e) { armed(e.currentTarget, 'Click again to erase everything', erase); });
    on('pw-form', 'submit', changePassword);
    on('signout-all', 'click', signOutEverywhere);
    on('user-form', 'submit', createUser);
    if ($('dash-hero') && window.CS && CS.ready) {
      CS.ready.then(function () {
        if (!CS.user) { location.replace('/signin?next=/dashboard'); return; }
        refresh().then(function () { $('dashboard').hidden = false; if (location.hash) { var t = document.getElementById(location.hash.slice(1)); if (t) t.scrollIntoView(); } });
      });
    }
    var q = new URLSearchParams(location.search);
    if (q.get('signin') === '1' && !state().user && window.openAuthModal) setTimeout(openAuthModal, 400);
  }

  window.CSDash = { refresh: refresh, open: open, saveCurrent: saveCurrent };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
