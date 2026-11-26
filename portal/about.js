(function () {
  'use strict';
  const scene = document.querySelector('.about-scene');
  const intro = scene.querySelector('.about-intro');
  const portrait = scene.querySelector('.about-motion');
  const canvas = portrait.querySelector('canvas');
  const ctx = canvas.getContext('2d');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const sheet = new Image();
  const regions = [[196, 262], [435, 311], [692, 219]];
  const width = 96, height = 60, lastFrame = 15;
  let value = 0, target = 0, frame = 0, previous = 0;

  function ease(t) { return t * t * (3 - 2 * t); }

  function draw(time) {
    frame = 0;
    const elapsed = Math.min(64, previous ? time - previous : 16);
    previous = time;
    // A longer release keeps a wheel flick or reversed swipe from snapping the smile shut.
    value += (target - value) * (1 - Math.exp(-elapsed / (target < value ? 560 : 285)));
    if (Math.abs(target - value) < .001) value = target;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const position = value * lastFrame;
    if (position > 0) regions.forEach(([x, y], column) => {
      const lower = Math.floor(position);
      ctx.globalAlpha = 1;
      ctx.drawImage(sheet, column * width, lower * height, width, height, x, y, width, height);
      if (lower < lastFrame) {
        ctx.globalAlpha = position - lower;
        ctx.drawImage(sheet, column * width, (lower + 1) * height, width, height, x, y, width, height);
      }
    });
    ctx.globalAlpha = 1;
    if (target !== value) frame = requestAnimationFrame(draw);
    else previous = 0;
  }

  function update() {
    if (!scene.classList.contains('is-animated')) return;
    const distance = Math.max(1, scene.offsetHeight - intro.offsetHeight);
    const p = Math.max(0, Math.min(1, -scene.getBoundingClientRect().top / distance));
    target = p < .32 ? ease(p / .32) : p <= .42 ? 1 : 1 - ease((p - .42) / .58);
    if (!frame && target !== value) frame = requestAnimationFrame(draw);
  }
  function setup() {
    const active = !!ctx && sheet.naturalWidth > 0 && !reduced.matches;
    scene.classList.toggle('is-animated', active);
    cancelAnimationFrame(frame);
    frame = previous = 0;
    if (!active) { value = target = 0; ctx?.clearRect(0, 0, canvas.width, canvas.height); return; }
    const header = document.querySelector('.site-head').offsetHeight;
    scene.style.setProperty('--portrait-top', Math.min(header, innerHeight - intro.offsetHeight) + 'px');
    update();
  }
  window.addEventListener('scroll', update, {passive: true});
  window.addEventListener('resize', setup);
  reduced.addEventListener('change', setup);
  sheet.onload = setup;
  sheet.src = '/img/clinical-expressions.webp';
})();
