"""The feature deck's stand-in clip, drawn in each preset's colours.

    python examples/features/make_clips.py

A bar in the concept colour sweeps across a disc outlined in the hairline colour, on the slide colour: 960 by 540,
30 frames per second, 1.5 s. It stands in for a real clip on the slides that exercise the movie forms (src=, clip=,
a clip on a key press, a sequence, a still from a checkpoint); slide 10's manim8 clip is the real one. Each preset
gets its own render from its brand file, so the dark build plays a dark clip:

    assets/clips/       bar_bold.mp4, bar_back.mp4 (the same clip reversed), their stills (the last frame), and
                        bar_bold.midway.png (the frame at 0.75 s, the clip= slide's checkpoint still), from _brand.yml
    assets/clips/dark/  the same files from _brand-dark.yml

and the entry `bar_bold` in each preset's clips.json. Needs Pillow, ffmpeg (or imageio-ffmpeg) and lecturekit.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from lecturekit.theme import load_brand

HERE = Path(__file__).resolve().parent
W, H, FPS, FRAMES = 960, 540, 30, 45          # 1.5 s
CX, CY, R = 480, 270, 200                     # the disc
BAR_W, BAR_H = 50, 420
MIDWAY = 0.75                                 # seconds: the checkpoint still


def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def frame(i: int, colours: dict[str, str]) -> Image.Image:
    img = Image.new("RGB", (W, H), colours["slide"])
    d = ImageDraw.Draw(img)
    d.ellipse([CX - R, CY - R, CX + R, CY + R], outline=colours["hairline"], width=3)
    # the bar's centre moves from the disc's left edge to its right edge over the clip
    x = CX - R + 2 * R * i / (FRAMES - 1)
    d.rectangle([round(x - BAR_W / 2), CY - BAR_H // 2, round(x + BAR_W / 2), CY + BAR_H // 2], fill=colours["concept"])
    return img


def encode(frames: list[Image.Image], path: Path) -> None:
    cmd = [ffmpeg(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", str(path)]
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


def main() -> int:
    make("_brand.yml", "light", "")
    make("_brand-dark.yml", "dark", "dark")
    return 0


if __name__ == "__main__":
    sys.exit(main())
