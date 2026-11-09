"""Assemble the CI results page for GitHub Pages from the parts the jobs uploaded.

    python .github/scripts/ci_site.py site

`site/` holds the parts, downloaded side by side:

    paper/ dark/            each: kickoff/ features/ (the built decks), review/<deck>/ (shoot), review/<deck>-frags/
                            (fragment steps; the clips in parts walked with real keys), report/ (logs, junit)
    seam/                   features/ features-dark/ (built with the fresh manim8 clip), clips/ (assets/clips),
                            frags/ frags-dark/, report/ (logs, junit, manifests)

The script writes `site/index.html` (job results, the decks in both presets with their study PDFs and contact
sheets, the feature deck's clips in parts, the test results, the seam's evidence) and an `index.html` listing in every report and review directory,
since Pages lists no directories. The job results come from the environment: RESULTS is a JSON object of job name
to result (success, failure, cancelled, skipped), with RUN_URL, SHA and REF beside it.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

CSS = """
:root { --bg: #ffffff; --ink: #202b33; --muted: #566573; --hair: #d8dde3; --ok: #1b7f3b; --bad: #b3261e;
        --warn: #8a5a00; --card: #f5f7f9; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
        --bg: #111417; --ink: #e6eaee; --muted: #9aa5b1; --hair: #2c333a; --ok: #5cc27e; --bad: #ff8a80;
        --warn: #e0b354; --card: #1a1f24; } }
body { background: var(--bg); color: var(--ink); font: 15px/1.5 system-ui, sans-serif; margin: 0; }
main { max-width: 980px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 22px; margin: 0 0 4px; } h2 { font-size: 17px; margin: 32px 0 8px; }
p.meta { color: var(--muted); margin: 0 0 16px; } a { color: inherit; }
table { border-collapse: collapse; width: 100%; } td, th { border-bottom: 1px solid var(--hair); padding: 6px 8px;
        text-align: left; vertical-align: top; } th { color: var(--muted); font-weight: 600; }
.success { color: var(--ok); font-weight: 600; } .failure { color: var(--bad); font-weight: 600; }
.cancelled, .skipped, .missing { color: var(--warn); font-weight: 600; }
pre { background: var(--card); padding: 10px; overflow-x: auto; font-size: 12.5px; max-height: 420px; }
video { max-width: 100%; border: 1px solid var(--hair); background: #fff; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.card { background: var(--card); padding: 12px; } .card h3 { font-size: 15px; margin: 0 0 6px; }
"""

PRESETS = ("paper", "dark")
DECKS = ("kickoff", "features")


def esc(s: object) -> str:
    return html.escape(str(s))


def link(site: Path, rel: str, text: str) -> str:
    return f'<a href="{esc(rel)}">{esc(text)}</a>' if (site / rel).exists() else f'<span class="missing">{esc(text)} (absent)</span>'


def junit(path: Path) -> dict | None:
    if not path.exists():
        return None
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    out = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0, "failed": []}
    for s in suites:
        for key in ("tests", "failures", "errors", "skipped"):
            out[key] += int(s.get(key, 0))
        out["time"] += float(s.get("time", 0))
        for case in s.iter("testcase"):
            for kind in ("failure", "error"):
                node = case.find(kind)
                if node is not None:
                    name = f"{case.get('classname', '')}::{case.get('name', '')}"
                    out["failed"].append((name, (node.get("message") or node.text or "")[:2000]))
    return out


def junit_block(title: str, data: dict | None) -> str:
    if data is None:
        return f"<p><b>{esc(title)}</b>: <span class='missing'>no results (the job did not reach its tests)</span></p>"
    bad = data["failures"] + data["errors"]
    state = "failure" if bad else "success"
    passed = data["tests"] - bad - data["skipped"]
    head = (f"<p><b>{esc(title)}</b>: <span class='{state}'>{passed} passed, {bad} failed</span>, "
            f"{data['skipped']} skipped, {data['time']:.0f} s</p>")
    rows = "".join(f"<details><summary>{esc(n)}</summary><pre>{esc(m)}</pre></details>" for n, m in data["failed"])
    return head + rows


def log_block(site: Path, rel: str, title: str) -> str:
    path = site / rel
    if not path.exists():
        return f"<p><b>{esc(title)}</b>: <span class='missing'>no log</span></p>"
    text = path.read_text(encoding="utf-8", errors="replace")
    tail = "\n".join(text.splitlines()[-200:])
    return f"<details><summary><b>{esc(title)}</b> ({link(site, rel, 'full log')})</summary><pre>{esc(tail)}</pre></details>"


def parts_slides(deck_html: Path) -> list[tuple[int, str, str, str]]:
    """The clips in parts of a built live deck: (slide number, section id, title, clip name), from its markup."""
    if not deck_html.exists():
        return []
    text = deck_html.read_text(encoding="utf-8", errors="replace")
    starts = [m for m in re.finditer(r'<section id="([^"]+)"', text)]
    out = []
    for n, m in enumerate(starts):
        end = starts[n + 1].start() if n + 1 < len(starts) else len(text)
        body = text[m.start():end]
        clip = re.search(r'data-lk-seg="([^"]+)"', body)
        if clip:
            title = re.search(r"<h2[^>]*>(.*?)</h2>", body, re.S)
            name = re.sub(r"<[^>]+>", "", title.group(1)).strip() if title else m.group(1)
            out.append((n + 1, m.group(1), name, clip.group(1)))     # the title slide is the first section
    return out


def listings(site: Path) -> None:
    """An index.html in every report, review and frags directory, so links to them open on Pages."""
    for top in [site / p for p in ("paper", "dark", "seam")]:
        if not top.exists():
            continue
        for d in [top / "review", top / "report", top / "frags", top / "frags-dark", top / "clips"]:
            for sub in [d, *[p for p in d.rglob("*") if p.is_dir()]] if d.exists() else []:
                if (sub / "index.html").exists():
                    continue
                items = sorted(sub.iterdir())
                rows = "".join(
                    f'<li><a href="{esc(p.name)}{"/" if p.is_dir() else ""}">{esc(p.name)}</a></li>' for p in items
                )
                sub.joinpath("index.html").write_text(
                    f"<!doctype html><meta charset='utf-8'><title>{esc(sub.relative_to(site))}</title>"
                    f"<style>{CSS}</style><main><h1>{esc(sub.relative_to(site))}</h1><ul>{rows}</ul></main>",
                    encoding="utf-8",
                )


def main(site: Path) -> int:
    raw = json.loads(os.environ.get("RESULTS", "{}"))
    # toJSON(needs) gives {job: {"result": ..., "outputs": {...}}}; a plain {job: result} works too
    results = {j: (v.get("result", "unknown") if isinstance(v, dict) else v) for j, v in raw.items()}
    run_url, sha, ref = os.environ.get("RUN_URL", ""), os.environ.get("SHA", ""), os.environ.get("REF", "")
    repo = os.environ.get("REPO_URL", "https://github.com/tknapen/lecturekit")
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    listings(site)
    parts = []

    jobs = "".join(f"<tr><td>{esc(j)}</td><td class='{esc(r)}'>{esc(r)}</td></tr>" for j, r in results.items())
    parts.append(f"<h2>Jobs</h2><table><tr><th>job</th><th>result</th></tr>{jobs}</table>")

    rows = []
    for deck in DECKS:
        cells = []
        for preset in PRESETS:
            base = f"{preset}/{deck}"
            cells.append(
                "<td>" + " · ".join([
                    link(site, f"{base}/slides-live.html", "live deck"),
                    link(site, f"{base}/slides-study.pdf", "study PDF"),
                    link(site, f"{preset}/review/{deck}/sheet.png", "contact sheet"),
                    link(site, f"{base}/timing.txt", "timing"),
                ]) + "</td>"
            )
        rows.append(f"<tr><td>{deck}</td>{''.join(cells)}</tr>")
    parts.append("<h2>Decks</h2><table><tr><th>deck</th><th>paper</th><th>dark</th></tr>" + "".join(rows) + "</table>")

    seg = parts_slides(site / "paper/features/slides-live.html") or parts_slides(site / "dark/features/slides-live.html")
    parts.append("<h2>Clips in parts</h2>")
    if seg:
        parts.append(
            "<p>The feature deck's clips held at their stops by key presses (<code>stops=</code>): open a slide and "
            "press Right; the frags reports walk each one with real keys and read the frame of every hold.</p>"
        )
        rows = []
        for number, sid, title, clip in seg:
            cells = []
            for preset in PRESETS:
                cells.append("<td>" + " · ".join([
                    link(site, f"{preset}/features/slides-live.html", "live").replace(
                        'href="' + f"{preset}/features/slides-live.html" + '"',
                        'href="' + f"{preset}/features/slides-live.html#/{esc(sid)}" + '"'),
                    link(site, f"{preset}/review/features-frags/s{number:02d}-f0.png", "first hold"),
                    link(site, f"{preset}/review/features-frags/index.html", "frags"),
                ]) + "</td>")
            rows.append(f"<tr><td>{number} {esc(title)}<br><span class='meta'>{esc(clip)}</span></td>{''.join(cells)}</tr>")
        parts.append("<table><tr><th>slide</th><th>paper</th><th>dark</th></tr>" + "".join(rows) + "</table>")
    else:
        parts.append("<p class='missing'>no built feature deck with a clip in parts</p>")

    parts.append("<h2>Tests and checks</h2>")
    parts.append(junit_block("Engine tests (pytest)", junit(site / "paper/report/pytest.xml")))
    for preset in PRESETS:
        parts.append(log_block(site, f"{preset}/report/checks.log", f"Review checks, {preset} (contrast, shoot, measure, frags, overflow)"))

    seam = site / "seam"
    parts.append("<h2>The seam with manim8</h2>")
    parts.append(
        "<p>lecturekit installed with pip and its manim8 extra; the feature deck's manim8 clip rendered afresh in both "
        "presets by <code>lk clips</code>, its index checked against the manifest of the job that made it, the deck "
        "built with it, its fragments checked.</p>"
    )
    cards = []
    for preset, sub in (("paper", ""), ("dark", "dark/")):
        index_path = seam / f"clips/{sub}clips.json"
        entries = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
        for name, e in sorted(entries.items()):
            if e.get("producer") != "manim8":
                continue
            video = e.get("video", "").replace("assets/clips/", "clips/")
            facts = ", ".join(f"{k} {e[k]}" for k in ("width", "height", "fps", "duration", "revision") if k in e)
            cards.append(
                f"<div class='card'><h3>{esc(name)}, {preset}</h3>"
                f"<video src='seam/{esc(video)}' controls muted playsinline preload='metadata'></video>"
                f"<p class='meta'>{esc(facts)}</p></div>"
            )
    parts.append("<div class='grid'>" + "".join(cards) + "</div>" if cards else "<p class='missing'>no manim8 clip was indexed</p>")
    parts.append(log_block(site, "seam/report/index-check.log", "Index against manifest, paper"))
    parts.append(log_block(site, "seam/report/index-check-dark.log", "Index against manifest, dark"))
    parts.append(junit_block("Seam tests (pytest)", junit(seam / "report/pytest.xml")))
    parts.append(
        "<p>" + " · ".join([
            link(site, "seam/features/slides-live.html", "feature deck with the fresh clip, paper"),
            link(site, "seam/features-dark/slides-live.html", "dark"),
            link(site, "seam/features/slides-study.pdf", "study PDF"),
            link(site, "seam/frags/index.html", "frags report, paper"),
            link(site, "seam/frags-dark/index.html", "dark"),
            link(site, "seam/report/index.html", "manifests and logs"),
        ]) + "</p>"
    )

    commit = f'<a href="{esc(repo)}/commit/{esc(sha)}">{esc(sha[:7])}</a>' if sha else "unknown commit"
    run = f' · <a href="{esc(run_url)}">workflow run</a>' if run_url else ""
    page = (
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>lecturekit CI</title><style>{CSS}</style><main>"
        f"<h1>lecturekit CI</h1><p class='meta'>{esc(ref)} at {commit}{run} · built {esc(when)}</p>"
        + "".join(parts) + "</main></html>"
    )
    (site / "index.html").write_text(page, encoding="utf-8")
    print(f"ci_site: wrote {site / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "site")))
