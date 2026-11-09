"""Barcode test clips for the segmentation prototype.

Each frame carries its own index as 10 black/white blocks across the top band, so the frame a browser shows can be
read back from pixels. The picture below the band holds still during "rests" around each stop (like a manim8 static
play) and moves otherwise, so rests are real but the barcode still identifies every frame.

Variants:
  k30.mp4   30 fps, 12 s, keyframes forced at 0 and every stop (manim8-like), faststart
  g30.mp4   30 fps, 12 s, x264 GOP 250, no keyframe at the stops, moov at the end (external worst case)
  k60.mp4   60 fps, 12 s, keyframes forced at stops, faststart
Stills: <variant>.f<frame>.png extracted by frame number (select=eq(n,K)).
"""
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/clips")
OUT.mkdir(parents=True, exist_ok=True)
W, H, BITS, BLK = 640, 360, 10, 56
STOP_S = [3.0, 6.0, 9.0]   # stops in seconds; frames depend on fps
REST_S = 0.5               # picture is static for REST_S before and after each stop


def frame_image(n, fps, total):
    t = n / fps
    img = Image.new("RGB", (W, H), (235, 238, 242))
    d = ImageDraw.Draw(img)
    for b in range(BITS):  # barcode: bit b of n, MSB first
        on = (n >> (BITS - 1 - b)) & 1
        x0 = 20 + b * (BLK + 4)
        d.rectangle([x0, 8, x0 + BLK, 8 + BLK], fill=(255, 255, 255) if on else (0, 0, 0))
    # picture: a dot that moves along x, frozen inside rests
    tt = t
    for s in STOP_S:
        if abs(t - s) <= REST_S:
            tt = s
    x = 40 + (W - 80) * (tt / (total / fps))
    d.ellipse([x - 22, 200 - 22, x + 22, 200 + 22], fill=(78, 134, 198))
    d.text((20, 300), f"frame {n}", fill=(34, 48, 74))
    return img


def make(name, fps, seconds, gop=None, faststart=True):
    total = int(round(fps * seconds))
    stops = [int(round(s * fps)) for s in STOP_S]
    path = OUT / f"{name}.mp4"
    args = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
            "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18"]
    if gop:
        args += ["-g", str(gop), "-sc_threshold", "0"]
    else:
        args += ["-force_key_frames", "expr:" + "+".join(f"eq(n,{k})" for k in [0] + stops)]
    if faststart:
        args += ["-movflags", "+faststart"]
    args += [str(path)]
    p = subprocess.Popen(args, stdin=subprocess.PIPE)
    for n in range(total):
        p.stdin.write(frame_image(n, fps, total).tobytes())
    p.stdin.close(); p.wait()
    bounds = [0] + stops + [total - 1]
    for k in bounds:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-vf", f"select=eq(n\\,{k})",
                        "-vsync", "0", "-frames:v", "1", str(OUT / f"{name}.f{k}.png")], check=True)
    pts = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "frame=pts_time,key_frame", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout.split()
    rows = [tuple(r.split(",")[:2]) for r in pts]
    key = [i for i, (k, _) in enumerate(rows) if k == "1"]
    return {"video": str(path), "fps": fps, "frames": total,
            "bounds": [{"f": k, "t": float(rows[k][1])} for k in bounds],
            "keyframes": key}


meta = {"k30": make("k30", 30, 12), "g30": make("g30", 30, 12, gop=250, faststart=False),
        "k60": make("k60", 60, 12)}
(OUT / "meta.json").write_text(json.dumps(meta, indent=1))
for k, v in meta.items():
    print(k, v["frames"], "frames, bounds", [b["f"] for b in v["bounds"]], "keyframes", v["keyframes"][:8])
