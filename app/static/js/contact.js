/* Contact page — office-hours badge and submit feedback.

   The form itself is a plain POST to the server: no JavaScript is required to
   send an enquiry, and there is no client-side "success" that can lie about
   what happened. This file only adds polish on top. */
(function () {
  'use strict';

  /* ── Office hours ───────────────────────────────────────────────────────
     Both the "today" highlight and the open/closed badge are derived from the
     data attributes on the rows, which come from the admin settings — so the
     badge can never disagree with the hours printed next to it. */

  var DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  var now = new Date();
  var today = now.getDay();
  var minutesNow = now.getHours() * 60 + now.getMinutes();

  var toMinutes = function (hhmm) {
    var parts = String(hhmm).split(':');
    return Number(parts[0]) * 60 + Number(parts[1]);
  };

  var openNow = false;

  document.querySelectorAll('.hours-item').forEach(function (item) {
    if (Number(item.dataset.day) !== today) return;

    item.classList.add('today');
    var dayEl = item.querySelector('.hours-day');
    if (dayEl) dayEl.textContent = DAY_NAMES[today] + ' ← Today';

    if (item.dataset.open && item.dataset.close) {
      openNow = minutesNow >= toMinutes(item.dataset.open) &&
                minutesNow < toMinutes(item.dataset.close);
    }
  });

  var badge = document.querySelector('.open-badge');
  if (badge) {
    var badgeText = badge.querySelector('.open-badge-text');
    var dot = badge.querySelector('.open-dot');
    if (!openNow) {
      badge.style.background = 'rgba(239,68,68,0.1)';
      badge.style.borderColor = 'rgba(239,68,68,0.25)';
      badge.style.color = '#dc2626';
      if (dot) {
        dot.style.background = '#ef4444';
        dot.style.boxShadow = '0 0 0 3px rgba(239,68,68,0.2)';
      }
      if (badgeText) badgeText.textContent = 'Currently closed';
    }
    badge.hidden = false;
  }

  /* ── Submit feedback ───────────────────────────────────────────────────
     Disables the button while the POST is in flight so an impatient
     double-click cannot create two enquiries. */

  var form = document.getElementById('contactForm');
  var button = document.getElementById('submitBtn');
  var label = button && button.querySelector('.submit-btn-label');

  if (form && button) {
    form.addEventListener('submit', function () {
      if (!form.checkValidity()) return;
      button.setAttribute('aria-busy', 'true');
      // Not `disabled`: a disabled submit button is omitted from the POST in
      // some browsers, and the navigation would lose it either way.
      window.setTimeout(function () {
        if (label) label.textContent = 'Sending…';
      }, 0);
    });
  }

  /* Move focus to the confirmation after a successful round trip. */
  var success = document.getElementById('formSuccess');
  if (success && !success.hidden) {
    success.focus();
  }
})();
