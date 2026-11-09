"""The feature deck's stand-in clip, drawn in each preset's colours.

    python examples/features/make_clips.py

A bar in the concept colour sweeps across a disc outlined in the hairline colour, on the slide colour: 960 by 540,
30 frames per second, 1.5 s. It stands in for a real clip on the slides that exercise the movie forms (src=, clip=,
a clip on a key press, a sequence, a still from a checkpoint); the manim8 clip is the real one. Each preset gets
its own render from its brand file, so the dark build plays a dark clip:

    assets/clips/       bar_bold.mp4, bar_back.mp4 (the same clip reversed), their stills (the last frame), and
                        bar_bold.midway.png (the frame at 0.75 s, the clip= slide's checkpoint still), from _brand.yml
    assets/clips/dark/  the same files from _brand-dark.yml

and the entry `bar_bold` in each preset's clips.json.

A second stand-in, `bar_steps`, is a clip in parts: the same bar crosses the disc in four moves and rests at
three positions on the way, 0.6 s still before and after each (6.5 s). It is rendered to a temporary file and
brought in as an external MP4 is, through `lk clips adopt` (lecturekit.clips.adopt) with its three stops, `left`,
`centre` and `right`, at 1.4, 3.2 and 5.0 s; adopt copies it into each preset's clips folder with its index first,
writes the stills of frame 0, of each stop and of the end, measures the rests on the pixels and writes a format 2
entry. Needs Pillow, ffmpeg (or imageio-ffmpeg) and lecturekit.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from lecturekit.clips import adopt
from lecturekit.theme import load_brand

HERE = Path(__file__).resolve().parent
W, H, FPS, FRAMES = 960, 540, 30, 45          # 1.5 s
CX, CY, R = 480, 270, 200                     # the disc
BAR_W, BAR_H = 50, 420
MIDWAY = 0.75                                 # seconds: the checkpoint still

# bar_steps, in frames at 30 fps: a still lead, then four eased moves of 0.6 s across the disc with a rest of
# 1.2 s between them, each stop in the middle of its rest (0.6 s still before it and after it), and a short end
STEP_LEAD, STEP_MOVE, STEP_REST, STEP_END = 6, 18, 36, 9
STEP_STOPS = [("left", "left of centre"), ("centre", "at the centre"), ("right", "right of centre")]


def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def bar_at(x: float, colours: dict[str, str]) -> Image.Image:
    img = Image.new("RGB", (W, H), colours["slide"])
    d = ImageDraw.Draw(img)
    d.ellipse([CX - R, CY - R, CX + R, CY + R], outline=colours["hairline"], width=3)
    d.rectangle([round(x - BAR_W / 2), CY - BAR_H // 2, round(x + BAR_W / 2), CY + BAR_H // 2], fill=colours["concept"])
    return img


def frame(i: int, colours: dict[str, str]) -> Image.Image:
    # the bar's centre moves from the disc's left edge to its right edge over the clip
    return bar_at(CX - R + 2 * R * i / (FRAMES - 1), colours)


def step_positions() -> tuple[list[float], list[int]]:
    """bar_steps: the bar's centre in every frame, and the frames of its three stops."""
    xs = [CX - R + 2 * R * k / 4 for k in range(5)]          # the edges of the disc and three positions between
    out, stops = [xs[0]] * STEP_LEAD, []
    for k in range(4):
        for i in range(STEP_MOVE):
            t = (i + 1) / STEP_MOVE
            out.append(xs[k] + (xs[k + 1] - xs[k]) * t * t * (3 - 2 * t))   # eased in and out
        if k < 3:
            stops.append(len(out) + STEP_REST // 2)
            out.extend([xs[k + 1]] * STEP_REST)
    out.extend([xs[4]] * STEP_END)
    return out, stops


def encode(frames: list[Image.Image], path: Path, keyframes: list[int] = ()) -> None:
    keys = ["-force_key_frames", "expr:" + "+".join(f"eq(n,{k})" for k in [0, *keyframes])] if keyframes else []
    cmd = [ffmpeg(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", *keys, "-movflags", "+faststart",
           str(path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    for f in frames:
        proc.stdin.write(f.tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit(f"ffmpeg failed writing {path}")


def make(brand: str, mode: str, sub: str) -> None:
    colours = dict(load_brand(HERE / brand, mode=mode).colors)
    out = HERE / "assets" / "clips" / sub
    out.mkdir(parents=True, exist_ok=True)
    frames = [frame(i, colours) for i in range(FRAMES)]
    encode(frames, out / "bar_bold.mp4")
    encode(frames[::-1], out / "bar_back.mp4")
    frames[-1].save(out / "bar_bold.png")
    frames[0].save(out / "bar_back.png")          # the reversed clip ends where the forward one starts
    frames[round(MIDWAY * FPS)].save(out / "bar_bold.midway.png")
    rel = "assets/clips/" + (sub + "/" if sub else "")
    index_path = out / "clips.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    index["bar_bold"] = {
        "checkpoints": {"midway": rel + "bar_bold.midway.png"},
        "duration": FRAMES / FPS,
        "fps": float(FPS),
        "height": H,
        "producer": "external",
        "revision": "make_clips.py",
        "source": "make_clips.py (synthetic stand-in)",
        "still": rel + "bar_bold.png",
        "video": rel + "bar_bold.mp4",
        "width": W,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(HERE)}: bar_bold.mp4, bar_back.mp4 and stills ({mode}: slide {colours['slide']})")
    # the clip in parts, adopted as an MP4 made elsewhere is; the stops are seconds of the video
    xs, stops = step_positions()
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "bar_steps.mp4"
        encode([bar_at(x, colours) for x in xs], src, keyframes=stops)
        rec = adopt(HERE, src, "bar_steps", stops=[f"{sid}={k / FPS:g}" for (sid, _), k in zip(STEP_STOPS, stops)],
                    labels=[label for _, label in STEP_STOPS], mode=mode)
    print(f"adopted {rec.video}: {rec.frames} frames, stops "
          + ", ".join(f"{s['id']} at frame {s['frame']} ({s['rest_before']} still before)" for s in rec.stops))


def main() -> int:
    make("_brand.yml", "light", "")
    make("_brand-dark.yml", "dark", "dark")
    return 0


if __name__ == "__main__":
    sys.exit(main())
