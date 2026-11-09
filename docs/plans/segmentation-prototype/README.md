# Segmentation prototype

This is a prototype of the runtime that holds one clip at stops on key presses. Section 3 of
`../animation-integration.md` gives the design. It is a design study, not engine code: nothing in the extension
loads these files.

## Files

| File | What it is |
| --- | --- |
| `gen_clips.py` | Writes the barcode test clips. Every frame carries its own index as ten black and white blocks, and the picture rests for 0.5 s on each side of the stops at 3, 6 and 9 s. There are three encodings: `k30` (keyframes at the stops, faststart), `g30` (GOP 250 with moov at the end, the layout manim8 writes) and `k60` (60 fps). It also writes a still for each boundary, extracted by frame number. |
| `build_deck.py` | Writes `slides.qmd`. The deck holds the markup the filter would emit for a segmented clip, an ordinary clip, the r-stack of finding I9, a mid-GOP clip and a `start=key` clip. |
| `lk-seg.js`, `lk-seg.css` | The runtime: the state machine, the keys bound through `Reveal.configure`, the still that covers each seek, the deck-wide guard, the speaker relay and the Blob fallback. |
| `live-head.patch` | Makes the extension's capture-phase Space, R and click handlers skip segmented clips. The real change removes that listener. |
| `rangeserver.py` | A static server that answers HTTP Range requests. |
| `run_proto.py` | The main driver: real key presses forward and back, a backward entry, exact-frame reads from the canvas and from screenshots, the receiver, and print. |
| `run_speaker.py`, `run_stress.py`, `run_events.py`, `run_notes.py` | The speaker popup, random key mashing, the order of Reveal's events, and the notes after a backward entry. |

## Running it

```sh
cp -r ../../../_extensions .                   # a copy of the extension beside the deck
patch -p0 < live-head.patch
python gen_clips.py assets/clips               # needs ffmpeg and Pillow
python build_deck.py
quarto render slides.qmd --to lecturekit-revealjs
python run_proto.py range 2                    # or: norange 2; a third argument norvfc forces the timeupdate path
```

`LK_CHROME` names a Chromium binary; without it, Playwright's own Chromium is used. The engine's venv has
Playwright.

## What it showed

These results come from Chromium 1243 (headless) with Quarto 1.11.9 and reveal.js 5.1.0. They were re-run from this
copy on 9 November 2026.

- `run_proto.py` passes 52 of 52 checks both with and without Range support. The speaker driver passes 9 of 9, and
  so does the stress driver.
- **Exact holds.** Pausing and then setting `currentTime` to the middle of the stop frame holds exactly that frame.
  This is true forward and backward, mid-GOP, and with moov at the end.
- **Pause timing.** With `requestVideoFrameCallback` and a two-frame guard, the pause lands one to two frames
  *before* a stop. The `timeupdate` fallback pauses 75 to 290 ms early. Rests therefore belong before a stop.
- **Backward entry and preview windows.** A keyboard backward entry fires only `slidechanged`, with every cue
  already visible. The runtime holds the final frame and never plays. The speaker previews never load the clip.

Not tested: Firefox, WebKit, `file://`, `quarto preview`, 1080p clips, a hidden tab and the degraded path.
