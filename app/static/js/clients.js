/* Clients page — sector tablist. */
(function () {
  'use strict';

  var tabs = Array.prototype.slice.call(document.querySelectorAll('.sector-tab'));
  if (!tabs.length) return;

  var select = function (tab, moveFocus) {
    tabs.forEach(function (other) {
      var isTarget = other === tab;
      var panel = document.getElementById('panel-' + other.dataset.sector);
      other.classList.toggle('active', isTarget);
      other.setAttribute('aria-selected', String(isTarget));
      other.tabIndex = isTarget ? 0 : -1;
      if (panel) {
        panel.classList.toggle('active', isTarget);
        panel.hidden = !isTarget;
      }
    });
    if (moveFocus) tab.focus();
  };

  tabs.forEach(function (tab, index) {
    tab.addEventListener('click', function () { select(tab, false); });

    // Left/right arrows move between tabs, as expected of a tablist.
    tab.addEventListener('keydown', function (event) {
      var offset = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
      if (!offset) return;
      event.preventDefault();
      select(tabs[(index + offset + tabs.length) % tabs.length], true);
    });
  });
})();
