// Sessions use one cookie per browser. Recheck the visible workspace when returning to a tab.
window.watchAccountTab = function (initialCsrf) {
  let checking = false;
  async function check() {
    if (checking || document.hidden) return;
    checking = true;
    try {
      const response = await fetch('/api/session', {cache:'no-store', credentials:'same-origin'});
      if (response.ok) {
        const session = await response.json();
        if ((session.csrf || '') !== initialCsrf) location.replace(session.user ? '/app' : '/signin');
      }
    } catch { /* Retry when focus or connectivity returns. */ }
    finally { checking = false; }
  }
  window.addEventListener('focus', check);
  window.addEventListener('online', check);
  window.addEventListener('pageshow', event => { if (event.persisted) check(); });
  document.addEventListener('visibilitychange', check);
};
