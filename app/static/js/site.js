/* ==========================================================================
   Designplus Solutions — shared site behaviour
   Mobile navigation and the footer copyright year. Loaded with `defer` on
   every page, so the DOM is ready by the time this runs.
   ========================================================================== */

(function () {
  'use strict';

  /* ── Mobile navigation ────────────────────────────────────────────────── */

  var toggle = document.querySelector('.nav-toggle');
  var links = document.getElementById('nav-links');
  var mobileQuery = window.matchMedia('(max-width: 768px)');

  if (toggle && links) {
    // The menu is only ever collapsed on small screens. On desktop the list
    // must stay visible, so `hidden` is cleared whenever we cross the break.
    var syncToBreakpoint = function () {
      if (mobileQuery.matches) {
        links.hidden = toggle.getAttribute('aria-expanded') !== 'true';
      } else {
        links.hidden = false;
      }
    };

    var setExpanded = function (expanded) {
      toggle.setAttribute('aria-expanded', String(expanded));
      syncToBreakpoint();
    };

    setExpanded(false);

    toggle.addEventListener('click', function () {
      setExpanded(toggle.getAttribute('aria-expanded') !== 'true');
    });

    // Following a link inside the drawer should close it behind you.
    links.addEventListener('click', function (event) {
      if (event.target.closest('a') && mobileQuery.matches) setExpanded(false);
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
        setExpanded(false);
        toggle.focus();
      }
    });

    // Safari < 14 only supports the deprecated addListener form.
    if (mobileQuery.addEventListener) {
      mobileQuery.addEventListener('change', syncToBreakpoint);
    } else if (mobileQuery.addListener) {
      mobileQuery.addListener(syncToBreakpoint);
    }
  }

  /* ── Footer year ──────────────────────────────────────────────────────── */

  var year = document.querySelector('[data-current-year]');
  if (year) year.textContent = String(new Date().getFullYear());
})();
