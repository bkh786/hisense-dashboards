/* ==========================================================================
   Hisense Dashboard - shared layout helper
   1. Measures the tab bar + header heights so the header is frozen smoothly.
   2. Controls the collapsible left filter sidebar drawer across all pages.
   3. Manages filter toggle button, edge toggle, backdrop, ESC key, and active badge.
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
  }

  // --- Collapsible Filter Sidebar Drawer Controller ---
  var isFilterSidebarInitialized = false;
  function initFilterSidebar() {
    if (isFilterSidebarInitialized) return;
    var toggleBtn = document.getElementById('filterToggleBtn');
    var sidebar = document.getElementById('filterSidebar');
    isFilterSidebarInitialized = true;
    var backdrop = document.getElementById('filterBackdrop');
    var closeBtn = document.getElementById('filterSidebarClose');
    var edgeToggle = document.getElementById('filterSidebarEdgeToggle');
    var applyBtn = document.getElementById('filterSidebarApply');
    var resetLink = document.getElementById('filterSidebarReset');
    var resetBtn = document.getElementById('resetBtn');

    function openSidebar() {
      sidebar.classList.add('is-open');
      if (backdrop) backdrop.classList.add('is-open');
      if (toggleBtn) {
        toggleBtn.classList.add('is-active');
        toggleBtn.setAttribute('aria-expanded', 'true');
      }
      document.body.classList.add('filter-sidebar-open');
    }

    function closeSidebar() {
      sidebar.classList.remove('is-open');
      if (backdrop) backdrop.classList.remove('is-open');
      if (toggleBtn) {
        toggleBtn.classList.remove('is-active');
        toggleBtn.setAttribute('aria-expanded', 'false');
      }
      document.body.classList.remove('filter-sidebar-open');
      // Close any open multi-select panels inside
      document.querySelectorAll('.msel.open').forEach(function (m) {
        m.classList.remove('open');
      });
    }

    if (toggleBtn) {
      toggleBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        if (sidebar.classList.contains('is-open')) {
          closeSidebar();
        } else {
          openSidebar();
        }
      });
    }

    if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if (edgeToggle) edgeToggle.addEventListener('click', closeSidebar);
    if (backdrop) backdrop.addEventListener('click', closeSidebar);
    if (applyBtn) applyBtn.addEventListener('click', closeSidebar);

    if (resetLink) {
      resetLink.addEventListener('click', function (e) {
        e.preventDefault();
        if (resetBtn) resetBtn.click();
      });
    }

    // Keyboard ESC to close
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && sidebar.classList.contains('is-open')) {
        closeSidebar();
      }
    });

    // Update active filters badge on the floating toggle button
    function updateActiveFilterBadge() {
      var badge = document.getElementById('filterActiveBadge');
      if (!badge) return;
      var count = 0;
      // Check multi-selects
      document.querySelectorAll('#filterGrid .msel-btn .val').forEach(function (valSpan) {
        var text = (valSpan.textContent || '').trim().toLowerCase();
        if (text && text !== 'all' && text !== 'none' && text !== 'all selected') {
          count++;
        }
      });
      // Check custom date inputs if different from default min/max
      var dFrom = document.getElementById('dateFromInput');
      var dTo = document.getElementById('dateToInput');
      if (dFrom && dTo) {
        if (dFrom.value && dFrom.min && dFrom.value !== dFrom.min) count++;
        if (dTo.value && dTo.max && dTo.value !== dTo.max) count++;
      }
      if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'inline-flex';
        badge.title = count + ' active filter' + (count > 1 ? 's' : '');
      } else {
        badge.style.display = 'none';
      }
    }

    var filterGrid = document.getElementById('filterGrid');
    if (filterGrid) {
      filterGrid.addEventListener('change', function () {
        setTimeout(updateActiveFilterBadge, 100);
      });
      filterGrid.addEventListener('click', function () {
        setTimeout(updateActiveFilterBadge, 150);
      });
      if (window.MutationObserver) {
        var obs = new MutationObserver(function () {
          setTimeout(updateActiveFilterBadge, 100);
        });
        obs.observe(filterGrid, { childList: true, subtree: true, characterData: true });
      }
    }

    if (resetBtn) {
      resetBtn.addEventListener('click', function () {
        setTimeout(updateActiveFilterBadge, 150);
      });
    }

    // Initial badge check after filters are rendered
    setTimeout(updateActiveFilterBadge, 400);
    setTimeout(updateActiveFilterBadge, 1200);

    window.openFilterSidebar = openSidebar;
    window.closeFilterSidebar = closeSidebar;
  }

  window.addEventListener('resize', measure);
  window.addEventListener('load', function () {
    measure();
    initFilterSidebar();
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFilterSidebar);
  } else {
    initFilterSidebar();
  }

  if (window.ResizeObserver) {
    var ro = new ResizeObserver(measure);
    ['.browser-tab-nav', 'header.topbar'].forEach(function (sel) {
      var el = document.querySelector(sel);
      if (el) ro.observe(el);
    });
  }
  measure();
})();
