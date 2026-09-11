/* Portfolio page — category filter. */
(function () {
  'use strict';

  var tabs = Array.prototype.slice.call(document.querySelectorAll('.filter-tab'));
  var grid = document.getElementById('projectsGrid');
  if (!tabs.length || !grid) return;

  var cards = Array.prototype.slice.call(grid.querySelectorAll('.project-card'));

  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      var category = tab.dataset.filter;

      tabs.forEach(function (other) {
        var isTarget = other === tab;
        other.classList.toggle('active', isTarget);
        other.setAttribute('aria-pressed', String(isTarget));
      });

      // Toggling `hidden` directly, rather than timing a style change, means
      // clicking through the filters quickly cannot strand a card mid-fade.
      cards.forEach(function (card) {
        card.hidden = !(category === 'all' || card.dataset.category === category);
      });
    });
  });
})();
