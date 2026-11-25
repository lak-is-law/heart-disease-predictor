/* Runs before first paint so the saved or system theme is applied without a flash. */
(function () {
  try {
    var t = localStorage.getItem('cs-theme');
    if (t === 'light' || t === 'dark') document.documentElement.setAttribute('data-theme', t);
  } catch (e) { /* storage blocked: follow the system setting */ }
})();
