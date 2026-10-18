/* ==========================================================================
   Hisense Dashboard - shared layout helper
   Measures the tab bar + header heights so the header and filter bar can be
   frozen (position: sticky) directly underneath them on every page, and flags
   the filter bar with .is-stuck once it is pinned.
   ========================================================================== */
(function () {
  var root = document.documentElement;

  function measure() {
    var nav = document.querySelector('.browser-tab-nav');
    var top = document.querySelector('header.topbar');
    var navH = nav ? nav.getBoundingClientRect().height : 0;
    var topH = top ? top.getBoundingClientRect().height : 0;
    root.style.setProperty('--nav-h', navH + 'px');
    root.style.setProperty('--top-h', topH + 'px');
    checkStuck();
  }

  function checkStuck() {
    var fb = document.querySelector('.filterbar');
    if (!fb) return;
    var pinAt = parseFloat(getComputedStyle(root).getPropertyValue('--nav-h') || 0) +
                parseFloat(getComputedStyle(root).getPropertyValue('--top-h') || 0);
    var stuck = getComputedStyle(fb).position === 'sticky' &&
                fb.getBoundingClientRect().top <= pinAt + 1 && window.scrollY > 0;
    fb.classList.toggle('is-stuck', stuck);
  }

  var ticking = false;
  window.addEventListener('scroll', function () {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () { checkStuck(); ticking = false; });
  }, { passive: true });
  window.addEventListener('resize', measure);
  window.addEventListener('load', measure);
  if (window.ResizeObserver) {
    var ro = new ResizeObserver(measure);
    ['.browser-tab-nav', 'header.topbar'].forEach(function (sel) {
      var el = document.querySelector(sel);
      if (el) ro.observe(el);
    });
  }
  measure();
})();
