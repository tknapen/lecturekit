"""In-page helpers shared by the prototype drivers."""
HELPERS = r"""
window.__mon = {viol: []};
window.__readFrame = function (v) {
  const c = document.createElement('canvas'); c.width = v.videoWidth; c.height = v.videoHeight;
  const g = c.getContext('2d'); g.drawImage(v, 0, 0);
  const sx = c.width / 640; let n = 0;
  for (let b = 0; b < 10; b++) {
    const x = Math.round((20 + b * 60 + 28) * sx), y = Math.round(36 * sx);
    const d = g.getImageData(x - 3, y - 3, 7, 7).data; let s = 0;
    for (let i = 0; i < d.length; i += 4) s += d[i] + d[i + 1] + d[i + 2];
    n = (n << 1) | (s / (d.length / 4) / 3 > 128 ? 1 : 0);
  }
  return n;
};
window.__readImg = function (img) {
  const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0); const sx = c.width / 640; let n = 0;
  for (let b = 0; b < 10; b++) {
    const x = Math.round((20 + b * 60 + 28) * sx), y = Math.round(36 * sx);
    const d = g.getImageData(x - 3, y - 3, 7, 7).data; let s = 0;
    for (let i = 0; i < d.length; i += 4) s += d[i] + d[i + 1] + d[i + 2];
    n = (n << 1) | (s / (d.length / 4) / 3 > 128 ? 1 : 0);
  }
  return n;
};
window.__state = function (id) {
  const st = (window.__lkClips || []).find(s => s.id === id); if (!st) return null;
  const vis = Array.from(st.box.querySelectorAll('img.lk-still')).filter(i => getComputedStyle(i).opacity === '1').map(i => +i.getAttribute('data-lk-b'));
  return {phase: st.phase, at: st.at, k: st.k, plays: st.plays, paused: st.v.paused, t: st.v.currentTime,
          src: st.v.getAttribute('src'), driving: st.box.classList.contains('lk-driving'), stills: vis,
          frame: (st.v.readyState >= 2 && st.box.classList.contains('lk-driving')) ? __readFrame(st.v) : null,
          trace: st.trace.slice(-400)};
};
function shownVideo(v) {
  if (!v.closest('section.present')) return false;
  for (let n = v; n && n.tagName !== 'SECTION'; n = n.parentElement) {
    if (n.classList && n.classList.contains('fragment') && !n.classList.contains('visible')) return false;
    const p = n.parentElement;
    if (p && p.classList && p.classList.contains('r-stack'))
      for (let s = n.nextElementSibling; s; s = s.nextElementSibling) if (s.classList.contains('fragment') && s.classList.contains('visible')) return false;
  }
  return true;
}
setInterval(() => {
  document.querySelectorAll('.reveal video').forEach(v => {
    if (!v.paused && !shownVideo(v)) window.__mon.viol.push([Math.round(performance.now()), v.getAttribute('aria-label'), (v.getAttribute('src')||'').split('/').pop(), +v.currentTime.toFixed(3)]);
  });
}, 20);
"""
