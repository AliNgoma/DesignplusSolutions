/* Services page — FAQ accordion. */
(function () {
  'use strict';

  var items = Array.prototype.slice.call(document.querySelectorAll('.faq-item'));

  var setOpen = function (item, open) {
    var button = item.querySelector('.faq-q');
    var answer = item.querySelector('.faq-a');
    item.classList.toggle('open', open);
    if (button) button.setAttribute('aria-expanded', String(open));
    if (answer) answer.hidden = !open;
  };

  items.forEach(function (item) {
    // The first item is marked open in the markup; mirror that into ARIA.
    setOpen(item, item.classList.contains('open'));

    var button = item.querySelector('.faq-q');
    if (!button) return;

    button.addEventListener('click', function () {
      var willOpen = !item.classList.contains('open');
      items.forEach(function (other) { setOpen(other, false); });
      setOpen(item, willOpen);
    });
  });
})();
