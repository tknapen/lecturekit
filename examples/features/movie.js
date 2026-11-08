// movie.js: clips autoplay when their slide (or fragment) appears, which
// Reveal does through data-autoplay. This adds: click on a clip to pause and
// resume, R to replay the clips on the current slide from the start.
(function () {
  function ready(fn) {
    if (window.Reveal && Reveal.isReady && Reveal.isReady()) fn();
    else if (window.Reveal) Reveal.on('ready', fn);
    else document.addEventListener('DOMContentLoaded', function () { if (window.Reveal) Reveal.on('ready', fn); });
  }
  function clips(section) {
    return section ? Array.prototype.slice.call(section.querySelectorAll('video.lk-clip')) : [];
  }
  ready(function () {
    document.querySelectorAll('video.lk-clip').forEach(function (v) {
      v.controls = false;
      v.addEventListener('click', function (e) {
        e.preventDefault(); e.stopPropagation();
        if (v.paused) v.play(); else v.pause();
      });
    });
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'r' && e.key !== 'R') return;
      clips(Reveal.getCurrentSlide()).forEach(function (v) {
        if (v.closest('.fragment') && !v.closest('.fragment').classList.contains('visible')) return;
        v.currentTime = 0; v.play();
      });
    });
    // a clip inside a fragment starts when the fragment appears
    Reveal.on('fragmentshown', function (ev) {
      clips(ev.fragment).forEach(function (v) { v.currentTime = 0; v.play(); });
    });
    Reveal.on('fragmenthidden', function (ev) {
      clips(ev.fragment).forEach(function (v) { v.pause(); });
    });
  });
})();
