"""The clip index's format 2: what `lk clips` writes so that a deck can hold one clip at a frame.

Three producers, one entry shape: `lk clips adopt` for an MP4 made elsewhere, kit scenes with `checkpoint()` (Manim
sections, summed), manim8 projects (`result.stops` of the render manifest, here a recorded manifest with a
hand-made `result.stops`). The oracle is a barcode clip: every frame carries its own index in ten black and white
blocks, so a still can be read back as the frame it is. Needs ffmpeg and Pillow; the real Manim render at the end
runs where Manim is installed.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from lecturekit import clips
from lecturekit.cli import main as lk

PIL = pytest.importorskip("PIL")
from PIL import Image, ImageDraw  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "manim8"
pytestmark = pytest.mark.skipif(clips._ffmpeg() is None, reason="ffmpeg not installed")

W, H, BITS = 320, 180, 10


# ---------------------------------------------------------------- clips to test with
def write_video(path: Path, frames, fps: int, *args: str) -> Path:
    """Encode PIL frames as H.264 (yuv420p), with extra ffmpeg output options."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = list(frames)
    w, h = frames[0].size
    p = subprocess.Popen([clips._ffmpeg(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                          "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", *args, str(path)],
                         stdin=subprocess.PIPE)
    for im in frames:
        p.stdin.write(im.convert("RGB").tobytes())
    p.stdin.close()
    assert p.wait() == 0
    return path


def barcode_frame(n: int, dot: float) -> Image.Image:
    """Frame n: its index as ten blocks across the top (most significant first), a dot at `dot` (0 to 1) below."""
    im = Image.new("RGB", (W, H), (235, 238, 242))
    d = ImageDraw.Draw(im)
    for b in range(BITS):
        on = (n >> (BITS - 1 - b)) & 1
        x0 = 8 + b * 30
        d.rectangle([x0, 6, x0 + 26, 32], fill=(255, 255, 255) if on else (0, 0, 0))
    x = 20 + (W - 40) * dot
    d.ellipse([x - 12, 110 - 12, x + 12, 110 + 12], fill=(78, 134, 198))
    return im


def read_barcode(png: Path) -> int:
    with Image.open(png) as im:
        g = im.convert("L")
        s = g.width / W
        n = 0
        for b in range(BITS):
            n = n * 2 + (1 if g.getpixel((int((8 + b * 30 + 13) * s), int(19 * s))) > 128 else 0)
        return n


def barcode_clip(path: Path, fps: int = 30, seconds: int = 6, stops=(2.0, 4.0), rest: float = 0.5, args=()):
    """The prototype's oracle, small: the dot holds still within `rest` of each stop; the barcode never does."""
    total = fps * seconds

    def dot(n):
        t = n / fps
        for s in stops:
            if abs(t - s) <= rest:
                t = s
        return t / seconds

    return write_video(path, (barcode_frame(n, dot(n)) for n in range(total)), fps, *args)


def rest_clip(path: Path, frames: int = 150, stops=(50, 100), rest: int = 15) -> Path:
    """No barcode: a square that moves one step a frame, except that frames k-rest .. k+rest show frame k's
    picture for each stop k. Encoded losslessly, so a picture that holds decodes to the same pixels."""
    def pos(n):
        for k in stops:
            if abs(n - k) <= rest:
                return k
        return n

    def frame(n):
        im = Image.new("RGB", (160, 90), (255, 255, 255))
        p = pos(n)
        x, y = 4 + (p % 50) * 3, 10 + (p // 50) * 25
        ImageDraw.Draw(im).rectangle([x, y, x + 12, y + 12], fill=(20, 40, 60))
        return im

    return write_video(path, (frame(n) for n in range(frames)), 30, "-qp", "0")


def atoms(path: Path) -> list[str]:
    """The top-level boxes of an MP4, in file order."""
    data, out, i = Path(path).read_bytes(), [], 0
    while i + 8 <= len(data):
        size, kind = struct.unpack(">I4s", data[i:i + 8])
        if size == 1:
            size = struct.unpack(">Q", data[i + 8:i + 16])[0]
        out.append(kind.decode("latin-1"))
        i += size or len(data)
    return out


def framemd5(path: Path) -> list[str]:
    out = subprocess.run([clips._ffmpeg(), "-v", "error", "-i", str(path), "-map", "0:v:0", "-f", "framemd5", "-"],
                         capture_output=True, text=True, check=True).stdout
    return [line.rsplit(",", 1)[-1].strip() for line in out.splitlines() if line and not line.startswith("#")]


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def no_nulls(obj) -> bool:
    if isinstance(obj, dict):
        return all(v is not None and no_nulls(v) for v in obj.values())
    if isinstance(obj, list):
        return all(v is not None and no_nulls(v) for v in obj)
    return True


def make_deck(tmp_path: Path) -> Path:
    deck = tmp_path / "deck"
    deck.mkdir()
    (deck / "_quarto.yml").write_text("project:\n  type: default\n")
    return deck


def saved(deck: Path, mode: str = "light") -> dict:
    return json.loads(clips.index_path(deck, mode).read_text())


# ---------------------------------------------------------------- decoding
def test_frame_table_counts_by_decoding_with_or_without_ffprobe(tmp_path, monkeypatch):
    mp4 = barcode_clip(tmp_path / "b.mp4", seconds=2, stops=(1.0,))
    with_probe = clips.frame_table(mp4)
    assert (with_probe.frames, with_probe.fps, with_probe.width, with_probe.height) == (60, 30.0, W, H)
    assert with_probe.pts[:3] == [0.0, 0.033333, 0.066667] and with_probe.keys[0]
    assert with_probe.nearest(1.0) == 30 and with_probe.nearest(1.01) == 30 and with_probe.nearest(99) == 59
    monkeypatch.setattr(clips, "_ffprobe", lambda: None)               # imageio-ffmpeg ships no ffprobe
    showinfo = clips.frame_table(mp4)
    assert (showinfo.frames, showinfo.fps, showinfo.width, showinfo.height) == (60, 30.0, W, H)
    assert showinfo.pts == with_probe.pts and showinfo.keys == with_probe.keys


def test_frames_are_extracted_by_number(tmp_path):
    mp4 = barcode_clip(tmp_path / "b.mp4", seconds=2, stops=(1.0,), args=("-g", "250"))
    outs = [tmp_path / f"x{i}.png" for i in range(4)]
    clips.extract_frames(mp4, [37, 0, 59, 37], outs)                    # any order, repeats allowed
    assert [read_barcode(p) for p in outs] == [37, 0, 59, 37]
    with pytest.raises(clips.ClipError, match="no frame 60"):
        clips.extract_frames(mp4, [5, 60], [tmp_path / "a.png", tmp_path / "b.png"])


def test_rests_are_frames_of_unchanged_picture(tmp_path):
    mp4 = rest_clip(tmp_path / "r.mp4")
    table = clips.frame_table(mp4)
    size, lumas = clips.luma_frames(mp4, table)
    assert len(lumas) == table.frames == 150
    assert clips.rests(lumas, size, 50) == (15, 15) and clips.rests(lumas, size, 100) == (15, 15)
    # frame 40 is inside the hold around frame 50 (35 to 65) and shows its picture: 5 frames before it, 25 after
    assert clips.rests(lumas, size, 40) == (5, 25)
    assert clips.rests(lumas, size, 20) == (0, 0)


def test_a_keyframe_in_a_rest_is_the_same_picture():
    # H.264 codes a keyframe in a still rest afresh: at 160 px wide it differs from the frames before it by up to
    # 5 grey levels on a few pixels (manim8's tuning_sweep), which is no change of picture; 9 levels is the tail of
    # an eased motion, which is
    size = (16, 9)
    base = bytes([128] * (16 * 9))
    noise = bytearray(base)
    noise[3] += 5
    noise[40] -= 4
    motion = bytearray(base)
    motion[70] += 9
    assert clips.same_picture(base, bytes(noise), size)
    assert not clips.same_picture(base, bytes(motion), size)


# ---------------------------------------------------------------- adopt
def test_adopt_writes_stills_that_are_the_frames_they_name(tmp_path, capsys):
    deck = make_deck(tmp_path)
    src = barcode_clip(tmp_path / "made" / "sweep.mp4",
                       args=("-force_key_frames", "expr:eq(n,0)+eq(n,60)+eq(n,120)"))
    rec = clips.adopt(deck, src, "sweep", stops=["lenient=2.0", "4.01"], labels=["lenient", "strict criterion"])
    entry = saved(deck)["sweep"]
    assert entry == rec.to_dict() and no_nulls(entry) and "null" not in clips.index_path(deck).read_text()
    assert (entry["format"], entry["producer"], entry["fps"], entry["frames"]) == (2, "external", 30.0, 180)
    assert (entry["width"], entry["height"], entry["duration"]) == (W, H, 6.0)
    assert entry["video"] == "assets/clips/sweep.mp4" and entry["sha256"] == sha256(deck / entry["video"])
    assert entry["source"] == "sweep.mp4" and entry["revision"] == clips.file_hash(src)   # outside the deck
    assert [(s["id"], s["frame"], s["pts"], s["label"]) for s in entry["stops"]] == [
        ("lenient", 60, 2.0, "lenient"), ("stop_2", 120, 4.0, "strict criterion")]   # 4.01 s snaps to frame 120
    assert entry["poster"] == "assets/clips/sweep.f0000.png" and read_barcode(deck / entry["poster"]) == 0
    for s in entry["stops"]:
        assert s["still"] == f"assets/clips/sweep.f{s['frame']:04d}.png"
        assert read_barcode(deck / s["still"]) == s["frame"]
        assert s["frozen"] == [] and "notes" not in s
        assert (s["rest_before"], s["rest_after"]) == (0, 0)            # the barcode changes on every frame
    assert entry["end"] == {"frame": 179, "pts": 5.966667, "still": "assets/clips/sweep.f0179.png"}
    assert read_barcode(deck / entry["end"]["still"]) == 179
    assert entry["still"] == "assets/clips/sweep.png" and read_barcode(deck / entry["still"]) == 179
    assert entry["checkpoints"] == {"lenient": "assets/clips/sweep.f0060.png", "stop_2": "assets/clips/sweep.f0120.png"}
    err = capsys.readouterr().err
    assert "stop lenient (frame 60) has 0 frames of unchanged picture before it; a deck refuses" in err
    assert "not a keyframe" not in err


def test_adopt_moves_the_index_first_by_stream_copy(tmp_path, capsys):
    deck = make_deck(tmp_path)
    src = barcode_clip(deck / "incoming" / "late.mp4", seconds=4, stops=(2.0,), args=("-g", "250", "-sc_threshold", "0"))
    assert atoms(src).index("moov") > atoms(src).index("mdat")          # moov last, as manim8 writes it
    clips.adopt(deck, src, "late", stops=["2"])
    entry = saved(deck)["late"]
    out = deck / entry["video"]
    assert atoms(out).index("moov") < atoms(out).index("mdat")
    assert framemd5(out) == framemd5(src)                               # every frame as it was
    assert entry["source"] == "incoming/late.mp4"                       # inside the deck: relative to it
    assert entry["stops"][0]["frame"] == 60 and read_barcode(deck / entry["stops"][0]["still"]) == 60
    assert "stop stop_1 (frame 60) is not a keyframe" in capsys.readouterr().err


def test_adopt_size_forces_a_keyframe_at_every_stop(tmp_path):
    deck = make_deck(tmp_path)
    src = barcode_clip(tmp_path / "g.mp4", args=("-g", "250", "-sc_threshold", "0"))
    assert [i for i, k in enumerate(clips.frame_table(src).keys) if k] == [0]
    clips.adopt(deck, src, "small", stops=["2", "4"], size="160x90", mode="dark")
    entry = saved(deck, "dark")["small"]
    assert entry["video"] == "assets/clips/dark/small.mp4" and not clips.index_path(deck).exists()
    table = clips.frame_table(deck / entry["video"])
    assert (table.width, table.height, table.frames) == (160, 90, 180) == (entry["width"], entry["height"], 180)
    assert {0, 60, 120} <= {i for i, k in enumerate(table.keys) if k}
    assert [read_barcode(deck / s["still"]) for s in entry["stops"]] == [60, 120]
    assert read_barcode(deck / entry["end"]["still"]) == 179


def test_rests_of_a_reencoded_clip_are_its_pictures(tmp_path):
    """A keyframe forced at a stop is coded afresh, a few levels away from the frames before it; the rest is the
    picture's, so it is measured on the frames the producer made."""
    deck = make_deck(tmp_path)
    src = rest_clip(tmp_path / "r.mp4")
    clips.adopt(deck, src, "held", stops=["a=1.6667", "b=3.3333"])
    clips.adopt(deck, src, "held_small", stops=["a=1.6667", "b=3.3333"], size="80x46")
    for name in ("held", "held_small"):
        stops = saved(deck)[name]["stops"]
        assert [(s["id"], s["frame"], s["rest_before"], s["rest_after"]) for s in stops] == [
            ("a", 50, 15, 15), ("b", 100, 15, 15)], name


@pytest.mark.parametrize("stops, labels, message", [
    (["0"], None, "at frame 0, the first frame"),
    (["5.9667"], None, "the last frame"),
    (["9"], None, "after the end of the video"),
    (["a=2", "b=2.01"], None, "both at frame 60"),
    (["2", "4"], ["one"], "1 label for 2 stops"),
    (["Bad=2"], None, "not a slug"),
    (["end=2"], None, "not a slug"),
    (["a=2", "a=4"], None, "used twice"),
    (["2"], ["x" * 41], "1 to 40 characters"),
    (["two seconds"], None, "a second of the video, or ID=SECONDS"),
])
def test_adopt_refuses_a_stop_no_deck_could_hold(tmp_path, stops, labels, message):
    deck = make_deck(tmp_path)
    src = barcode_clip(tmp_path / "b.mp4")
    with pytest.raises(clips.ClipError, match=message):
        clips.adopt(deck, src, "b", stops=stops, labels=labels)
    assert not (deck / "assets" / "clips" / "b.mp4").exists() and not clips.index_path(deck).exists()


def test_adopt_refuses_a_name_a_producer_renders(tmp_path):
    deck = make_deck(tmp_path)
    (deck / "anim").mkdir()
    (deck / "anim" / "clip_bar_bold.py").write_text("class BarBold(Scene):\n    pass\n")
    src = barcode_clip(tmp_path / "b.mp4", seconds=2, stops=(1.0,))
    with pytest.raises(clips.ClipError, match="is the kit clip anim/clip_bar_bold.py"):
        clips.adopt(deck, src, "bar_bold")
    with pytest.raises(clips.ClipError, match="a clip name is lower case"):
        clips.adopt(deck, src, "Bar Bold")


def test_adopt_again_replaces_the_stills(tmp_path):
    deck = make_deck(tmp_path)
    src = barcode_clip(tmp_path / "b.mp4")
    clips.adopt(deck, src, "b", stops=["2", "4"])
    clips.adopt(deck, src, "b", stops=["3"])
    names = sorted(p.name for p in (deck / "assets" / "clips").glob("b.f*.png"))
    assert names == ["b.f0000.png", "b.f0090.png", "b.f0179.png"]
    assert [s["frame"] for s in saved(deck)["b"]["stops"]] == [90]
    assert not [p for p in (deck / "assets" / "clips").iterdir() if p.name.startswith(".")]   # no staging left


def test_lk_clips_adopt(tmp_path, capsys):
    deck = make_deck(tmp_path)
    src = barcode_clip(tmp_path / "b.mp4")
    assert lk(["clips", "adopt", str(src), "--name", "b", "--deck", str(deck), "--stops", "first=2", "4",
               "--labels", "first", "second"]) == 0
    out = capsys.readouterr().out
    assert "b: 320x180, 180 frames at 30 fps; first at frame 60 (2 s, rest 0+0), stop_2 at frame 120" in out
    assert [s["label"] for s in saved(deck)["b"]["stops"]] == ["first", "second"]
    assert lk(["clips", "adopt", str(src), "--name", "c", "--deck", str(deck), "--stops", "0"]) == 1
    assert "lk clips adopt: stop stop_1 is at frame 0" in capsys.readouterr().err
    assert "c" not in saved(deck)


# ---------------------------------------------------------------- manim8: result.stops
def manim8_clip(tmp_path: Path, fixture: str = "manifest_stops.json") -> tuple[Path, Path, dict]:
    """A manim8 project's render as lecturekit finds it: the recorded manifest, and a small movie made to agree with
    it (the picture moves during the manifest's moving plays and holds during its static ones), the checkpoint
    PNGs taken from that movie at their frames."""
    deck = make_deck(tmp_path)
    clip_dir = deck / "clips" / "families" / "neuro" / "divisive_normalization"
    manifest = json.loads((FIXTURES / fixture).read_text())
    result = manifest["result"]
    fps = 30
    moving = [False] * 540
    for p in result["plays"]:
        first = round(p["start_seconds"] * fps)
        for n in range(first, first + p["frames"]):
            moving[n] = not p["static"]

    def frame(n):            # the square has moved once for every moving frame before this one
        p = sum(moving[:n])
        im = Image.new("RGB", (160, 90), (255, 255, 255))
        x, y = 4 + (p % 50) * 3, 4 + (p // 50) * 14
        ImageDraw.Draw(im).rectangle([x, y, x + 10, y + 10], fill=(23, 91, 142))
        return im

    v0 = result["videos"][0]
    movie = clip_dir / v0["path"]
    starts = sorted({round(p["start_seconds"] * fps) for p in result["plays"]})
    write_video(movie, (frame(n) for n in range(540)), fps, "-qp", "0",
                "-force_key_frames", "expr:" + "+".join(f"eq(n,{k})" for k in starts))   # a play starts a GOP
    v0.update(width_px=160, height_px=90, sha256=sha256(movie))
    for c in result["checkpoints"]:
        clips.extract_frames(movie, [c["frame_index"] if "frame_index" in c else
                                     round(c["expected_time_seconds"] * fps)], [clip_dir / c["png"]])
        c.update(width_px=160, height_px=90)
    return deck, clip_dir, manifest


def test_manim8_stops_come_from_result_stops(tmp_path, capsys):
    deck, clip_dir, manifest = manim8_clip(tmp_path)
    rec = clips.manim8_record(deck, clip_dir, manifest).to_dict()
    assert no_nulls(rec) and (rec["format"], rec["frames"], rec["fps"]) == (2, 540, 30.0)
    assert rec["sha256"] == sha256(deck / rec["video"])
    stops = {s["id"]: s for s in rec["stops"]}
    assert list(stops) == ["excitation_visible", "pool_raised"]                       # candidates, in time order
    ev, pr = stops["excitation_visible"], stops["pool_raised"]
    assert (ev["frame"], ev["pts"], ev["label"]) == (120, 4.0, "excitation alone")
    assert ev["notes"] == manifest["job"]["snapshots"]["excitation_visible"]["description"]
    assert (ev["rest_before"], ev["rest_after"]) == (34, 0)       # a moving play starts at the stop
    assert (pr["frame"], pr["pts"], pr["rest_before"], pr["rest_after"]) == (390, 13.0, 15, 15)
    for s in rec["stops"]:
        assert s["still"] == f"assets/clips/divisive_normalization.f{s['frame']:04d}.png" and s["frozen"] == []
        assert clips.mean_difference(deck / s["still"], deck / rec["checkpoints"][s["id"]]) == 0
    assert rec["poster"].endswith(".f0000.png") and rec["end"]["frame"] == 539
    assert rec["still"] == rec["checkpoints"]["rebalanced"]                           # the latest checkpoint
    assert len(rec["checkpoints"]) == 4
    err = capsys.readouterr().err
    assert "no play" not in err and "moves" not in err and "keyframe" not in err


def test_manim8_without_result_stops_has_no_candidates(tmp_path):
    deck, clip_dir, manifest = manim8_clip(tmp_path, "manifest_render.json")
    assert "stops" not in manifest["result"]
    rec = clips.manim8_record(deck, clip_dir, manifest).to_dict()
    assert rec["format"] == 2 and rec["stops"] == [] and rec["frames"] == 540
    assert len(rec["checkpoints"]) == 4                     # every snapshot is still a checkpoint for still=


def test_manim8_stop_off_its_time_is_refused(tmp_path):
    deck, clip_dir, manifest = manim8_clip(tmp_path)
    manifest["result"]["stops"][1]["frame_index"] = 391
    with pytest.raises(clips.ClipError, match=r"stop pool_raised: frame_index 391 is not its time, 13 s at 30 fps"):
        clips.manim8_record(deck, clip_dir, manifest)
    assert not (deck / "assets" / "clips").exists() or not list((deck / "assets" / "clips").glob("*.mp4"))


def test_manim8_still_that_is_not_its_checkpoint_is_refused(tmp_path):
    deck, clip_dir, manifest = manim8_clip(tmp_path)
    png = clip_dir / next(c["png"] for c in manifest["result"]["checkpoints"] if c["snapshot_id"] == "pool_raised")
    clips.extract_frames(clip_dir / manifest["result"]["videos"][0]["path"], [300], [png])   # a moving frame
    with pytest.raises(clips.ClipError, match="stop pool_raised: frame 390 of the movie is not the producer's picture"):
        clips.manim8_record(deck, clip_dir, manifest)
    assert not list((deck / "assets" / "clips").glob("divisive_normalization*"))       # nothing moved in


def test_manim8_frame_count_must_agree_when_there_are_stops(tmp_path, capsys):
    deck, clip_dir, manifest = manim8_clip(tmp_path)
    manifest["result"]["videos"][0]["frame_count"] = 541
    with pytest.raises(clips.ClipError, match="says the movie has 541 frames; decoding it gives 540"):
        clips.manim8_record(deck, clip_dir, manifest)
    manifest["result"].pop("stops")
    clips.manim8_record(deck, clip_dir, manifest)
    assert "says the movie has 541 frames" in capsys.readouterr().err


def test_manim8_warns_where_its_records_and_the_stop_disagree(tmp_path, capsys):
    deck, clip_dir, manifest = manim8_clip(tmp_path)
    plays = manifest["result"]["plays"]
    next(p for p in plays if round(p["start_seconds"] * 30) == 375)["static"] = False   # a draft: rest that moves
    manifest["result"]["stops"][0]["rest_before_frames"] = 40                         # more than the pixels hold
    clips.manim8_record(deck, clip_dir, manifest)
    err = capsys.readouterr().err
    assert "stop pool_raised: a play that moves (from frame 375) runs in the 15 frames of rest before it" in err
    assert "stop excitation_visible: the producer made 40 frames of rest before it, the pixels show 34" in err


def test_manim8_crop_keeps_the_frames_and_forces_keyframes(tmp_path):
    deck, clip_dir, manifest = manim8_clip(tmp_path)
    movie = clip_dir / manifest["result"]["videos"][0]["path"]
    manifest["result"]["plays"] = []                         # nothing to cross-check the plays with
    write_video(movie, (Image.open(clip_dir / manifest["result"]["checkpoints"][0]["png"]) for _ in range(540)), 30,
                "-g", "1000", "-sc_threshold", "0")          # one GOP, a still picture
    for c in manifest["result"]["checkpoints"]:
        clips.extract_frames(movie, [c["frame_index"]], [clip_dir / c["png"]])
    rec = clips.manim8_record(deck, clip_dir, manifest, crop=True).to_dict()
    table = clips.frame_table(deck / rec["video"])
    assert table.frames == 540 and (table.width, table.height) == (rec["width"], rec["height"]) != (160, 90)
    assert {0, 120, 390} <= {i for i, k in enumerate(table.keys) if k}
    assert [(s["rest_before"], s["rest_after"]) for s in rec["stops"]] == [(120, 419), (390, 149)]


# ---------------------------------------------------------------- kit: checkpoint() and the section sums
def load_checkpoint_module():
    """nmcheckpoint without the kit package, whose __init__ imports Manim."""
    path = ROOT / "src" / "lecturekit" / "manim" / "nmcheckpoint.py"
    spec = importlib.util.spec_from_file_location("nmcheckpoint_alone", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class StubScene:
    def __init__(self):
        self.calls = []

    def wait(self, t):
        self.calls.append(("wait", t))

    def next_section(self, name, section_type):
        self.calls.append(("section", name, section_type))


def test_checkpoint_waits_half_the_rest_on_each_side_of_its_section(tmp_path, monkeypatch):
    nm = load_checkpoint_module()
    assert nm.CHECKPOINT_SECTION == clips.CHECKPOINT_SECTION and nm.CHECKPOINTS_ENV == clips.CHECKPOINTS_ENV
    assert nm.STOP_ID.pattern == clips.STOP_ID.pattern and nm.RESERVED == clips.RESERVED_STOP_IDS
    side = tmp_path / "side.jsonl"
    monkeypatch.setenv(nm.CHECKPOINTS_ENV, str(side))
    scene = StubScene()
    nm.checkpoint(scene, "first_sweep", label="rightward sweep", rest=0.6)
    nm.checkpoint(scene, "second")
    assert scene.calls == [("wait", 0.3), ("section", "first_sweep", "lecturekit.checkpoint"), ("wait", 0.3),
                           ("section", "second", "lecturekit.checkpoint")]
    rows = [json.loads(line) for line in side.read_text().splitlines()]
    assert rows == [{"id": "first_sweep", "label": "rightward sweep", "rest": 0.6, "scene": "StubScene"},
                    {"id": "second", "rest": 0.0, "scene": "StubScene"}]


@pytest.mark.parametrize("args, message", [
    (("Sweep",), "not|slug"), (("end",), "slug"), (("a", "x" * 41), "1 to 40"), (("a", "two\nlines"), "one line"),
    (("a", None, -1), "negative"),
])
def test_checkpoint_refuses(args, message):
    nm = load_checkpoint_module()
    with pytest.raises(ValueError, match=message):
        nm.checkpoint(StubScene(), *args)


def test_checkpoint_twice_in_one_scene_is_refused():
    nm = load_checkpoint_module()
    scene = StubScene()
    nm.checkpoint(scene, "a")
    with pytest.raises(ValueError, match="set twice"):
        nm.checkpoint(scene, "a")


FAKE_MANIM = """import json, os, shutil, sys
from pathlib import Path
args = sys.argv[1:]
assert "--save_sections" in args, args
media, name = Path(args[args.index("--media_dir") + 1]), args[args.index("-o") + 1]
built = Path(os.environ["FAKE_BUILT"])
out = media / "videos" / "clip_sweep" / "720p30"
(out / "sections").mkdir(parents=True, exist_ok=True)
shutil.copy(built / "movie.mp4", out / f"{name}.mp4")
for f in (built / "sections").iterdir():
    shutil.copy(f, out / "sections" / (f"{name}.json" if f.suffix == ".json" else f.name))
side = os.environ.get("NM_CHECKPOINTS_FILE")
if side and (built / "calls.jsonl").exists():
    Path(side).write_text((built / "calls.jsonl").read_text())
"""


def kit_deck(tmp_path: Path, monkeypatch, sections, calls, still=None) -> Path:
    """A deck with one kit scene and a fake Manim that delivers a prebuilt render: the rest clip as the movie,
    cut into section files at the given boundaries, with Manim's sections index and the checkpoint calls."""
    deck = make_deck(tmp_path)
    (deck / "anim").mkdir()
    attr = f"    still = {still!r}\n" if still is not None else "    pass\n"
    (deck / "anim" / "clip_sweep.py").write_text(f"class Sweep(Scene):\n{attr}")
    built = tmp_path / "built"
    movie = rest_clip(built / "movie.mp4")
    (built / "sections").mkdir()
    index, first = [], 0
    for i, (sname, stype, nb) in enumerate(sections):
        video = f"sweep_{i:04d}_{sname}.mp4"
        subprocess.run([clips._ffmpeg(), "-y", "-v", "error", "-i", str(movie), "-vf",
                        f"select=between(n\\,{first}\\,{first + nb - 1}),setpts=N/30/TB", "-qp", "0",
                        *clips._passthrough(clips._ffmpeg()), str(built / "sections" / video)], check=True)
        index.append({"name": sname, "type": stype, "video": video, "nb_frames": str(nb)})
        first += nb
    (built / "sections" / "index.json").write_text(json.dumps(index))
    (built / "calls.jsonl").write_text("".join(json.dumps(c) + "\n" for c in calls))
    fake = tmp_path / "manim"
    fake.write_text(f"#!/bin/sh\nexec \"{sys.executable}\" \"{tmp_path / 'fake_manim.py'}\" \"$@\"\n")
    fake.chmod(0o755)
    (tmp_path / "fake_manim.py").write_text(FAKE_MANIM)
    monkeypatch.setattr(clips, "_manim_exe", lambda: str(fake))
    monkeypatch.setenv("FAKE_BUILT", str(built))
    return deck


def test_kit_stops_are_the_sums_of_manim_sections(tmp_path, monkeypatch):
    sections = [("autocreated", "default.normal", 50), ("first_sweep", "lecturekit.checkpoint", 30),
                ("unrelated", "default.normal", 20), ("second", "lecturekit.checkpoint", 50)]
    calls = [{"id": "first_sweep", "label": "rightward sweep", "rest": 1.0}, {"id": "second", "rest": 0.0}]
    deck = kit_deck(tmp_path, monkeypatch, sections, calls, still="first_sweep")
    index, failures = clips.run_clips(deck)
    assert failures == []
    rec = index["sweep"]
    assert (rec["format"], rec["producer"], rec["frames"]) == (2, "kit", 150)
    assert [(s["id"], s["frame"], s["label"], s["rest_before"], s["rest_after"]) for s in rec["stops"]] == [
        ("first_sweep", 50, "rightward sweep", 15, 15), ("second", 100, "second", 15, 15)]
    assert rec["checkpoints"] == {"first_sweep": "assets/clips/sweep.f0050.png", "second": "assets/clips/sweep.f0100.png"}
    assert (deck / rec["still"]).read_bytes() == (deck / "assets" / "clips" / "sweep.f0050.png").read_bytes()
    assert no_nulls(rec) and rec["sha256"] == sha256(deck / rec["video"])


def test_kit_scene_without_checkpoints_is_format_2_without_stops(tmp_path, monkeypatch):
    deck = kit_deck(tmp_path, monkeypatch, [("autocreated", "default.normal", 150)], [])
    index, failures = clips.run_clips(deck)
    assert failures == [] and index["sweep"]["stops"] == [] and index["sweep"]["frames"] == 150
    assert index["sweep"]["still"] == "assets/clips/sweep.png" and "checkpoints" not in index["sweep"]


@pytest.mark.parametrize("sections, calls, message", [
    ([("autocreated", "default.normal", 150)], [{"id": "lost", "rest": 0}],
     "checkpoint lost has no frames after it"),                   # Manim drops a section with no animation
    ([("autocreated", "default.normal", 60), ("a", "lecturekit.checkpoint", 60)], [{"id": "a", "rest": 0}],
     "sections add up to 120 frames, the movie has 150"),
    ([("a", "lecturekit.checkpoint", 150)], [{"id": "a", "rest": 0}], "checkpoint a is at the first frame"),
])
def test_kit_sections_that_disagree_with_the_movie_fail_the_clip(tmp_path, monkeypatch, sections, calls, message):
    deck = kit_deck(tmp_path, monkeypatch, sections, calls)
    index, failures = clips.run_clips(deck)
    assert len(failures) == 1 and message in failures[0].reason and "sweep" not in index


def test_kit_unknown_still_id(tmp_path, monkeypatch):
    deck = kit_deck(tmp_path, monkeypatch, [("autocreated", "default.normal", 50), ("a", "lecturekit.checkpoint", 100)],
                    [{"id": "a", "rest": 0}])
    _, failures = clips.run_clips(deck, stills=["sweep=nowhere"])
    assert len(failures) == 1 and "neither a second of the clip nor one of its checkpoints (a)" in failures[0].reason
    index, failures = clips.run_clips(deck, stills=["sweep=1.0"])
    assert failures == [] and (deck / index["sweep"]["still"]).exists()


# ---------------------------------------------------------------- a real render, where Manim is installed
def test_real_kit_render_with_two_checkpoints(tmp_path):
    pytest.importorskip("manim")
    if not clips._manim_exe():
        pytest.skip("no manim command beside this Python")
    deck = make_deck(tmp_path)
    shutil.copy(ROOT / "src" / "lecturekit" / "scaffold" / "templates" / "_brand.yml", deck / "_brand.yml")
    (deck / "anim").mkdir()
    (deck / "anim" / "kit.py").write_text("from lecturekit.manim import *\n")
    (deck / "anim" / "clip_sweep.py").write_text(
        "from kit import *\n\n\nclass Sweep(Scene):\n    def construct(self):\n"
        "        dot = Dot(LEFT * 4, radius=0.4, color=BLUE)\n        self.add(dot)\n"
        "        self.play(dot.animate.move_to(RIGHT * 2), run_time=1)\n"
        "        checkpoint(self, 'went_right', rest=0.6)\n"
        "        self.play(dot.animate.shift(UP * 2), run_time=1)\n"
        "        checkpoint(self, 'went_up', label='moved up', rest=0.6)\n"
        "        self.play(dot.animate.shift(LEFT * 3), run_time=1)\n")
    index, failures = clips.run_clips(deck)
    assert failures == [], failures
    rec = index["sweep"]
    sections = json.loads(next((deck / "anim" / "media").rglob("sections/sweep.json")).read_text())
    nb = [int(s["nb_frames"]) for s in sections]
    assert [s["frame"] for s in rec["stops"]] == [nb[0], nb[0] + nb[1]] and sum(nb) == rec["frames"]
    assert [s["label"] for s in rec["stops"]] == ["went right", "moved up"]
    assert all(s["rest_before"] >= 9 for s in rec["stops"])          # 0.3 s at 30 fps
    video = deck / rec["video"]
    for s in rec["stops"]:
        frame = tmp_path / f"decoded{s['frame']}.png"
        subprocess.run([clips._ffmpeg(), "-v", "error", "-i", str(video), "-vf", f"select=eq(n\\,{s['frame']})",
                        *clips._passthrough(clips._ffmpeg()), "-frames:v", "1", str(frame)], check=True)
        assert clips.mean_difference(deck / s["still"], frame) == 0
