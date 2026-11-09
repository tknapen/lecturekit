"""A stand-in for manim8's `scianim`, for lecturekit's seam tests.

It writes manim8's real render layout (`renders/<revision>/<job>/`, the full movie first and the per-scene
section movies after it, one PNG per checkpoint, `manifest.json`) from a manifest recorded from a real
`scianim render --profile final` of the divisive_normalization example (`manifest_render.json`), with the
videos and stills made small. It keeps a cache pointer per cache key as manim8 does, so a second render of the
same inputs is a cache hit that writes nothing.

Environment:
    FAKE_SCIANIM_LOG      append one JSON line per call (the argv) to this file
    FAKE_SCIANIM_OLD=1    behave like a manim8 without `render --json` and `--style` (human output on stdout)
    FAKE_SCIANIM_FAIL     comma-separated project names whose render fails
    FAKE_SCIANIM_SCHEMA   write this manifest schema_version
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "manifest_render.json"
OLD = os.environ.get("FAKE_SCIANIM_OLD") == "1"
W, H, FPS, SECONDS = 320, 180, 30, 2


def log(argv: list[str]) -> None:
    path = os.environ.get("FAKE_SCIANIM_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(argv) + "\n")


def fail(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    sys.exit(code)


def opt(args: list[str], name: str) -> str | None:
    if name in args:
        i = args.index(name)
        return args[i + 1] if i + 1 < len(args) else None
    return None


def family_of(project: Path) -> Path | None:
    for d in project.resolve().parents:
        if (d / "family.yaml").exists():
            return d
    return None


def ffmpeg() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def video(path: Path, colour: str, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exe = ffmpeg()
    if exe:
        subprocess.run([exe, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        f"color=c={colour}:s={W}x{H}:r={FPS}:d={seconds},"
                        f"drawbox=x=100:y=50:w=120:h=80:color=0x175B8E:t=fill",
                        "-pix_fmt", "yuv420p", str(path)], check=True)
    else:
        path.write_bytes(f"fake movie {colour} {seconds}".encode())


def still(path: Path, box: tuple[int, int, int, int]) -> None:
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (W, H), "#FFFFFF")
    ImageDraw.Draw(im).rectangle(box, fill="#175B8E")
    im.save(path)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(args: list[str]) -> None:
    project = Path(args[0])
    want_json = "--json" in args and not OLD
    if OLD and ("--json" in args or "--style" in args):
        fail("No such option: --json" if "--json" in args else "No such option: --style", 2)
    say = sys.stderr if want_json else sys.stdout
    profile = opt(args, "--profile") or "draft"
    revision = opt(args, "--revision")
    style = opt(args, "--style")
    if project.name in (os.environ.get("FAKE_SCIANIM_FAIL") or "").split(","):
        fail(f"worker failed: the storyboard of {project.name} asks for a kind the registry does not have")
    family = family_of(project)
    if family is None or not (family / ".venv").exists():
        fail(f"family environment unavailable at {family}/.venv; run `scianim family env sync {family}`")
    if revision is None and not (project / "code" / f"scene_{project.name}.py").exists():
        fail("scene module missing; run `scianim codegen` first")
    spec = (project / "animation.yaml").read_bytes()
    key = "sha256:" + hashlib.sha256(json.dumps([profile, style, revision]).encode() + spec).hexdigest()
    pointer = project / ".scianim" / "cache" / f"{key[7:]}.json"
    if pointer.exists() and "--no-cache" not in args:
        manifest = json.loads((project / json.loads(pointer.read_text())["manifest"]).read_text())
        manifest["cache_hit"] = True
        print(f"cache hit {key[:23]}... -> {manifest['job']['output_dir']}/manifest.json", file=say)
        if want_json:
            print(json.dumps(manifest, indent=2))
        return
    print(f"rendering {profile} video of {revision or 'working'} (cache {key[:23]}...)", file=say)
    record = json.loads(FIXTURE.read_text())
    old_job = record["job"]["job_id"]
    job = f"job_{dt.datetime.now(dt.UTC).strftime('%Y%m%dT%H%M%S')}_{secrets.token_hex(3)}"
    rev = revision or "working"
    record = json.loads(json.dumps(record).replace(old_job, job).replace("renders/working/", f"renders/{rev}/"))
    out = project / "renders" / rev / job
    out.mkdir(parents=True)
    movie = out / f"{job}.mp4"
    video(movie, "white", SECONDS)                       # the full movie first ...
    for i, s in enumerate(record["result"]["sections"]):  # ... the sections after it, as Manim writes them
        video(project / s["video"], ["red", "green"][i % 2], SECONDS / 2)
    for i, c in enumerate(record["result"]["checkpoints"]):
        still(project / c["png"], (60 + 20 * i, 40, 140 + 20 * i, 120))
        c["width_px"], c["height_px"] = W, H
    v = record["result"]["videos"][0]
    v.update(width_px=W, height_px=H, fps=float(FPS), duration_seconds=float(SECONDS), frame_count=FPS * SECONDS,
             sha256=sha(movie))
    record["job"].update(revision_id=rev, cache_key=key, quality_profile=profile, output_dir=f"renders/{rev}/{job}")
    if style:
        name, _, version = style.partition("@")
        record["job"]["resolved_style"].update(theme=name, theme_version=version)
    if os.environ.get("FAKE_SCIANIM_SCHEMA"):
        record["schema_version"] = os.environ["FAKE_SCIANIM_SCHEMA"]
    record["created_at"] = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    record["cache_hit"] = False
    (out / "manifest.json").write_text(json.dumps(record, indent=2))
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(json.dumps({"manifest": f"renders/{rev}/{job}/manifest.json"}))
    print(f"video: {v['path']} | {W}x{H} | {FPS} fps\nstatus: succeeded", file=say)
    if want_json:
        print(json.dumps(record, indent=2))


def pointer_set(doc: dict, path: str, value) -> None:
    parts = path.strip("/").split("/")
    for p in parts[:-1]:
        doc = doc.setdefault(p, {})
    doc[parts[-1]] = value


def main(argv: list[str]) -> None:
    log(argv)
    if not argv:
        fail("usage: scianim COMMAND", 2)
    cmd, rest = argv[0], argv[1:]
    if cmd == "render" and "--help" in rest:
        opts = "--profile --revision --sample --no-cache" + ("" if OLD else " --style --json")
        print(f"Usage: scianim render [OPTIONS] PROJECT\n options: {opts}")
    elif cmd == "render":
        render(rest)
    elif cmd == "codegen":
        project = Path(rest[0])
        (project / "code").mkdir(exist_ok=True)
        (project / "code" / f"scene_{project.name}.py").write_text("# generated\n")
        print(f"wrote {project / 'code'}")
    elif cmd == "family" and rest[:2] == ["env", "sync"]:
        (Path(rest[2]) / ".venv").mkdir(exist_ok=True)
        print(f"environment ready at {Path(rest[2]) / '.venv'}")
    elif cmd == "family" and rest[0] == "init":
        ws = Path(opt(rest, "--workspace") or ".")
        name, _, version = (opt(rest, "--style") or "tomas_scientific@0.1.0").partition("@")
        d = ws / "families" / rest[1]
        d.mkdir(parents=True)
        (d / "family.yaml").write_text(f'schema_version: "1.0"\nid: {rest[1]}\ntitle: {rest[1]}\nstyle:\n'
                                       f'  name: {name}\n  version: "{version}"\nenvironment:\n  manager: uv\n')
    elif cmd == "project" and rest[0] == "init":
        ws = Path(opt(rest, "--workspace") or ".")
        d = ws / "families" / (opt(rest, "--family") or "") / rest[1]
        fam = yaml.safe_load((d.parent / "family.yaml").read_text())
        d.mkdir(parents=True)
        (d / "animation.yaml").write_text(
            f'schema_version: "1.0"\nid: {rest[1]}\ntitle: "{opt(rest, "--title") or rest[1]}"\nsources: []\n'
            'output:\n  duration_seconds: 15\n  width_px: 1920\n  height_px: 1080\n  aspect_ratio: "16:9"\n'
            f'  fps: 30\n  container: mp4\nstyle:\n  name: {fam["style"]["name"]}\n'
            f'  version: "{fam["style"]["version"]}"\n  overrides: {{}}\nequations: []\n')
    elif cmd == "workspace" and rest[0] == "init":
        ws = Path(rest[1])
        for sub in ("styles", "families", "assets"):
            (ws / sub).mkdir(parents=True, exist_ok=True)
        (ws / "workspace.yaml").write_text(f'schema_version: "1.0"\nid: {ws.name}\n')
    elif cmd == "propose" and rest[0] == "apply":
        project, proposal_file = Path(rest[1]), Path(rest[2])
        proposal = yaml.safe_load(proposal_file.read_text())
        if os.environ.get("FAKE_SCIANIM_PROPOSALS"):
            shutil.copy(proposal_file, Path(os.environ["FAKE_SCIANIM_PROPOSALS"]) / proposal_file.name)
        for target in proposal["targets"]:
            path = project / target["file"]
            doc = yaml.safe_load(path.read_text())
            for op in target["patch"]:
                pointer_set(doc, op["path"], op["value"])
            path.write_text(yaml.safe_dump(doc, sort_keys=False))
        applied = project / "proposals" / "applied"
        applied.mkdir(parents=True, exist_ok=True)
        (applied / f"{proposal['id']}.yaml").write_text(yaml.safe_dump({"proposal": proposal}))
        print(f"applied {proposal['id']}")
    else:
        fail(f"fake scianim: unknown command {argv}", 2)


if __name__ == "__main__":
    main(sys.argv[1:])
