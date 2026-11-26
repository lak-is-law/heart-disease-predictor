(function () {
  'use strict';
  var portrait = document.querySelector('.about-portrait');
  var motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var header = document.querySelector('.site-head');
  var pending = false;

  function paint() {
    pending = false;
    if (motion.matches) return;
    var bounds = portrait.getBoundingClientRect();
    var start = bounds.top + window.scrollY;
    // Finish the expression cycle while the faces are still below the sticky header.
    var distance = Math.max(64, start + bounds.height * 0.12 - header.offsetHeight);
    var progress = Math.max(0, Math.min(1, window.scrollY / distance));
    var smile = Math.sin(Math.PI * progress) ** 2;
    portrait.style.setProperty('--smile', smile.toFixed(3));
    portrait.style.setProperty('--lean', (.6 * smile).toFixed(2) + 'deg');
    portrait.style.setProperty('--lift', (-12 * smile).toFixed(2) + 'px');
  }
  function schedule() {
    if (!pending && !motion.matches) { pending = true; requestAnimationFrame(paint); }
  }
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', schedule);
  motion.addEventListener('change', schedule);
  schedule();
})();
