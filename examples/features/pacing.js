// pacing.js: the live deck's slide numbers in the foot, and a pacing clock
// in the speaker view. Each slide heading carries data-planned, the
// cumulative planned minutes up to and including that slide, written by the
// dual-output filter. The clock compares elapsed time with the plan at the
// current slide and turns red when behind by more than a minute.
(function () {
  function ready(fn) {
    if (window.Reveal && Reveal.isReady && Reveal.isReady()) fn();
    else if (window.Reveal) Reveal.on('ready', fn);
    else document.addEventListener('DOMContentLoaded', function () { if (window.Reveal) Reveal.on('ready', fn); });
  }

  function slideHeading(section) {
    return section && section.querySelector(':scope > h1, :scope > h2, :scope > h3');
  }

  function updateFoot() {
    var foot = document.querySelector('.lk-foot .lk-foot-number');
    var reveal = document.querySelector('.reveal');
    var idx = Reveal.getIndices();
    var total = Reveal.getTotalSlides();
    var current = Reveal.getCurrentSlide();
    var onTitle = current && (current.classList.contains('title-slide') || current.id === 'title-slide');
    if (reveal) reveal.classList.toggle('lk-on-title', !!onTitle);
    if (foot) foot.textContent = (idx.h + 1) + ' / ' + total;
  }

  var start = null;
  function fmt(min) {
    var sign = min < 0 ? '-' : '';
    min = Math.abs(min);
    var m = Math.floor(min), s = Math.round((min - m) * 60);
    if (s === 60) { m += 1; s = 0; }
    return sign + m + ':' + (s < 10 ? '0' : '') + s;
  }

  function pacing() {
    if (!(Reveal.isSpeakerNotes && Reveal.isSpeakerNotes())) return;
    var box = document.querySelector('.lk-pacing');
    if (!box) {
      box = document.createElement('div');
      box.className = 'lk-pacing';
      document.body.appendChild(box);
    }
    if (start === null) start = Date.now();
    var h = slideHeading(Reveal.getCurrentSlide());
    var planned = h && h.dataset.planned ? parseFloat(h.dataset.planned) : null;
    var elapsed = (Date.now() - start) / 60000;
    var text = 'elapsed ' + fmt(elapsed);
    box.classList.remove('lk-behind', 'lk-ahead');
    if (planned !== null) {
      var diff = elapsed - planned;
      text += ' | plan ' + fmt(planned) + ' | ' + (diff > 0 ? '+' : '') + fmt(diff);
      if (diff > 1) box.classList.add('lk-behind');
      else if (diff < -1) box.classList.add('lk-ahead');
    }
    if (window.LK_BUDGET) text += ' | budget ' + fmt(window.LK_BUDGET);
    box.textContent = text;
  }

  ready(function () {
    // the foot is emitted inside the last slide; move it beside the slides
    // so that it scales with them and shows on every slide
    var foot = document.querySelector('.lk-foot');
    var slides = document.querySelector('.reveal .slides');
    if (foot && slides && foot.parentNode !== slides) slides.appendChild(foot);
    updateFoot();
    pacing();
    Reveal.on('slidechanged', function () { updateFoot(); pacing(); });
    setInterval(pacing, 1000);
    // key P resets the clock (speaker view only)
    document.addEventListener('keydown', function (e) {
      if (e.key === 'p' || e.key === 'P') { start = Date.now(); pacing(); }
    });
  });
})();
