"""The media of an export: what a clip is, the parts cut frame-exactly, the stills by frame number.

Everything goes through lecturekit.clips (ffmpeg, ffprobe, the frame table), into a work folder; a part, a still
or a remuxed clip is made once however many slides use it. The files PowerPoint gets are H.264, yuv420p, with
their index first; these are the safe settings for PowerPoint on Windows and macOS as far as could be found, not
settings checked in PowerPoint here (docs/EXPORT.md).
"""

from __future__ import annotations

import json
import re
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .. import clips
from .plan import Colour, Cut, Frame


@dataclass
class Info:
    """What the export needs to know of a video."""
    width: int
    height: int
    display: tuple[float, float]        # width times the sample aspect ratio, height
    fps: float
    frames: int
    codec: str | None
    pix_fmt: str | None
    mp4: bool                           # an MP4 (or QuickTime) container
    index_first: bool                   # the moov atom before the mdat

    @property
    def embeddable(self) -> bool:
        """Whether PowerPoint can take the file as it is: H.264, yuv420p, in MP4, even-sized."""
        return (self.codec == "h264" and self.pix_fmt == "yuv420p" and self.mp4
                and self.width % 2 == 0 and self.height % 2 == 0)


def _atoms(path: Path) -> list[str]:
    """The top-level atoms of an MP4, in file order."""
    names = []
    with open(path, "rb") as f:
        while True:
            head = f.read(8)
            if len(head) < 8:
                break
            size, name = struct.unpack(">I4s", head)
            names.append(name.decode("latin-1"))
            if size == 1:
                size = struct.unpack(">Q", f.read(8))[0]
                f.seek(size - 16, 1)
            elif size == 0:
                break
            else:
                f.seek(size - 8, 1)
    return names


def _hex(tint: Colour) -> str:
    return "%02x%02x%02x" % tuple(tint)


#: swscale's exact conversion between YUV and RGB. Its default rounds a flat colour by up to 3 levels (measured on
#: the test clips: 2.5 levels of red in the mean, against 0.3 with these flags), which would show as a faint box.
_EXACT = "accurate_rnd+full_chroma_int+full_chroma_inp"


def _multiply(tint: Colour) -> list[str]:
    """The ffmpeg filters that multiply each frame by a colour, in RGB: what `mix-blend-mode: multiply` shows of a
    clip on a page of that one colour."""
    r, g, b = (f"{v / 255:.6f}" for v in tint)
    return [f"scale=flags={_EXACT}", "format=gbrp", f"colorchannelmixer=rr={r}:gg={g}:bb={b}"]


def _stream(path: Path) -> dict:
    """ffprobe's view of the first video stream (codec, pixel format, sample aspect ratio) and the container; where
    there is no ffprobe (the `export` extra brings ffmpeg alone), the same read from `ffmpeg -i`."""
    exe = clips._ffprobe()
    if not exe:
        return _stream_from_ffmpeg(path)
    r = subprocess.run([exe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=codec_name,pix_fmt,sample_aspect_ratio", "-show_entries", "format=format_name",
                        "-of", "json", str(path)], capture_output=True, text=True, check=False)
    if r.returncode:
        raise clips.ClipError(f"ffprobe could not read {path.name}")
    data = json.loads(r.stdout or "{}")
    st = (data.get("streams") or [{}])[0]
    st["format_name"] = (data.get("format") or {}).get("format_name", "")
    return st


def _stream_from_ffmpeg(path: Path) -> dict:
    """The fields of _stream from the header ffmpeg prints for an input, e.g. `Input #0, mov,mp4,m4a,3gp,3g2,mj2,
    from ...` and `Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(progressive), 1280x720
    [SAR 1:1 DAR 16:9], ...`."""
    exe = clips._need_ffmpeg()
    err = subprocess.run([exe, "-hide_banner", "-i", str(path)], capture_output=True, text=True, check=False).stderr
    out: dict = {}
    fmt = re.search(r"^Input #0, (.+?), from ", err, re.M)
    if fmt:
        out["format_name"] = fmt.group(1)
    video = re.search(r"Stream #0:\S*: Video: (\w+)[^,\n]*, (\w+)(.*)", err)
    if video:
        out["codec_name"], out["pix_fmt"] = video.group(1), video.group(2)
        sar = re.search(r"\[SAR (\d+:\d+)", video.group(3))
        if sar:
            out["sample_aspect_ratio"] = sar.group(1)
    return out


class Media:
    """The work folder of one export and what has been made in it."""

    def __init__(self, work: Path) -> None:
        self.work = Path(work)
        self.work.mkdir(parents=True, exist_ok=True)
        self._info: dict[Path, Info] = {}
        self._stills: dict[Frame, Path] = {}
        self._cuts: dict[Cut, Path] = {}
        self._names: dict[Path, str] = {}

    def _stem(self, file: Path) -> str:
        """A short name for a source file in the work folder, unique among the sources."""
        if file not in self._names:
            self._names[file] = f"{len(self._names):02d}-{file.stem}"
        return self._names[file]

    def info(self, file: Path) -> Info:
        file = Path(file)
        if file not in self._info:
            if not file.exists():
                raise clips.ClipError(f"the clip {file} is missing; build the deck again (lk build)")
            table = clips.frame_table(file)
            st = _stream(file)
            sar = clips._fraction(str(st.get("sample_aspect_ratio", "1:1")).replace(":", "/")) or 1.0
            mp4 = "mp4" in st.get("format_name", "") or file.suffix.lower() in (".mp4", ".m4v", ".mov")
            atoms = _atoms(file) if mp4 else []
            first = "moov" in atoms and "mdat" in atoms and atoms.index("moov") < atoms.index("mdat")
            self._info[file] = Info(width=table.width, height=table.height, display=(table.width * sar, table.height),
                                    fps=table.fps, frames=table.frames, codec=table.codec or st.get("codec_name"),
                                    pix_fmt=st.get("pix_fmt"), mp4=mp4, index_first=first)
        return self._info[file]

    def duration_ms(self, cut: Cut) -> int:
        """How long a movie plays: its frames at the clip's frame rate, in ms."""
        return max(1, round(cut.frames / self.info(cut.file).fps * 1000))

    def stills(self, frames: list[Frame]) -> dict[Frame, Path]:
        """PNGs of the frames, by frame number; one decoding pass per video for those not made yet. A frame with a
        tint is the plain frame multiplied by it."""
        todo: dict[Path, set[Frame]] = {}
        for fr in frames:
            plain = Frame(fr.file, fr.n)
            if plain not in self._stills:
                todo.setdefault(fr.file, set()).add(plain)
        for file, frs in todo.items():
            frs = sorted(frs, key=lambda f: f.n)
            outs = [self.work / f"{self._stem(file)}.f{fr.n:05d}.png" for fr in frs]
            clips.extract_frames(file, [fr.n for fr in frs], outs)
            self._stills.update(zip(frs, outs))
        for fr in frames:
            if fr.tint and fr not in self._stills:
                from PIL import Image, ImageChops
                plain = self._stills[Frame(fr.file, fr.n)]
                out = plain.with_name(f"{plain.stem}.x{_hex(fr.tint)}.png")
                with Image.open(plain) as im:
                    im = im.convert("RGB")
                    ImageChops.multiply(im, Image.new("RGB", im.size, tuple(fr.tint))).save(out)
                self._stills[fr] = out
        return {fr: self._stills[fr] for fr in frames}

    def movie(self, cut: Cut) -> Path:
        """The file of a movie: a part cut frame-exactly (frames a to b, both included) by re-encoding; a whole clip
        as it is when PowerPoint can take it, moved to index first by stream copy when it is not, else re-encoded. A
        movie with a tint is always re-encoded, its frames multiplied by the tint."""
        if cut in self._cuts:
            return self._cuts[cut]
        info = self.info(cut.file)
        stem = self._stem(cut.file)
        tint = _multiply(cut.tint) if cut.tint else []
        mark = f".x{_hex(cut.tint)}" if cut.tint else ""
        even = ["scale=trunc(iw/2)*2:trunc(ih/2)*2" + (f":flags={_EXACT}" if tint else ""), "format=yuv420p"]
        if cut.whole:
            if info.embeddable and info.index_first and not tint:
                out = cut.file
            elif info.embeddable and not tint:
                out = self.work / f"{stem}.mp4"
                clips.faststart(cut.file, out)
            else:
                out = self.work / f"{stem}{mark}.h264.mp4"
                clips.reencode(cut.file, out, [*tint, *even], [], info.frames)
        else:
            if not 0 <= cut.a < cut.b < info.frames:
                raise clips.ClipError(f"{cut.file.name} has {info.frames} frames; the part {cut.a} to {cut.b} "
                                      f"is not in it")
            out = self.work / f"{stem}.p{cut.a:05d}-{cut.b:05d}{mark}.mp4"
            clips.reencode(cut.file, out, [f"trim=start_frame={cut.a}:end_frame={cut.b + 1}", "setpts=PTS-STARTPTS",
                                           *tint, *even], [], cut.frames)
        self._cuts[cut] = out
        return out
