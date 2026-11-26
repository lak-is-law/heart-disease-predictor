/* CardioSense Discord-style onboarding wizard: multi-step profile, role, focus areas, referral source & guidelines. */
(function () {
  'use strict';
  if (typeof document === 'undefined') return;

  var ROLES = [
    ['Clinician / Physician', 'Practicing doctor or clinical specialist'],
    ['Medical Student / Resident', 'Medical training, internship or residency'],
    ['Researcher / Academic', 'Clinical, epidemiology or academic study'],
    ['Data Scientist / Engineer', 'ML evaluation, calibration or software'],
    ['Educator / Instructor', 'Teaching cardiology, stats or decision tools'],
    ['Personal / Curious Learner', 'Exploring cardiac risk estimation'],
    ['Other', 'Another background or interest']
  ];
  var EXP = ['Exploring', 'Student / Trainee', 'Practicing', 'Research / Academic'];
  var GOALS = [
    'Coronary risk estimation',
    'Interactive 3D heart & ECG',
    'Lab report import',
    'Selective-escalation research',
    'Teaching & case studies',
    'Desktop offline app'
  ];
  var REFS = [
    'Search engine',
    'GitHub / Open source',
    'Colleague or friend',
    'University or class',
    'Social media',
    'Research paper',
    'AI assistant',
    'Other'
  ];

  var backdrop = null;
  var isOpen = false;
  var step = 0;
  var state = {};

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function clear(n) { while (n && n.firstChild) n.removeChild(n.firstChild); }

  function getAuth() {
    if (window.csState) return window.csState();
    if (window.CS) return { user: window.CS.user, csrf: window.CS.csrf };
    return { user: null, csrf: '' };
  }

  function initials(name, email) {
    var s = (name || email || '?').trim().split(/\s+/);
    if (s.length > 1) return (s[0].charAt(0) + s[s.length - 1].charAt(0)).toUpperCase();
    return (s[0] || '?').charAt(0).toUpperCase();
  }

  function injectStyles() {
    if (document.getElementById('cs-ob-style')) return;
    var st = document.createElement('style');
    st.id = 'cs-ob-style';
    st.textContent = [
      '.cs-ob-back{position:fixed;inset:0;z-index:3500;display:flex;align-items:center;justify-content:center;padding:12px;background:rgba(4,10,18,.74);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);font-family:var(--font,var(--hx-font,system-ui,sans-serif));}',
      '.cs-ob-back[hidden]{display:none;}',
      '.cs-ob-card{width:min(580px,100%);max-height:min(92vh,760px);display:flex;flex-direction:column;border-radius:18px;background:var(--bg,var(--hx-bg-2,#0E1726));color:var(--fg,var(--hx-text,#F5F7FA));border:1px solid var(--line-strong,var(--hx-line,rgba(255,255,255,.14)));box-shadow:0 24px 64px rgba(0,0,0,.45);overflow:hidden;}',
      '.cs-ob-head{padding:18px 22px 14px;border-bottom:1px solid var(--line,var(--hx-line,rgba(255,255,255,.1)));background:var(--bg-soft,rgba(255,255,255,.02));}',
      '.cs-ob-top{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:12px;}',
      '.cs-ob-brand{display:flex;align-items:center;gap:10px;font-weight:600;font-size:.95rem;min-width:0;}',
      '.cs-ob-brand span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}',
      '.cs-ob-brand img{width:26px;height:26px;border-radius:7px;flex:none;}',
      '.cs-ob-step-lbl{font-size:.8rem;font-weight:600;color:var(--accent,var(--hx-cyan,#00F0FF));letter-spacing:.02em;white-space:nowrap;flex-shrink:0;}',
      '.cs-ob-close{width:34px;height:34px;flex-shrink:0;border-radius:50%;border:1px solid var(--line-strong,var(--hx-line,rgba(255,255,255,.16)));background:transparent;color:var(--dim,var(--hx-dim,#9AA6B8));font-size:1.25rem;line-height:1;cursor:pointer;display:grid;place-items:center;}',
      '.cs-ob-close:hover{color:var(--fg,var(--hx-text,#F5F7FA));}',
      '.cs-ob-bars{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;}',
      '.cs-ob-bars i{display:block;height:4px;border-radius:99px;background:var(--line,rgba(255,255,255,.12));transition:background .2s;}',
      '.cs-ob-bars i.on{background:var(--accent,var(--hx-cyan,#00F0FF));}',
      '.cs-ob-body{flex:1;overflow-y:auto;padding:22px;-webkit-overflow-scrolling:touch;}',
      '.cs-ob-h{margin:0 0 6px;font-size:1.35rem;font-weight:600;letter-spacing:-.025em;line-height:1.2;}',
      '.cs-ob-sub{margin:0 0 18px;color:var(--dim,var(--hx-dim,#9AA6B8));font-size:.94rem;line-height:1.5;}',
      '.cs-ob-preview{display:flex;align-items:center;gap:14px;padding:14px 16px;border-radius:14px;border:1px solid var(--line,var(--hx-line,rgba(255,255,255,.12)));background:var(--bg-soft,rgba(255,255,255,.03));margin-bottom:16px;}',
      '.cs-ob-av{width:52px;height:52px;border-radius:50%;flex:none;display:grid;place-items:center;background:var(--accent-soft,rgba(0,240,255,.14));color:var(--accent,var(--hx-cyan,#00F0FF));border:2px solid var(--accent,var(--hx-cyan,#00F0FF));font-size:1.2rem;font-weight:700;}',
      '.cs-ob-pv-txt{min-width:0;flex:1;}',
      '.cs-ob-pv-name{font-weight:600;font-size:1.02rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}',
      '.cs-ob-pv-meta{font-size:.84rem;color:var(--dim,var(--hx-dim,#9AA6B8));overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:2px;}',
      '.cs-ob-field{margin-bottom:14px;}',
      '.cs-ob-field label{display:block;font-size:.86rem;font-weight:500;margin:0 0 6px;color:var(--fg,var(--hx-text,#F5F7FA));}',
      '.cs-ob-field input,.cs-ob-field select{width:100%;box-sizing:border-box;min-height:44px;padding:10px 13px;border-radius:10px;border:1px solid var(--line-strong,var(--hx-line,rgba(255,255,255,.18)));background:var(--bg,var(--hx-bg,#07090E));color:var(--fg,var(--hx-text,#F5F7FA));font:inherit;font-size:.96rem;}',
      '.cs-ob-field input:focus{outline:2px solid var(--accent,var(--hx-cyan,#00F0FF));outline-offset:1px;border-color:transparent;}',
      '.cs-ob-two{display:grid;grid-template-columns:1fr 1fr;gap:12px;}',
      '.cs-ob-roles{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;}',
      '.cs-ob-opt{text-align:left;padding:12px 14px;border-radius:12px;border:1px solid var(--line-strong,var(--hx-line,rgba(255,255,255,.14)));background:var(--bg,var(--hx-bg,#07090E));color:var(--fg,var(--hx-text,#F5F7FA));cursor:pointer;display:flex;flex-direction:column;gap:3px;min-height:44px;transition:border-color .15s,background .15s;}',
      '.cs-ob-opt b{font-size:.92rem;font-weight:600;}',
      '.cs-ob-opt span{font-size:.78rem;color:var(--dim,var(--hx-dim,#9AA6B8));line-height:1.35;}',
      '.cs-ob-opt.on{border-color:var(--accent,var(--hx-cyan,#00F0FF));background:var(--accent-soft,rgba(0,240,255,.12));}',
      '.cs-ob-chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;}',
      '.cs-ob-chip{padding:9px 14px;min-height:40px;border-radius:999px;border:1px solid var(--line-strong,var(--hx-line,rgba(255,255,255,.16)));background:var(--bg,var(--hx-bg,#07090E));color:var(--fg,var(--hx-text,#F5F7FA));font:inherit;font-size:.86rem;font-weight:500;cursor:pointer;transition:border-color .15s,background .15s;}',
      '.cs-ob-chip.on{border-color:var(--accent,var(--hx-cyan,#00F0FF));background:var(--accent-soft,rgba(0,240,255,.14));color:var(--accent,var(--hx-cyan,#00F0FF));font-weight:600;}',
      '.cs-ob-sec-lbl{font-size:.86rem;font-weight:600;margin:0 0 8px;display:block;}',
      '.cs-ob-rules{list-style:none;margin:0 0 16px;padding:0;display:grid;gap:10px;}',
      '.cs-ob-rules li{padding:12px 14px;border-radius:12px;border:1px solid var(--line,var(--hx-line,rgba(255,255,255,.12)));background:var(--bg-soft,rgba(255,255,255,.03));font-size:.9rem;line-height:1.5;}',
      '.cs-ob-rules b{display:block;margin-bottom:2px;font-weight:600;}',
      '.cs-ob-rules span{color:var(--dim,var(--hx-dim,#9AA6B8));font-size:.85rem;}',
      '.cs-ob-agree{display:flex;align-items:flex-start;gap:10px;padding:12px 14px;border-radius:12px;border:1px solid var(--line-strong,var(--hx-line,rgba(255,255,255,.18)));cursor:pointer;font-size:.92rem;line-height:1.4;}',
      '.cs-ob-agree input{width:20px;height:20px;margin:2px 0 0;flex:none;accent-color:var(--accent,var(--hx-cyan,#00F0FF));}',
      '.cs-ob-err{min-height:1.25em;margin:10px 0 0;color:var(--bad,#F87171);font-size:.88rem;}',
      '.cs-ob-foot{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:14px 22px;border-top:1px solid var(--line,var(--hx-line,rgba(255,255,255,.1)));background:var(--bg-soft,rgba(255,255,255,.02));flex-wrap:wrap;}',
      '.cs-ob-foot-r{display:flex;align-items:center;gap:8px;margin-left:auto;}',
      '.cs-ob-btn{min-height:42px;padding:0 18px;border-radius:999px;font:inherit;font-size:.92rem;font-weight:600;cursor:pointer;border:1px solid transparent;display:inline-flex;align-items:center;justify-content:center;white-space:nowrap;}',
      '.cs-ob-btn.pri{background:var(--btn,var(--hx-cyan,#00F0FF));color:var(--btn-fg,#04121A);}',
      '.cs-ob-btn.line{background:transparent;color:var(--fg,var(--hx-text,#F5F7FA));border-color:var(--line-strong,var(--hx-line,rgba(255,255,255,.2)));}',
      '.cs-ob-btn.ghost{background:transparent;color:var(--dim,var(--hx-dim,#9AA6B8));padding:0 10px;}',
      '.cs-ob-btn[disabled]{opacity:.5;cursor:not-allowed;}',
      '@media(max-width:560px){.cs-ob-two,.cs-ob-roles{grid-template-columns:1fr;}.cs-ob-head,.cs-ob-body,.cs-ob-foot{padding-left:16px;padding-right:16px;}.cs-ob-brand{gap:8px;font-size:.84rem;}.cs-ob-brand img{width:22px;height:22px;}.cs-ob-foot{gap:8px;}.cs-ob-foot-r{width:auto;justify-content:flex-end;}}'
    ].join('');
    document.head.appendChild(st);
  }

  function buildModal() {
    if (backdrop) return;
    injectStyles();
    backdrop = el('div', 'cs-ob-back');
    backdrop.hidden = true;
    backdrop.setAttribute('role', 'dialog');
    backdrop.setAttribute('aria-modal', 'true');
    backdrop.setAttribute('aria-labelledby', 'cs-ob-title');

    var card = el('div', 'cs-ob-card');
    var head = el('div', 'cs-ob-head');
    var top = el('div', 'cs-ob-top');
    var brand = el('div', 'cs-ob-brand');
    var img = el('img'); img.src = '/favicon.svg'; img.alt = ''; img.width = 26; img.height = 26;
    brand.append(img, el('span', '', 'Welcome to CardioSense'));
    var right = el('div', ''); right.style.cssText = 'display:flex;align-items:center;gap:10px;';
    var stepLbl = el('span', 'cs-ob-step-lbl'); stepLbl.id = 'cs-ob-step-lbl';
    var closeBtn = el('button', 'cs-ob-close', '\u00d7'); closeBtn.type = 'button';
    closeBtn.setAttribute('aria-label', 'Skip onboarding for now');
    closeBtn.addEventListener('click', function () { skip(); });
    right.append(stepLbl, closeBtn);
    top.append(brand, right);

    var bars = el('div', 'cs-ob-bars'); bars.id = 'cs-ob-bars';
    for (var i = 0; i < 4; i++) bars.appendChild(el('i'));
    head.append(top, bars);

    var body = el('div', 'cs-ob-body'); body.id = 'cs-ob-body';
    var foot = el('div', 'cs-ob-foot'); foot.id = 'cs-ob-foot';

    card.append(head, body, foot);
    backdrop.appendChild(card);
    document.body.appendChild(backdrop);

    document.addEventListener('keydown', function (e) {
      if (isOpen && e.key === 'Escape') skip();
    });
  }

  function syncHeaderAndViews(user) {
    if (window.CS && window.CS.setUser) window.CS.setUser(user);
    document.dispatchEvent(new CustomEvent('cs:user-updated', { detail: { user: user } }));
    if (window.CSDash && window.CSDash.refresh) window.CSDash.refresh();
  }

  async function postAccount(payload) {
    var a = getAuth();
    var r = await fetch('/api/account', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': a.csrf || '' },
      body: JSON.stringify(payload)
    });
    var j = await r.json().catch(function () { return {}; });
    if (!r.ok) throw new Error(j.error || 'Could not save. Try again.');
    return j;
  }

  async function skip() {
    close();
    try {
      var j = await postAccount({ action: 'onboarding', skip: true });
      if (j.user) syncHeaderAndViews(j.user);
    } catch (e) { /* ignore */ }
  }

  async function finish(errEl, btn) {
    if (!state.acceptedGuidelines) {
      errEl.textContent = 'Tick the box to confirm the research-prototype guidelines.';
      return;
    }
    btn.disabled = true; errEl.textContent = '';
    try {
      var j = await postAccount({
        action: 'onboarding',
        name: state.name,
        headline: state.headline,
        roleType: state.roleType,
        organization: state.organization,
        country: state.country,
        experience: state.experience,
        useCase: state.useCase,
        referralSource: state.referralSource,
        referralDetail: state.referralDetail,
        acceptedGuidelines: state.acceptedGuidelines
      });
      close();
      if (j.user) syncHeaderAndViews(j.user);
      if (window.showToast) window.showToast('Profile set up');
      if (window.CSTutorial && !(j.user && j.user.tourSeen)) {
        setTimeout(function () { window.CSTutorial.start(); }, 350);
      }
    } catch (e) {
      errEl.textContent = e.message;
      btn.disabled = false;
    }
  }

  function render() {
    var body = document.getElementById('cs-ob-body');
    var foot = document.getElementById('cs-ob-foot');
    var lbl = document.getElementById('cs-ob-step-lbl');
    var bars = document.getElementById('cs-ob-bars');
    if (!body || !foot) return;

    clear(body); clear(foot);
    lbl.textContent = 'Step ' + (step + 1) + ' of 4';
    var bs = bars.querySelectorAll('i');
    for (var i = 0; i < bs.length; i++) bs[i].classList.toggle('on', i <= step);

    var err = el('p', 'cs-ob-err'); err.setAttribute('role', 'alert');

    if (step === 0) {
      var h = el('h2', 'cs-ob-h', 'Set up your profile');
      h.id = 'cs-ob-title';
      body.append(h, el('p', 'cs-ob-sub', 'Choose the name shown on your dashboard and reviews, and share a few details about yourself.'));

      var pv = el('div', 'cs-ob-preview');
      var av = el('div', 'cs-ob-av', initials(state.name, state.email));
      var pvt = el('div', 'cs-ob-pv-txt');
      var pvn = el('div', 'cs-ob-pv-name', state.name || 'Your name');
      var pvm = el('div', 'cs-ob-pv-meta', [state.headline, state.organization, state.country].filter(Boolean).join(' \u00b7 ') || state.email);
      pvt.append(pvn, pvm); pv.append(av, pvt); body.appendChild(pv);

      function updatePreview() {
        av.textContent = initials(state.name, state.email);
        pvn.textContent = state.name.trim() || 'Your name';
        pvm.textContent = [state.headline.trim(), state.organization.trim(), state.country.trim()].filter(Boolean).join(' \u00b7 ') || state.email;
      }

      var f1 = el('div', 'cs-ob-field');
      var l1 = el('label', '', 'Display name'); l1.htmlFor = 'ob-name';
      var i1 = el('input'); i1.id = 'ob-name'; i1.type = 'text'; i1.maxLength = 80; i1.placeholder = 'e.g. Dr. Asha Verma'; i1.value = state.name;
      i1.addEventListener('input', function () { state.name = i1.value; updatePreview(); });
      f1.append(l1, i1); body.appendChild(f1);

      var f2 = el('div', 'cs-ob-field');
      var l2 = el('label', '', 'Role / title (optional)'); l2.htmlFor = 'ob-head';
      var i2 = el('input'); i2.id = 'ob-head'; i2.type = 'text'; i2.maxLength = 100; i2.placeholder = 'e.g. Cardiology Fellow, Med Student, ML Researcher'; i2.value = state.headline;
      i2.addEventListener('input', function () { state.headline = i2.value; updatePreview(); });
      f2.append(l2, i2); body.appendChild(f2);

      var two = el('div', 'cs-ob-two');
      var f3 = el('div', 'cs-ob-field');
      var l3 = el('label', '', 'Organization / school (optional)'); l3.htmlFor = 'ob-org';
      var i3 = el('input'); i3.id = 'ob-org'; i3.type = 'text'; i3.maxLength = 100; i3.placeholder = 'Hospital, university or lab'; i3.value = state.organization;
      i3.addEventListener('input', function () { state.organization = i3.value; updatePreview(); });
      f3.append(l3, i3);

      var f4 = el('div', 'cs-ob-field');
      var l4 = el('label', '', 'Country / region (optional)'); l4.htmlFor = 'ob-country';
      var i4 = el('input'); i4.id = 'ob-country'; i4.type = 'text'; i4.maxLength = 60; i4.placeholder = 'e.g. India, United States'; i4.value = state.country;
      i4.addEventListener('input', function () { state.country = i4.value; updatePreview(); });
      f4.append(l4, i4);
      two.append(f3, f4); body.appendChild(two);
    } else if (step === 1) {
      var h2 = el('h2', 'cs-ob-h', 'What best describes you?');
      h2.id = 'cs-ob-title';
      body.append(h2, el('p', 'cs-ob-sub', 'Pick your primary role so we can tailor your workspace experience.'));

      var grid = el('div', 'cs-ob-roles');
      ROLES.forEach(function (r) {
        var b = el('button', 'cs-ob-opt' + (state.roleType === r[0] ? ' on' : ''));
        b.type = 'button';
        b.append(el('b', '', r[0]), el('span', '', r[1]));
        b.addEventListener('click', function () { state.roleType = r[0]; render(); });
        grid.appendChild(b);
      });
      body.appendChild(grid);

      body.appendChild(el('span', 'cs-ob-sec-lbl', 'Experience level (optional)'));
      var chips = el('div', 'cs-ob-chips');
      EXP.forEach(function (x) {
        var b = el('button', 'cs-ob-chip' + (state.experience === x ? ' on' : ''), x);
        b.type = 'button';
        b.addEventListener('click', function () { state.experience = state.experience === x ? '' : x; render(); });
        chips.appendChild(b);
      });
      body.appendChild(chips);
    } else if (step === 2) {
      var h3 = el('h2', 'cs-ob-h', 'Your goals & how you found us');
      h3.id = 'cs-ob-title';
      body.append(h3, el('p', 'cs-ob-sub', 'Choose what you plan to explore and let us know where you heard about CardioSense.'));

      body.appendChild(el('span', 'cs-ob-sec-lbl', 'What brings you to CardioSense? (pick any)'));
      var gbox = el('div', 'cs-ob-chips');
      GOALS.forEach(function (g) {
        var on = state.useCase.indexOf(g) >= 0;
        var b = el('button', 'cs-ob-chip' + (on ? ' on' : ''), g);
        b.type = 'button';
        b.addEventListener('click', function () {
          var idx = state.useCase.indexOf(g);
          if (idx >= 0) state.useCase.splice(idx, 1); else state.useCase.push(g);
          render();
        });
        gbox.appendChild(b);
      });
      body.appendChild(gbox);

      body.appendChild(el('span', 'cs-ob-sec-lbl', 'How did you hear about us?'));
      var rbox = el('div', 'cs-ob-chips');
      REFS.forEach(function (r) {
        var b = el('button', 'cs-ob-chip' + (state.referralSource === r ? ' on' : ''), r);
        b.type = 'button';
        b.addEventListener('click', function () { state.referralSource = r; render(); });
        rbox.appendChild(b);
      });
      body.appendChild(rbox);

      var fd = el('div', 'cs-ob-field');
      var ld = el('label', '', 'Care to share a bit more? (optional)'); ld.htmlFor = 'ob-ref-det';
      var idt = el('input'); idt.id = 'ob-ref-det'; idt.type = 'text'; idt.maxLength = 120;
      idt.placeholder = 'e.g. a friend, search topic, university course, post'; idt.value = state.referralDetail;
      idt.addEventListener('input', function () { state.referralDetail = idt.value; });
      fd.append(ld, idt); body.appendChild(fd);
    } else {
      var h4 = el('h2', 'cs-ob-h', 'One last check before you start');
      h4.id = 'cs-ob-title';
      body.append(h4, el('p', 'cs-ob-sub', 'CardioSense is built for learning and research. Review these ground rules first:'));

      var ul = el('ul', 'cs-ob-rules');
      [
        ['1. Research prototype, not a medical device', 'Estimates come from 303 patients at one 1980s clinic. Do not use CardioSense to diagnose, rule out disease, or decide treatment.'],
        ['2. Synthetic or de-identified data only', 'Never enter real patient names, hospital IDs, or protected health records into references or fields.'],
        ['3. Your profile and records stay in your control', 'Saved assessments are encrypted on the server, and you can edit your profile or erase your records anytime from your dashboard.']
      ].forEach(function (item) {
        var li = el('li'); li.append(el('b', '', item[0]), el('span', '', item[1])); ul.appendChild(li);
      });
      body.appendChild(ul);

      var ag = el('label', 'cs-ob-agree');
      var cb = el('input'); cb.type = 'checkbox'; cb.checked = Boolean(state.acceptedGuidelines);
      cb.addEventListener('change', function () { state.acceptedGuidelines = cb.checked; });
      ag.append(cb, el('span', '', 'I understand that CardioSense is a research prototype and will use synthetic or de-identified data only.'));
      body.appendChild(ag);
    }

    body.appendChild(err);

    var skipBtn = el('button', 'cs-ob-btn ghost', 'Skip for now'); skipBtn.type = 'button';
    skipBtn.addEventListener('click', skip);
    foot.appendChild(skipBtn);

    var right = el('div', 'cs-ob-foot-r');
    if (step > 0) {
      var back = el('button', 'cs-ob-btn line', 'Back'); back.type = 'button';
      back.addEventListener('click', function () { step--; render(); });
      right.appendChild(back);
    }
    if (step < 3) {
      var next = el('button', 'cs-ob-btn pri', 'Continue'); next.type = 'button';
      next.addEventListener('click', function () {
        if (step === 0 && state.name.trim().length < 2) { err.textContent = 'Enter a display name (at least 2 characters).'; return; }
        if (step === 1 && !state.roleType) { err.textContent = 'Select the option that best describes you.'; return; }
        if (step === 2 && !state.referralSource) { err.textContent = 'Select how you heard about CardioSense.'; return; }
        step++; render();
      });
      right.appendChild(next);
    } else {
      var done = el('button', 'cs-ob-btn pri', 'Finish setup'); done.type = 'button';
      done.addEventListener('click', function () { finish(err, done); });
      right.appendChild(done);
    }
    foot.appendChild(right);
  }

  async function open(opts) {
    var a = getAuth();
    if (!a.user || isOpen) return;
    buildModal();
    isOpen = true;
    step = 0;
    state = {
      email: a.user.email || '',
      name: a.user.name || '',
      headline: '',
      roleType: '',
      organization: '',
      country: '',
      experience: '',
      useCase: [],
      referralSource: '',
      referralDetail: '',
      acceptedGuidelines: false
    };
    if (opts && opts.prefill) {
      Object.assign(state, opts.prefill);
      state.useCase = Array.isArray(opts.prefill.useCase) ? opts.prefill.useCase.slice() : [];
    } else {
      try {
        var r = await fetch('/api/account', { credentials: 'same-origin' });
        if (r.ok) {
          var j = await r.json();
          if (j.profile) {
            state.name = j.profile.name || state.name;
            state.headline = j.profile.headline || '';
            state.roleType = j.profile.roleType || '';
            state.organization = j.profile.organization || '';
            state.country = j.profile.country || '';
            state.experience = j.profile.experience || '';
            state.useCase = Array.isArray(j.profile.useCase) ? j.profile.useCase.slice() : [];
            state.referralSource = j.profile.referralSource || '';
            state.referralDetail = j.profile.referralDetail || '';
            state.acceptedGuidelines = Boolean(j.profile.acceptedGuidelines);
          }
        }
      } catch (e) { /* ignore */ }
    }
    render();
    backdrop.hidden = false;
    var first = backdrop.querySelector('input, button.cs-ob-opt');
    if (first) setTimeout(function () { first.focus(); }, 30);
  }

  function close() {
    isOpen = false;
    if (backdrop) backdrop.hidden = true;
  }

  function maybeAutoOpen() {
    var p = location.pathname;
    if (p === '/signin' || p === '/signup' || p === '/signin.html' || p === '/signup.html') return;
    var a = getAuth();
    if (a.user && !a.user.onboarded && !a.user.onboardingSkipped) {
      setTimeout(function () {
        var cur = getAuth();
        if (cur.user && !cur.user.onboarded && !cur.user.onboardingSkipped) open();
      }, 350);
    }
  }

  window.CSOnboard = { open: open, close: close };
  document.addEventListener('cs:session', maybeAutoOpen);
  if (document.readyState === 'complete') maybeAutoOpen();
  else window.addEventListener('load', maybeAutoOpen);
})();
