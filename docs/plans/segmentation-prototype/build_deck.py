"""Write slides.qmd for the prototype deck: the markup the synthesized filter would emit for a segmented clip,
hand-written as raw HTML (video box) plus pandoc Divs (cue fragments with nested notes)."""
import json
from pathlib import Path

meta = json.loads(Path("assets/clips/meta.json").read_text())


def seg(name, start="auto", label="clip"):
    m = meta[name]
    b = m["bounds"]
    n_stops = len(b) - 2
    imgs = []
    for i, x in enumerate(b):
        s = (i - 1) if start == "auto" else i          # state whose hold this boundary is
        sattr = f' data-lk-s="{s}"' if s >= 0 else ""
        imgs.append(f'<img class="lk-still" data-lk-b="{i}"{sattr} data-src="assets/clips/{name}.f{x["f"]}.png" alt="">')
    bounds = json.dumps([{"f": x["f"], "t": round(x["t"], 6)} for x in b], separators=(",", ":"))
    html = (f'<div class="live-only lk-seg" data-lk-seg="{name}" data-lk-fps="{m["fps"]}" data-lk-start="{start}" '
            f'data-lk-v="p1" data-lk-bounds=\'{bounds}\'>\n'
            f'<video muted playsinline preload="none" disablepictureinpicture aria-label="{label}" '
            f'data-lk-src="assets/clips/{name}.mp4" poster="assets/clips/{name}.f0.png"></video>\n'
            + "\n".join(imgs) + "\n</div>")
    cues = []
    ncues = n_stops if start == "auto" else n_stops + 1
    for k in range(1, ncues + 1):
        cues.append(f'::: {{.fragment .lk-cue data-lk-for="{name}" data-lk-k="{k}"}}\n'
                    f'::: notes\nCUE{k}: part {k + (1 if start == "auto" else 0)} of {n_stops + 1} plays. Ask: what moves next?\n:::\n:::\n')
    return "```{=html}\n" + html + "\n```\n\n" + "\n".join(cues)


qmd = f"""---
title: "Segmentation prototype"
format: lecturekit-revealjs
resources: [assets/**, lk-seg.js, lk-seg.css]
include-in-header:
  - text: '<link rel="stylesheet" href="lk-seg.css"><script src="lk-seg.js"></script>'
---

## Before {{role=example}}

A slide before the clip.

## Clip in parts {{role=example time=2}}

{seg("k30")}

::: notes
Slide notes: the clip runs in four parts.
:::

## After {{role=example}}

::: {{.live-only}}
::: {{.movie src="assets/clips/k30.mp4" label="ordinary clip"}}
:::
:::

## Stack {{role=example}}

:::::: {{.live-only}}
::::: {{.r-stack}}
:::: {{.movie src="assets/clips/g30.mp4" label="stack a"}}
::::

:::: {{.fragment}}
::: {{.movie src="assets/clips/k60.mp4" label="stack b"}}
:::
::::
:::::
::::::

## Mid-GOP clip {{role=example}}

{seg("g30")}

## Key start {{role=example}}

{seg("k60", start="key")}

## End {{role=example}}

The end.
"""
Path("slides.qmd").write_text(qmd)
print("wrote slides.qmd")
