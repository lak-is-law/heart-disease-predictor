/* Workstation glue: sign-in goes to the sign-in page, and #dashboard opens the dashboard once the session is known. */
(function () {
  'use strict';
  window.openAuthModal = function () { location.href = '/signin?next=/app'; };
  function openHash() { if (location.hash === '#dashboard') location.replace('/app'); }
  document.addEventListener('cs:session', function () { setTimeout(openHash, 300); });
  window.addEventListener('hashchange', openHash);
})();

/* "Open" from the dashboard hands the inputs over through sessionStorage. */
(function () {
  var raw; try { raw = sessionStorage.getItem('cs-open'); sessionStorage.removeItem('cs-open'); } catch (e) { return; }
  if (!raw) return;
  var vals; try { vals = JSON.parse(raw); } catch (e) { return; }
  window.addEventListener('load', function () {
    setTimeout(function () {
      const picker = document.getElementById('sample-case');
      if (picker) picker.value = '';
      Object.keys(vals).forEach(function (k) { var n = document.getElementById('inp-' + k); if (n) n.value = String(vals[k]); });
      if (window.updatePortalPrediction) updatePortalPrediction();
      var ws = document.getElementById('live-workstation'); if (ws) ws.scrollIntoView({ behavior: 'smooth' });
    }, 600);
  });
})();
/* Save to dashboard asks for a short reference first. */
window.csAskRef = function () { return (window.prompt ? (window.prompt('Reference for this assessment (no names):', '') || '') : '').trim().slice(0, 40); };
