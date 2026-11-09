// Segmented-clip runtime: prototype for the synthesized design (design study, not lecturekit code).
// k = number of visible .lk-cue fragments of a clip. Hold boundary T(k) = k+1 (start=auto) or k (start=key).
// Forward: play from where the video is to T(k) (a key pressed during a part extends the target: play-through).
// Backward, or arriving with k > 0: pause and hold T(k) exactly, never play. A still covers every seek.
(function () {
  var Q = new URLSearchParams(location.search);
  var GUARD = parseFloat(Q.get('guard') || '2');          // frames before a boundary at which rVFC pauses
  var NO_RVFC = Q.has('nophase') || Q.has('norvfc');      // test switch: force the timeupdate fallback
  var TU_LEAD = 0.3;                                      // seconds: timeupdate fallback pauses this early
  var SEEK_TIMEOUT = 2000;
  var clips = [];
  var LOG = window.__lkLog = [];
  function L(st, msg) { LOG.push([Math.round(performance.now()), st ? st.id : '-', msg]); }

  function receiver() { return !!(window.Reveal && Reveal.isSpeakerNotes && Reveal.isSpeakerNotes()); }
  function printing() { return /print-pdf/i.test(location.search) || (Reveal.isPrintView && Reveal.isPrintView()); }
  function live(st) {
    return !receiver() && !printing() && st.slide.classList.contains('present') && !Reveal.isOverview() &&
      !document.hidden && !st.degraded;
  }
  function kOf(st) { return st.slide.querySelectorAll('.lk-cue[data-lk-for="' + st.id + '"].visible').length; }
  function T(st, k) { return st.key ? k : k + 1; }          // boundary that state k holds on
  function last(st) { return st.bounds.length - 1; }
  function tOf(st, b) { return st.bounds[b].t + 0.5 / st.fps; } // middle of frame b's display interval
  function setAttr(st) { st.box.setAttribute('data-lk-phase', st.phase); st.box.setAttribute('data-lk-at', String(st.at)); }
  function showStill(st, b) { st.box.classList.remove('lk-driving'); st.box.setAttribute('data-lk-show', String(b)); }
  function staticStill(st) { st.box.classList.remove('lk-driving'); st.box.removeAttribute('data-lk-show'); }
  function drive(st) { st.box.classList.add('lk-driving'); st.box.removeAttribute('data-lk-show'); }
  function pause(st) { if (!st.v.paused) st.v.pause(); }
  function phase(st, p, at) { st.phase = p; if (at !== undefined) st.at = at; setAttr(st); }

  function load(st) {
    if (st.v.getAttribute('src')) return;
    var src = st.v.getAttribute('data-lk-src') + '?v=' + st.ver;
    st.v.preload = 'auto'; st.v.setAttribute('src', src); st.v.load();
    L(st, 'load ' + src);
  }
  // A server without byte ranges: if the video is not seekable over its whole length once metadata is in,
  // fetch it into a Blob and swap the source (http(s) only).
  function checkSeekable(st) {
    var v = st.v, s = v.seekable, ok = s.length > 0 && s.end(s.length - 1) >= v.duration - 0.05;
    L(st, 'seekable ranges=' + s.length + (s.length ? ' end=' + s.end(s.length - 1).toFixed(3) : '') + ' dur=' + v.duration.toFixed(3));
    if (ok || st.blob || !/^https?:/.test(location.protocol)) return;
    st.blob = true; var gen = ++st.gen;
    L(st, 'not seekable: fetching Blob');
    fetch(v.currentSrc).then(function (r) { return r.blob(); }).then(function (b) {
      v.src = URL.createObjectURL(b); v.load(); L(st, 'blob swapped');
      st.entered = false; reconcile(st, 'blob');
    });
  }

  // seek onto boundary b; resolves true once that frame is up (stale generation: false)
  function seek(st, b, gen) {
    var v = st.v, t = tOf(st, b);
    return new Promise(function (resolve) {
      var done = false;
      function finish(ok) { if (done) return; done = true; clearTimeout(timer); v.removeEventListener('seeked', onSeeked); resolve(ok && gen === st.gen); }
      function onSeeked() {
        if (gen !== st.gen) return finish(false);
        if (Math.abs(v.currentTime - t) > 0.5 / st.fps) { L(st, 'seek missed ' + v.currentTime.toFixed(4) + ' want ' + t.toFixed(4)); return finish(false); }
        if (v.requestVideoFrameCallback) v.requestVideoFrameCallback(function () { finish(true); });
        requestAnimationFrame(function () { requestAnimationFrame(function () { finish(true); }); });
      }
      var timer = setTimeout(function () { if (gen === st.gen) { L(st, 'seek timeout'); st.degraded = true; staticStill(st); phase(st, 'degraded'); } finish(false); }, SEEK_TIMEOUT);
      v.addEventListener('seeked', onSeeked);
      if (v.readyState < 1) v.addEventListener('loadedmetadata', function () { if (!done && gen === st.gen) v.currentTime = t; }, { once: true });
      else v.currentTime = t;
    });
  }

  function hold(st, b, why) {
    var gen = ++st.gen;
    pause(st); showStill(st, b); phase(st, 'seeking', b);
    seek(st, b, gen).then(function (ok) { if (ok) { drive(st); phase(st, 'holding', b); L(st, 'hold b' + b + ' (' + why + ')'); } });
  }

  // play towards boundary st.target, from boundary `from` (seek first) or from where the video is (from = null)
  function playTo(st, target, from) {
    var gen = ++st.gen; st.target = target;
    function go() {
      if (gen !== st.gen) return;
      drive(st); phase(st, 'playing', from === null ? st.at : from);
      watch(st, gen);
      var p = st.v.play();
      if (p && p.catch) p.catch(function (e) {
        if (gen !== st.gen) return;
        L(st, 'play refused: ' + e.name); phase(st, 'blocked'); showStill(st, from === null ? st.at : from);
      });
      L(st, 'play to b' + target + (from === null ? ' from here' : ' from b' + from));
    }
    if (from === null) return go();
    pause(st); showStill(st, from); phase(st, 'seeking', from);
    seek(st, from, gen).then(function (ok) { if (ok) go(); });
  }

  function arrive(st, gen) {          // the watched frame reached the target: pause, then seek onto it exactly
    var b = st.target; st.gen++; var g = st.gen;
    pause(st);
    st.trace.push(['pause', st.lastMedia, st.v.currentTime, b]);
    seek(st, b, g).then(function (ok) { if (ok) { phase(st, 'holding', b); L(st, 'reached b' + b + ' (paused at ' + st.lastMedia.toFixed(4) + ')'); } });
  }
  function watch(st, gen) {
    function due(mt) { return mt >= st.bounds[st.target].t - GUARD / st.fps - 1e-4; }
    if (st.v.requestVideoFrameCallback && !NO_RVFC) {
      var cb = function (now, md) {
        st.lastMedia = md.mediaTime; st.trace.push(['f', md.mediaTime]);
        if (gen !== st.gen || st.phase !== 'playing') return;
        if (due(md.mediaTime)) return arrive(st, gen);
        st.v.requestVideoFrameCallback(cb);
      };
      st.v.requestVideoFrameCallback(cb);
    } else {
      st.v.ontimeupdate = function () {
        if (gen !== st.gen || st.phase !== 'playing') return;
        st.lastMedia = st.v.currentTime; st.trace.push(['tu', st.v.currentTime]);
        if (st.v.currentTime >= st.bounds[st.target].t - TU_LEAD) arrive(st, gen);
      };
    }
  }

  function reconcile(st, why) {
    if (!live(st)) {
      if (Reveal.isOverview() && st.entered && st.slide.classList.contains('present') && (st.phase === 'playing' || st.phase === 'paused')) {
        st.gen++; pause(st); phase(st, 'paused'); st.ov = st.k; L(st, 'overview: paused'); return;
      }
      st.ov = null;
      if (st.entered || !st.v.paused) L(st, 'not live (' + why + '): pause');
      st.gen++; pause(st); staticStill(st); st.entered = false; phase(st, 'static');
      return;
    }
    load(st);
    var k = kOf(st);
    if (!st.entered) {
      st.entered = true; st.k = k; L(st, 'enter k=' + k + ' (' + why + ')');
      if (k === 0 && !st.key) return playTo(st, T(st, 0), 0);
      return hold(st, T(st, k), 'enter');
    }
    if (st.ov !== null && st.ov !== undefined) {
      var ov = st.ov; st.ov = null;
      if (k === ov) { L(st, 'overview closed: resume'); return playTo(st, st.target, null); }
    }
    if (k === st.k) return;
    var prev = st.k; st.k = k; L(st, 'k ' + prev + '->' + k + ' (' + why + ')');
    if (k < prev) return hold(st, T(st, k), 'back');
    // forward: play-through. Holding or paused: continue from here; playing: just move the target.
    if (st.phase === 'playing') { st.target = T(st, k); L(st, 'target -> b' + st.target); return; }
    if (st.phase === 'holding' || st.phase === 'paused') return playTo(st, T(st, k), null);
    return playTo(st, T(st, k), T(st, k) - 1);   // seeking or blocked: start the latest part from its start
  }

  function current() {
    var s = Reveal.getCurrentSlide();
    for (var i = 0; i < clips.length; i++) if (clips[i].slide === s) return clips[i];
    return null;
  }
  function all(why) { clips.forEach(function (st) { reconcile(st, why); }); preloadNear(); guard(); }
  function preloadNear() {
    if (receiver() || printing()) return;
    var cur = Reveal.getIndices().h;
    clips.forEach(function (st) { if (Math.abs(st.h - cur) <= 1) load(st); });
  }

  // keys go through Reveal's keyboard config: it runs before plugin bindings (Quarto's R) and the built-ins,
  // and triggerKey from the speaker window reaches it
  function toMain(cmd) {
    try { window.parent.opener.postMessage(JSON.stringify({ namespace: 'lecturekit', cmd: cmd, state: Reveal.getState() }), '*'); } catch (e) {}
  }
  function space(e) {
    var st = current();
    if (receiver()) { if (st) return toMain('space'); }
    if (!st || !live(st)) return (e && e.shiftKey) ? Reveal.prev() : Reveal.next();
    if (e && e.shiftKey) return Reveal.prev();
    if (st.phase === 'playing') { st.gen++; pause(st); phase(st, 'paused'); L(st, 'space: pause'); }
    else if (st.phase === 'paused') { playTo(st, st.target, null); }
    else if (st.phase === 'blocked') { playTo(st, st.target, st.at); }
    else if (st.phase === 'holding') { if (st.at < last(st)) Reveal.next(); else L(st, 'space at final hold: ignored'); }
  }
  function replay() {
    var st = current();
    if (receiver()) { if (st) toMain('replay'); return; }
    if (!st || !live(st)) return;
    var b = T(st, st.k); if (b === 0) return;
    L(st, 'R: replay part to b' + b); playTo(st, b, b - 1);
  }
  window.addEventListener('message', function (ev) {
    var d; try { d = JSON.parse(ev.data); } catch (e) { return; }
    if (!d || d.namespace !== 'lecturekit' || receiver()) return;
    var s = Reveal.getState();
    L(null, 'relay ' + d.cmd + ' from speaker');
    if (d.state.indexh !== s.indexh || d.state.indexv !== s.indexv || d.state.indexf !== s.indexf) { L(null, 'relay stale: ignored'); return; }
    if (d.cmd === 'space') space({}); else if (d.cmd === 'replay') replay();
  });

  // deck-wide guard (also the I9 fix): no video plays unless it is on the present slide, outside hidden fragments
  // and not an r-stack step that a later visible fragment covers
  function shownVideo(v) {
    if (!v.closest('section.present')) return false;
    for (var n = v; n && n.tagName !== 'SECTION'; n = n.parentElement) {
      if (n.classList && n.classList.contains('fragment') && !n.classList.contains('visible')) return false;
      var p = n.parentElement;
      if (p && p.classList && p.classList.contains('r-stack')) {
        for (var s = n.nextElementSibling; s; s = s.nextElementSibling) if (s.classList.contains('fragment') && s.classList.contains('visible')) return false;
      }
    }
    return true;
  }
  function guard() {
    document.querySelectorAll('.reveal video').forEach(function (v) {
      if (v.paused) return;
      var st = null; for (var i = 0; i < clips.length; i++) if (clips[i].v === v) st = clips[i];
      if ((st && !live(st)) || receiver() || !shownVideo(v)) { v.pause(); L(st, 'guard paused ' + (v.getAttribute('src') || v.getAttribute('data-lk-src'))); }
    });
    clips.forEach(function (st) {
      if (st.phase === 'playing' && st.v.currentTime > st.bounds[st.target].t + 2 / st.fps) { L(st, 'guard: overshoot'); hold(st, st.target, 'overshoot'); }
    });
  }

  var inited = false;
  function init() {
    if (inited) return; inited = true;
    var hs = Reveal.getHorizontalSlides();
    document.querySelectorAll('.lk-seg').forEach(function (box) {
      var v = box.querySelector('video'), slide = box.closest('section');
      var st = { id: box.getAttribute('data-lk-seg'), box: box, v: v, slide: slide, h: hs.indexOf(slide),
        fps: parseFloat(box.getAttribute('data-lk-fps')), bounds: JSON.parse(box.getAttribute('data-lk-bounds')),
        key: box.getAttribute('data-lk-start') === 'key', ver: box.getAttribute('data-lk-v') || '0',
        gen: 0, k: 0, at: -1, target: -1, phase: 'static', entered: false, degraded: false, blob: false,
        trace: [], lastMedia: 0, plays: 0 };
      v.addEventListener('play', function () {
        st.plays++;
        if (st.phase !== 'playing' || !live(st)) {
          L(st, 'foreign play: paused'); st.v.pause();
          if (st.phase === 'holding' && live(st)) hold(st, st.at, 'foreign play');   // the play moved the frame: put it back
        }
      });
      v.addEventListener('loadedmetadata', function () { checkSeekable(st); });
      v.addEventListener('error', function () { L(st, 'media error'); st.degraded = true; staticStill(st); phase(st, 'degraded'); });
      clips.push(st); setAttr(st);
    });
    window.__lkClips = clips;
    var kb = Object.assign({}, typeof Reveal.getConfig().keyboard === 'object' ? Reveal.getConfig().keyboard : {});
    kb[32] = space; kb[82] = replay;
    Reveal.configure({ keyboard: kb });
    ['slidechanged', 'fragmentshown', 'fragmenthidden', 'overviewshown', 'overviewhidden'].forEach(function (ev) {
      Reveal.on(ev, function () { L(null, 'event ' + ev + ' f=' + Reveal.getIndices().f); all(ev); });
    });
    Reveal.on('paused', function () { clips.forEach(function (st) { if (st.phase === 'playing') { st.gen++; pause(st); phase(st, 'paused'); st.blanked = true; } }); });
    Reveal.on('resumed', function () { clips.forEach(function (st) { if (st.blanked) { st.blanked = false; if (st.phase === 'paused') playTo(st, st.target, null); } }); });
    document.addEventListener('visibilitychange', function () { all('visibility'); });
    setInterval(guard, 250);
    all('ready');
  }
  window.addEventListener('load', function () {
    if (!window.Reveal) return;
    if (Reveal.isReady()) init(); else Reveal.on('ready', init);
  });
})();
