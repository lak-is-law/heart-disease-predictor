/* CardioSense arrow-overlay guided tutorial for Dashboard (/dashboard) and Workstation (/app). */
(function () {
  'use strict';
  if (typeof document === 'undefined') return;

  var root = null, spot = null, arrow = null, pop = null;
  var active = false;
  var steps = [];
  var idx = 0;
  var repositionTimer = null;

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

  function injectStyles() {
    if (document.getElementById('cs-tut-style')) return;
    var st = document.createElement('style');
    st.id = 'cs-tut-style';
    st.textContent = [
      '.cs-tut-root{position:fixed;inset:0;z-index:3600;pointer-events:auto;font-family:var(--font,var(--hx-font,system-ui,sans-serif));}',
      '.cs-tut-root[hidden]{display:none;}',
      '.cs-tut-spot{position:fixed;z-index:3601;pointer-events:none;border-radius:14px;border:2px solid var(--accent,var(--hx-cyan,#00F0FF));box-shadow:0 0 0 9999px rgba(4,10,18,.74),0 0 24px rgba(0,229,255,.32);transition:top .24s ease,left .24s ease,width .24s ease,height .24s ease;}',
      '.cs-tut-arrow{position:fixed;z-index:3603;pointer-events:none;width:44px;height:44px;color:var(--accent,var(--hx-cyan,#00F0FF));filter:drop-shadow(0 2px 8px rgba(0,0,0,.55));}',
      '.cs-tut-arrow.up{animation:cs-tut-up 1.1s ease-in-out infinite;}',
      '.cs-tut-arrow.down{animation:cs-tut-dn 1.1s ease-in-out infinite;}',
      '@keyframes cs-tut-up{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}',
      '@keyframes cs-tut-dn{0%,100%{transform:translateY(0)}50%{transform:translateY(6px)}}',
      '@media(prefers-reduced-motion:reduce){.cs-tut-arrow{animation:none !important;}.cs-tut-spot{transition:none;}}',
      '.cs-tut-pop{position:fixed;z-index:3602;width:min(360px,calc(100vw - 24px));padding:18px 18px 16px;border-radius:16px;background:var(--bg,var(--hx-bg-2,#0E1726));color:var(--fg,var(--hx-text,#F5F7FA));border:1px solid var(--line-strong,var(--hx-line,rgba(255,255,255,.18)));box-shadow:0 20px 52px rgba(0,0,0,.5);}',
      '.cs-tut-top{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px;}',
      '.cs-tut-badge{font-size:.78rem;font-weight:700;color:var(--accent,var(--hx-cyan,#00F0FF));letter-spacing:.02em;text-transform:uppercase;}',
      '.cs-tut-skip{background:none;border:0;color:var(--dim,var(--hx-dim,#9AA6B8));font:inherit;font-size:.82rem;cursor:pointer;padding:2px 4px;}',
      '.cs-tut-skip:hover{color:var(--fg,var(--hx-text,#F5F7FA));}',
      '.cs-tut-h{margin:0 0 6px;font-size:1.08rem;font-weight:600;line-height:1.25;}',
      '.cs-tut-p{margin:0 0 14px;color:var(--dim,var(--hx-dim,#9AA6B8));font-size:.92rem;line-height:1.5;}',
      '.cs-tut-foot{display:flex;align-items:center;justify-content:space-between;gap:8px;}',
      '.cs-tut-dots{display:flex;gap:5px;align-items:center;}',
      '.cs-tut-dots i{width:7px;height:7px;border-radius:50%;background:var(--line-strong,rgba(255,255,255,.2));display:block;}',
      '.cs-tut-dots i.on{background:var(--accent,var(--hx-cyan,#00F0FF));width:16px;border-radius:99px;}',
      '.cs-tut-btns{display:flex;gap:8px;}',
      '.cs-tut-btn{min-height:38px;padding:0 16px;border-radius:999px;font:inherit;font-size:.88rem;font-weight:600;cursor:pointer;border:1px solid transparent;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;}',
      '.cs-tut-btn.pri{background:var(--btn,var(--hx-cyan,#00F0FF));color:var(--btn-fg,#04121A);}',
      '.cs-tut-btn.line{background:transparent;color:var(--fg,var(--hx-text,#F5F7FA));border-color:var(--line-strong,var(--hx-line,rgba(255,255,255,.2)));}'
    ].join('');
    document.head.appendChild(st);
  }

  function pageSteps() {
    if (document.getElementById('live-workstation')) {
      return [
        {
          sel: '.quick-scenario-strip',
          title: '1. Load a sample or lab report',
          body: 'Tap any synthetic scenario chip here, or scroll down to EHR & Lab Ingestion to drop in a CSV, JSON, HL7 or text report.'
        },
        {
          sel: '.safety-net-toggle-wrapper',
          title: '2. Adjust inputs & threshold',
          body: 'Edit the 13 clinical values below. Toggle High-sensitivity mode (0.28) to flag more borderline cases for review.'
        },
        {
          sel: '#portal-cgi-viewport',
          title: '3. Inspect the 3D heart & ECG',
          body: 'The 3D heart, ECG rhythm strip and risk gauge respond live as you adjust values. Drag or zoom the heart to inspect chambers.'
        },
        {
          sel: '.header-save-btn',
          title: '4. Save or export your case',
          body: 'Click Save to open the clinical summary report, print a PDF, or save the encrypted assessment straight to your Dashboard.'
        }
      ];
    }
    if (document.getElementById('dash-hero')) {
      return [
        {
          sel: '.dash-hero .hx-actions a[href="/app"]',
          title: '1. Start a new assessment',
          body: 'Open the Workstation to enter the 13 clinical inputs or import a sample lab report and see the live 3D heart and ECG.'
        },
        {
          sel: '#dash-stats',
          title: '2. Track your risk report',
          body: 'Your saved assessment count, average risk, trend chart and risk-band breakdown update automatically as you save cases.'
        },
        {
          sel: '#dash-export',
          title: '3. Re-open or export saved cases',
          body: 'Reload any saved assessment back into the Workstation, export your list as CSV, or remove records at any time.'
        },
        {
          sel: '#dash-profile .hx-panel-head',
          title: '4. Edit profile or delete account',
          body: 'Update your display name, role and how you heard about us below. At the very bottom of Account & profile, you can permanently delete your account.'
        }
      ];
    }
    return [];
  }

  function findTarget(sel) {
    var node = document.querySelector(sel);
    if (!node) return null;
    var r = node.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return null;
    return node;
  }

  function ensureUI() {
    if (root) return;
    injectStyles();
    root = el('div', 'cs-tut-root');
    root.hidden = true;
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-label', 'Guided tutorial');

    spot = el('div', 'cs-tut-spot');
    arrow = el('div', 'cs-tut-arrow');
    pop = el('div', 'cs-tut-pop');

    root.append(spot, arrow, pop);
    document.body.appendChild(root);

    window.addEventListener('resize', function () { if (active) positionStep(false); });
    window.addEventListener('scroll', function () { if (active) positionStep(false); }, { passive: true });
    document.addEventListener('keydown', function (e) { if (active && e.key === 'Escape') finish(true); });
  }

  function renderArrowSvg(dir) {
    clear(arrow);
    arrow.className = 'cs-tut-arrow ' + dir;
    var NS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 44 44');
    svg.setAttribute('width', '44');
    svg.setAttribute('height', '44');
    var p = document.createElementNS(NS, 'path');
    p.setAttribute('fill', 'none');
    p.setAttribute('stroke', 'currentColor');
    p.setAttribute('stroke-width', '3.2');
    p.setAttribute('stroke-linecap', 'round');
    p.setAttribute('stroke-linejoin', 'round');
    if (dir === 'up') {
      p.setAttribute('d', 'M22 40V8 M11 19L22 7L33 19');
    } else {
      p.setAttribute('d', 'M22 4V36 M11 25L22 37L33 25');
    }
    svg.appendChild(p);
    arrow.appendChild(svg);
  }

  function renderPop() {
    var s = steps[idx];
    clear(pop);

    var top = el('div', 'cs-tut-top');
    top.appendChild(el('span', 'cs-tut-badge', 'Tour \u00b7 Step ' + (idx + 1) + ' of ' + steps.length));
    var sk = el('button', 'cs-tut-skip', 'Skip tour'); sk.type = 'button';
    sk.addEventListener('click', function () { finish(true); });
    top.appendChild(sk);

    var h = el('h3', 'cs-tut-h', s.title);
    var p = el('p', 'cs-tut-p', s.body);

    var foot = el('div', 'cs-tut-foot');
    var dots = el('div', 'cs-tut-dots');
    for (var i = 0; i < steps.length; i++) {
      var d = el('i', i === idx ? 'on' : '');
      dots.appendChild(d);
    }
    var btns = el('div', 'cs-tut-btns');
    if (idx > 0) {
      var bk = el('button', 'cs-tut-btn line', 'Back'); bk.type = 'button';
      bk.addEventListener('click', function () { idx--; showStep(); });
      btns.appendChild(bk);
    }
    var nx = el('button', 'cs-tut-btn pri', idx < steps.length - 1 ? 'Next' : 'Got it');
    nx.type = 'button';
    nx.addEventListener('click', function () {
      if (idx < steps.length - 1) { idx++; showStep(); }
      else finish(false);
    });
    btns.appendChild(nx);
    foot.append(dots, btns);

    pop.append(top, h, p, foot);
  }

  function positionStep(doScroll) {
    if (!active || !steps[idx]) return;
    var target = findTarget(steps[idx].sel);
    if (!target) return;
    if (doScroll) {
      var r0 = target.getBoundingClientRect();
      if (r0.top < 76 || r0.bottom > window.innerHeight - 160) {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
    var r = target.getBoundingClientRect();
    var pad = 6;
    var sx = Math.max(4, r.left - pad);
    var sy = Math.max(4, r.top - pad);
    var sw = Math.min(window.innerWidth - sx - 4, r.width + pad * 2);
    var sh = Math.min(window.innerHeight - sy - 4, r.height + pad * 2);
    spot.style.left = sx + 'px';
    spot.style.top = sy + 'px';
    spot.style.width = sw + 'px';
    spot.style.height = sh + 'px';

    var popRect = pop.getBoundingClientRect();
    var vw = window.innerWidth, vh = window.innerHeight;
    var gap = 52;
    var spaceBelow = vh - (sy + sh);
    var spaceAbove = sy;
    var placeBelow = spaceBelow >= popRect.height + gap + 12 || spaceBelow >= spaceAbove;

    var popTop = placeBelow
      ? Math.min(vh - popRect.height - 12, sy + sh + gap)
      : Math.max(12, sy - popRect.height - gap);
    var centerTargetX = sx + sw / 2;
    var popLeft = Math.max(12, Math.min(vw - popRect.width - 12, centerTargetX - popRect.width / 2));

    pop.style.left = popLeft + 'px';
    pop.style.top = popTop + 'px';

    var arrowX = Math.max(popLeft + 20, Math.min(popLeft + popRect.width - 64, centerTargetX - 22));
    if (placeBelow) {
      renderArrowSvg('up');
      arrow.style.left = arrowX + 'px';
      arrow.style.top = Math.max(8, sy + sh + 6) + 'px';
    } else {
      renderArrowSvg('down');
      arrow.style.left = arrowX + 'px';
      arrow.style.top = Math.max(8, popTop + popRect.height + 4) + 'px';
    }
  }

  function showStep() {
    while (idx < steps.length && !findTarget(steps[idx].sel)) idx++;
    if (idx >= steps.length) { finish(false); return; }
    renderPop();
    positionStep(true);
    clearTimeout(repositionTimer);
    repositionTimer = setTimeout(function () { positionStep(false); }, 320);
  }

  async function markSeen() {
    try { localStorage.setItem('cs-tour-seen', '1'); } catch (e) { /* ignore */ }
    var a = getAuth();
    if (!a.user) return;
    try {
      await fetch('/api/account', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': a.csrf || '' },
        body: JSON.stringify({ action: 'tour' })
      });
    } catch (e) { /* ignore */ }
  }

  function finish() {
    active = false;
    clearTimeout(repositionTimer);
    if (root) root.hidden = true;
    markSeen();
  }

  function start() {
    steps = pageSteps().filter(function (s) { return Boolean(findTarget(s.sel)); });
    if (!steps.length) return;
    ensureUI();
    active = true;
    idx = 0;
    root.hidden = false;
    showStep();
  }

  window.CSTutorial = { start: start, finish: finish };
})();
