"""Check a deck's manim8 clip entries against the manifests of the jobs that made them.

    python .github/scripts/check_clip_index.py examples/features tuning_sweep [--mode dark]

For each named clip, the entry in the preset's clips.json is compared with the manifest of the job it records
(found under the project's renders/ by the job id):

- the delivered video is the job's full movie remuxed with its index first: the same coded frames as
  result.videos[0] (whose sha256 is the manifest's), the moov box before the mdat, the entry's sha256 its own, and
  its size, frame rate, duration and frame count equal the movie's;
- revision is job.revision_id, job.id and job.cache_key are the job's, source is relative to the deck;
- every checkpoint of the job is copied byte for byte, and each one's frame in the copied video differs from its
  PNG by a mean of at most 1.0 grey level;
- the still is one of the checkpoints, and no value in the entry is null;
- the entry is format 2: its stops are the manifest's result.stops (id, frame, label), in order, each still the
  stop's frame of the delivered video and within a mean of 1.0 of the checkpoint PNG, with at least 3 frames of
  rest before it; the poster is frame 0 and the end the last frame.

Exit 0 when every check holds, 1 otherwise. Needs ffmpeg and ffprobe (or imageio-ffmpeg) and Pillow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def frame_count(video: Path) -> int:
    """Decoded frames, counted by ffmpeg itself (ffprobe is not always beside imageio-ffmpeg's binary)."""
    r = subprocess.run([ffmpeg(), "-v", "error", "-i", str(video), "-map", "0:v:0", "-f", "null", "-",
                        "-progress", "pipe:1"], capture_output=True, text=True, check=True)
    frames = [line.split("=", 1)[1] for line in r.stdout.splitlines() if line.startswith("frame=")]
    return int(frames[-1])


def packets(video: Path) -> list[str]:
    """The hash of every coded frame of the video stream, in order: equal for a remux by stream copy."""
    r = subprocess.run([ffmpeg(), "-v", "error", "-i", str(video), "-map", "0:v:0", "-c", "copy", "-f", "framemd5",
                        "-"], capture_output=True, text=True, check=True)
    return [line.rsplit(",", 1)[-1].strip() for line in r.stdout.splitlines() if line and not line.startswith("#")]


def top_boxes(video: Path) -> list[str]:
    """The top-level boxes of an MP4, in file order."""
    names, data = [], video.read_bytes()
    at = 0
    while at + 8 <= len(data):
        size = int.from_bytes(data[at:at + 4], "big")
        names.append(data[at + 4:at + 8].decode("latin-1"))
        if size == 1:
            size = int.from_bytes(data[at + 8:at + 16], "big")
        if size < 8:
            break
        at += size
    return names


def png_difference(a_path: Path, b_path: Path) -> float:
    from PIL import Image, ImageChops, ImageStat
    a = Image.open(a_path).convert("RGB")
    b = Image.open(b_path).convert("RGB")
    if a.size != b.size:
        return float("inf")
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


def frame_difference(video: Path, index: int, png: Path) -> float:
    """Mean absolute difference, in grey levels over all channels, between frame `index` of `video` and `png`."""
    from PIL import Image, ImageChops, ImageStat
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "frame.png"
        subprocess.run([ffmpeg(), "-v", "error", "-y", "-i", str(video), "-vf", f"select=eq(n\\,{index})",
                        "-frames:v", "1", str(out)], check=True)
        if not out.exists():
            return float("inf")                     # the video has no such frame
        a = Image.open(out).convert("RGB")
        b = Image.open(png).convert("RGB")
        if a.size != b.size:
            return float("inf")
        return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


def nulls(value, where: str = "") -> list[str]:
    if value is None:
        return [where or "(entry)"]
    if isinstance(value, dict):
        return [n for k, v in value.items() for n in nulls(v, f"{where}.{k}" if where else k)]
    return []


def check(deck: Path, name: str, mode: str) -> list[str]:
    index_file = deck / "assets" / "clips" / ("dark/clips.json" if mode == "dark" else "clips.json")
    index = json.loads(index_file.read_text(encoding="utf-8"))
    entry = index.get(name)
    if entry is None:
        return [f"{name} is not in {index_file}"]
    problems = [f"{name}: {where} is null" for where in nulls(entry)]
    if entry.get("producer") != "manim8":
        return problems + [f"{name}: producer is {entry.get('producer')!r}, not 'manim8'"]
    source = Path(entry["source"])
    if source.is_absolute() or ".." in source.parts:
        problems.append(f"{name}: source {source} is not relative to the deck")
    project = deck / source
    job = entry.get("job") or {}
    found = sorted((project / "renders").rglob(f"{job.get('id')}/manifest.json"))
    if not found:
        return problems + [f"{name}: no manifest for job {job.get('id')} under {project / 'renders'}"]
    manifest = json.loads(found[0].read_text(encoding="utf-8"))
    mjob, result = manifest["job"], manifest["result"]
    movie = result["videos"][0]
    video = deck / entry["video"]

    def same(what: str, ours, theirs) -> None:
        if ours != theirs:
            problems.append(f"{name}: {what} is {ours!r}, the manifest says {theirs!r}")

    rendered = project / movie["path"]
    if not rendered.exists():
        problems.append(f"{name}: the job's movie {rendered} is missing")
    else:
        same("the rendered movie's sha256", sha256(rendered), movie["sha256"])
        if packets(video) != packets(rendered):
            problems.append(f"{name}: {entry['video']} does not hold the coded frames of the job's movie (a remux by "
                            "stream copy keeps them)")
    same("the entry's sha256", entry.get("sha256"), sha256(video))
    boxes = top_boxes(video)
    if "moov" not in boxes or "mdat" not in boxes or boxes.index("moov") > boxes.index("mdat"):
        problems.append(f"{name}: {entry['video']} has its boxes in the order {boxes}; the index (moov) comes first")
    same("width", entry.get("width"), movie["width_px"])
    same("height", entry.get("height"), movie["height_px"])
    same("fps", entry.get("fps"), movie["fps"])
    same("duration", entry.get("duration"), movie["duration_seconds"])
    same("duration (the full movie, not a section)", entry.get("duration"), mjob["output"]["duration_seconds"])
    same("the video's frame count", frame_count(video), movie["frame_count"])
    same("revision", entry.get("revision"), mjob["revision_id"])
    same("job.id", job.get("id"), mjob["job_id"])
    same("job.cache_key", job.get("cache_key"), mjob["cache_key"])
    style = mjob.get("resolved_style") or {}
    if job.get("style"):
        same("job.style", job["style"], f"{style.get('theme')}@{style.get('theme_version')}")
    copied = entry.get("checkpoints") or {}
    same("the checkpoint ids", sorted(copied), sorted(c["snapshot_id"] for c in result["checkpoints"]))
    for cp in result["checkpoints"]:
        ours = copied.get(cp["snapshot_id"])
        if not ours:
            continue
        same(f"checkpoint {cp['snapshot_id']}'s sha256", sha256(deck / ours), cp["sha256"])
        if cp.get("renderer_time_seconds") is not None:
            at = round(cp["renderer_time_seconds"] * movie["fps"])
            diff = frame_difference(video, at, deck / ours)
            if diff > 1.0:
                problems.append(f"{name}: frame {at} of the video differs from checkpoint {cp['snapshot_id']} "
                                f"by {diff:.2f} grey levels on average (at most 1.0)")
    if entry.get("still") not in copied.values():
        problems.append(f"{name}: the still {entry.get('still')} is not one of the checkpoints")
    # format 2: the stops are manim8's, each still the frame it names
    same("format", entry.get("format"), 2)
    same("frames", entry.get("frames"), movie["frame_count"])
    ours_stops = [(s.get("id"), s.get("frame"), s.get("label")) for s in entry.get("stops") or []]
    same("the stops", ours_stops, [(s["snapshot_id"], s["frame_index"], s["label"]) for s in result.get("stops") or []])
    by_id = {c["snapshot_id"]: c for c in result["checkpoints"]}
    bounds = [(0, entry.get("poster"))] + [(s.get("frame"), s.get("still")) for s in entry.get("stops") or []]
    end = entry.get("end") or {}
    same("the end frame", end.get("frame"), movie["frame_count"] - 1)
    bounds.append((end.get("frame"), end.get("still")))
    for frame, still in bounds:
        if not still or not (deck / still).exists():
            problems.append(f"{name}: the still of frame {frame} ({still}) is missing")
            continue
        diff = frame_difference(video, frame, deck / still)
        if diff > 0.0:
            problems.append(f"{name}: {still} is not frame {frame} of the video (mean difference {diff:.3f})")
    for s in entry.get("stops") or []:
        if abs(s.get("pts", -1) - s["frame"] / movie["fps"]) > 1e-3:
            problems.append(f"{name}: stop {s['id']}'s pts {s.get('pts')} is not frame {s['frame']} at {movie['fps']} fps")
        if s.get("rest_before", 0) < 3:
            problems.append(f"{name}: stop {s['id']} has {s.get('rest_before')} frames of rest before it (a deck needs 3)")
        png = by_id.get(s["id"], {}).get("png")
        if png and (project / png).exists() and (deck / s["still"]).exists():
            diff = png_difference(deck / s["still"], project / png)
            if diff > 1.0:
                problems.append(f"{name}: stop {s['id']}'s still differs from manim8's checkpoint by {diff:.2f}")
    if not problems:
        print(f"ok {name} ({mode}): {entry['video']} is job {mjob['job_id']}'s full movie remuxed, "
              f"{movie['duration_seconds']} s, {movie['frame_count']} frames, sha256 {movie['sha256'][:12]}..., "
              f"revision {mjob['revision_id']}, {len(copied)} checkpoints, still {entry['still']}, "
              f"stops {', '.join(f'{i}@{f}' for i, f, _ in ours_stops) or 'none'}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("deck", type=Path)
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--mode", choices=("light", "dark"), default="light")
    a = ap.parse_args(argv)
    problems = [p for name in a.clips for p in check(a.deck, name, a.mode)]
    for p in problems:
        print(f"error: {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
