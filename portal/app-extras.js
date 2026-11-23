/* Workstation glue: sign-in goes to the sign-in page, and #dashboard opens the dashboard once the session is known. */
(function () {
  'use strict';
  window.openAuthModal = function () { location.href = '/signin?next=/app'; };
  function openHash() { if (location.hash === '#dashboard' && window.CSDash && window.CS && window.CS.user) window.CSDash.open(); }
  document.addEventListener('cs:session', function () { setTimeout(openHash, 300); });
  window.addEventListener('hashchange', openHash);
})();
