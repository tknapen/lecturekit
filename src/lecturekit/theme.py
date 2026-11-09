"""The theme: `_brand.yml` read once, tokens written for every consumer.

A deck's look is defined in one place, Quarto's `_brand.yml`. Quarto applies
it to the live deck itself. Everything else that needs the same values reads
it through this module:

* the Beamer side, as `\\definecolor{nm<Name>}` lines and fontspec lines
  (`tokens.tex`), also written by the Lua filter at render time;
* the live deck, as `--nm-<name>` CSS variables (`tokens.css`);
* Python code (TikZ figures, Manim clips), as `tokens.py` or directly through
  :func:`load_brand`;
* manim8, as versioned styles that inherit `default@0.5.0`, one per preset
  (`lecturekit_paper@<version>`, `lecturekit_dark@<version>`), written into the
  project's manim8 workspace and selected in its projects (`lk theme --manim8`).

Names: a palette entry `ink` becomes `nmInk`, `--nm-ink` and `INK`; a
multi-word entry `role-concept` becomes `nmRoleConcept`, `--nm-role-concept`
and `ROLE_CONCEPT`.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

#: the colour names the engine itself relies on; a brand file should define them
ENGINE_COLORS = (
    "paper", "slide", "ink", "muted", "hairline",
    "concept", "caveat", "example", "anchor", "question",
    "input", "state", "update", "context",
)

#: the families bundled in the extension's fonts/ directory, used by file whatever the brand says about their source
BUNDLED_FONTS = {
    "TeX Gyre Heros": {"dir": "", "r": "texgyreheros-regular.otf", "b": "texgyreheros-bold.otf",
                       "ri": "texgyreheros-italic.otf", "bi": "texgyreheros-bolditalic.otf"},
    "TeX Gyre Pagella": {"dir": "", "r": "texgyrepagella-regular.otf", "b": "texgyrepagella-bold.otf",
                         "ri": "texgyrepagella-italic.otf", "bi": "texgyrepagella-bolditalic.otf"},
    "Roboto": {"dir": "roboto", "r": "Roboto-Regular.ttf", "b": "Roboto-Bold.ttf",
               "ri": "Roboto-Italic.ttf", "bi": "Roboto-BoldItalic.ttf"},
}
MATH_FONT = "texgyrepagella-math.otf"


def bundled_fonts_dir() -> Path:
    from .project import extension_source
    return (extension_source() / "fonts").resolve()


#: brand.yml semantic names that may alias palette entries
SEMANTIC_COLORS = (
    "foreground", "background", "primary", "secondary", "tertiary",
    "success", "info", "warning", "danger", "light", "dark", "link",
)


def camel(name: str) -> str:
    """`role-concept` -> `RoleConcept` (the LaTeX colour is `nmRoleConcept`)."""
    parts = re.split(r"[-_]", name)
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


def constant(name: str) -> str:
    """`role-concept` -> `ROLE_CONCEPT`."""
    return re.sub(r"[-\s]", "_", name).upper()


def _hex(value: str) -> str:
    v = value.strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", v):
        return v.upper()
    if re.fullmatch(r"#[0-9a-fA-F]{3}", v):
        return "#" + "".join(c * 2 for c in v[1:]).upper()
    raise ValueError(f"not a hex colour: {value!r}")


@dataclass
class FontFace:
    family: str
    source: str = "system"            # system | file | google | bunny
    files: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Tokens:
    """Everything a consumer needs from a brand file."""

    name: str
    path: Path | None
    colors: dict[str, str]                 # name -> #RRGGBB, palette and semantic names
    base_font: str | None
    heading_font: str | None
    mono_font: str | None
    fonts: dict[str, FontFace]
    base_size: str | None = None
    mode: str = "light"
    heading_weight: str | None = None

    # ------------------------------------------------------------------ access
    def __getattr__(self, item: str) -> str:
        # tokens.INK, tokens.CONCEPT ...
        key = item.lower().replace("_", "-")
        colors = self.__dict__.get("colors", {})
        if key in colors:
            return colors[key]
        key2 = item.lower()
        if key2 in colors:
            return colors[key2]
        raise AttributeError(item)

    def __getitem__(self, name: str) -> str:
        return self.colors[name]

    def missing_engine_colors(self) -> list[str]:
        return [c for c in ENGINE_COLORS if c not in self.colors]

    # ----------------------------------------------------------------- writers
    def latex(self) -> str:
        lines = ["% colour and font tokens from _brand.yml (written by lecturekit; do not edit)"]
        for name in sorted(self.colors):
            lines.append(f"\\definecolor{{nm{camel(name)}}}{{HTML}}{{{self.colors[name][1:]}}}")
        lines.extend(self.fontspec_lines())
        return "\n".join(lines) + "\n"

    def fontspec_lines(self) -> list[str]:
        """The fontspec lines of tokens.tex: the serif (headings) family as the main font, the sans (base) family
        as the sans font, the theme's two letterspaced families, and the math font, as lkbrand.lua writes them."""
        serif = self.heading_font or "TeX Gyre Pagella"
        sans = self.base_font or "TeX Gyre Heros"
        return [
            "\\setmainfont" + self._fontspec_args(serif),
            "\\setsansfont" + self._fontspec_args(sans),
            "\\newfontfamily\\nmSerifCaps" + self._fontspec_args(serif, "LetterSpace=2.0"),
            "\\newfontfamily\\nmSansCaps" + self._fontspec_args(sans, "LetterSpace=8.0"),
            f"\\setmathfont{{{MATH_FONT}}}[Path={bundled_fonts_dir().as_posix()}/]",
        ]

    def faces(self, family: str) -> dict[str, Path] | None:
        """The files of a family by face (r, b, ri, bi): from the brand's `source: file` entry, else the bundle."""
        face = self.fonts.get(family)
        if face and face.source == "file" and face.files:
            by: dict[str, Path] = {}
            base = (self.path.parent if self.path else Path.cwd()).resolve()
            for f in face.files:
                path = Path(f["path"] if isinstance(f, dict) else str(f))
                weight = str(f.get("weight", 400)) if isinstance(f, dict) else "400"
                style = (f.get("style", "normal") if isinstance(f, dict) else "normal")
                bold = weight in ("bold", "semibold") or (weight.isdigit() and int(weight) >= 600)
                key = ("b" if bold else "r") + ("i" if style == "italic" else "")
                by.setdefault(key, path if path.is_absolute() else base / path)
            if "r" in by or "b" in by:
                return by
        if family in BUNDLED_FONTS:
            d = bundled_fonts_dir() / BUNDLED_FONTS[family]["dir"]
            return {k: d / v for k, v in BUNDLED_FONTS[family].items() if k != "dir"}
        return None

    def _fontspec_args(self, family: str, extra: str | None = None) -> str:
        by = self.faces(family)
        if not by:
            return f"{{{family}}}[{extra}]" if extra else f"{{{family}}}"
        upright = by.get("r") or by.get("b")
        opts = [f"Path={upright.parent.as_posix()}/"]
        if "b" in by:
            opts.append(f"BoldFont={by['b'].name}")
        if "ri" in by:
            opts.append(f"ItalicFont={by['ri'].name}")
        if "bi" in by:
            opts.append(f"BoldItalicFont={by['bi'].name}")
        if upright.suffix == ".otf":
            opts.append("Ligatures=TeX")
        if extra:
            opts.append(extra)
        return f"{{{upright.name}}}[{','.join(opts)}]"

    def css(self) -> str:
        body = "".join(f"--nm-{name}:{self.colors[name]};" for name in sorted(self.colors))
        return ":root{" + body + "}\n"

    def python(self) -> str:
        lines = [
            '"""Colour and font tokens from _brand.yml (written by lecturekit; do not edit)."""',
            "",
            f"BRAND = {self.name!r}",
            f"MODE = {self.mode!r}",
            f"BASE_FONT = {self.base_font!r}",
            f"HEADING_FONT = {self.heading_font!r}",
            f"MONO_FONT = {self.mono_font!r}",
            "",
            "COLORS = {",
        ]
        for name in sorted(self.colors):
            lines.append(f"    {name!r}: {self.colors[name]!r},")
        lines.append("}")
        lines.append("")
        for name in sorted(self.colors):
            lines.append(f"{constant(name)} = {self.colors[name]!r}")
        lines.append("")
        lines.append("def rgb(name):")
        lines.append('    """0 to 1 RGB triple of a token, for matplotlib and Manim."""')
        lines.append("    h = COLORS[name].lstrip('#')")
        lines.append("    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))")
        return "\n".join(lines) + "\n"

    def manim8_style(self, version: str, inherits: str = "default@0.5.0", name: str | None = None) -> str:
        """A manim8 style version mapping the brand onto manim8's palette roles (THEMING.md).

        manim8's rule is that a style change is a new version, never an edit; the caller chooses the version
        string. The sheet validates against manim8's `StyleSheet`: the name and every palette key are slugs
        (lowercase letters, digits and underscores, starting with a letter).
        """
        c = self.colors

        def pick(*names: str, default: str | None = None) -> str | None:
            for n in names:
                if n in c:
                    return c[n]
            return default

        background = pick("slide", "background", default="#FFFFFF")
        foreground = pick("ink", "foreground", default="#202B33")
        text_muted = pick("muted", default="#566573")
        hairline = pick("hairline")
        roles = {
            "primary_signal": pick("input", "concept", default="#0072B2"),
            "normalization_pool": pick("update", "example", default="#C45A00"),
            "emphasis": pick("concept", "primary", default="#175B8E"),
            "warning": pick("caveat", "danger", default="#A33A32"),
            "comparison": pick("context", "question", default="#7A5195"),
        }
        palette: dict[str, str] = {
            "background": background,
            "foreground": foreground,
            "secondary_text": text_muted,
            # manim8 fills inactive units with `neutral` and draws meshes and fall-back series in `muted`:
            # quiet surfaces, so they come from the hairline (and halfway to the muted text), never a text grey
            "neutral": hairline or mix(background, foreground, 0.15),
            "muted": mix(hairline, text_muted, 0.5) if hairline else text_muted,
            "grid": mix(background, hairline or foreground, 0.5 if hairline else 0.1),
            **roles,
        }
        palette["uncertainty"] = mix(background, roles["primary_signal"], 0.15)
        palette["selection"] = mix(background, roles["primary_signal"], 0.08)
        for role, value in roles.items():
            palette[f"{role}_soft"] = mix(background, value, SOFT_TINT)
        # project tokens beyond the roles travel as extra palette entries, under slug keys, with their tints
        for brand_name in sorted(c):
            key = slug(brand_name)
            if key is None or key in palette or brand_name in SEMANTIC_COLORS:
                continue
            palette[key] = c[brand_name]
            soft = f"{key}_soft"
            if brand_name not in SURFACE_COLORS and soft not in palette and len(soft) <= 64:
                palette[soft] = mix(background, c[brand_name], SOFT_TINT)
        typography: dict[str, dict[str, Any]] = {}
        head = self.heading_font or self.base_font
        for role, fam in (("title", head), ("body", self.base_font), ("annotation", self.base_font),
                          ("axis_label", self.base_font), ("tick_label", self.base_font), ("caption", self.base_font)):
            if fam:
                typography[role] = {"font_family": fam, "font_fallbacks": font_fallbacks(fam)}
        weight = manim8_weight(self.heading_weight)
        if weight and "title" in typography:
            typography["title"]["weight"] = weight
        doc = {
            "schema_version": "1.0",
            "name": name or style_name(self),
            "version": version,
            "description": f"lecturekit brand {self.name!r} ({self.mode}) mapped onto manim8 palette roles; "
                           "written by `lk theme --manim8`, a new version per change.",
            "inherits": inherits,
            "palette": palette,
            "typography": typography,
        }
        return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)


#: share of the role colour in a `<role>_soft` tint, the rest the background (manim8's own tints are about 35 %)
SOFT_TINT = 0.35
#: brand tokens that are surfaces or text, which get no `_soft` tint in a manim8 style
SURFACE_COLORS = ("paper", "slide", "ink", "body", "heading", "muted", "hairline")
SERIF_HINTS = ("pagella", "palatino", "termes", "times", "garamond", "georgia", "libertin", "schola", "bonum",
               "baskerville", "minion", "charter", "book antiqua", "serif")
SERIF_FALLBACKS = ("TeX Gyre Pagella", "Palatino", "P052", "serif")
SANS_FALLBACKS = ("TeX Gyre Heros", "Helvetica", "Nimbus Sans", "sans-serif")


def slug(text: str, prefix: str = "c") -> str | None:
    """A manim8 slug (`^[a-z][a-z0-9_]{0,63}$`): `DoG` -> `dog`, `lecturekit paper` -> `lecturekit_paper`."""
    s = re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")
    if not s:
        return None
    if not s[0].isalpha():
        s = f"{prefix}_{s}"
    return s[:64].rstrip("_")


def style_name(tokens: "Tokens", mode: str | None = None) -> str:
    """The manim8 style name of a brand in a mode: the brand's name as a slug, `_dark` added for the dark side
    of a brand whose name does not already say so (`lecturekit paper` -> `lecturekit_paper`,
    `lecturekit dark` -> `lecturekit_dark`)."""
    name = slug(tokens.name) or "brand"
    if (mode or tokens.mode) == "dark" and not name.endswith("dark"):
        name = f"{name}_dark"[:64]
    return name


def mix(a: str, b: str, t: float) -> str:
    """`t` of the way from colour `a` to colour `b`, as #RRGGBB."""
    ha, hb = _hex(a)[1:], _hex(b)[1:]
    parts = [round(int(ha[i:i + 2], 16) * (1 - t) + int(hb[i:i + 2], 16) * t) for i in (0, 2, 4)]
    return "#" + "".join(f"{v:02X}" for v in parts)


def font_fallbacks(family: str) -> list[str]:
    """Fall-back families for a font, serif or sans by the family's name, without repeats or the family itself."""
    chain = SERIF_FALLBACKS if any(h in family.lower() for h in SERIF_HINTS) and "sans" not in family.lower() \
        else SANS_FALLBACKS
    out: list[str] = []
    for f in chain:
        if f != family and f not in out:
            out.append(f)
    return out


def manim8_weight(weight: Any) -> str | None:
    """A brand font weight (400, `bold`) as manim8's weight name, or None."""
    if weight is None:
        return None
    w = str(weight).strip().lower()
    names = {"normal": "regular", "regular": "regular", "light": "light", "medium": "medium",
             "semibold": "semibold", "bold": "bold"}
    if w in names:
        return names[w]
    if w.isdigit():
        n = int(w)
        return "light" if n < 400 else "regular" if n < 500 else "medium" if n < 600 else "semibold" if n < 700 \
            else "bold"
    return None


# ---------------------------------------------------------------------- loading
def find_brand(start: Path | None = None, env: bool = True) -> Path | None:
    """The nearest `_brand.yml` walking up from `start` (or `LECTUREKIT_BRAND`)."""
    named = os.environ.get("LECTUREKIT_BRAND") if env else None
    if named:
        return Path(named)
    here = (start or Path.cwd()).resolve()
    for d in [here, *here.parents]:
        p = d / "_brand.yml"
        if p.exists():
            return p
    return None


def brand_for_mode(start: Path | None = None, mode: str = "light", env: bool = True) -> Path | None:
    """The brand file of a preset. Light: the nearest `_brand.yml`. Dark: the brand that the project's dark
    profile names (`brand:` in `_quarto-dark.yml`), else a `_brand-dark.yml`, else the light file, read on its
    dark side. `LECTUREKIT_BRAND` wins when `env` is set."""
    named = os.environ.get("LECTUREKIT_BRAND") if env else None
    if named:
        return Path(named)
    light = find_brand(start, env=False)
    if mode != "dark":
        return light
    here = (start or Path.cwd()).resolve()
    for d in [here, *here.parents]:
        profile = d / "_quarto-dark.yml"
        if profile.exists():
            data = yaml.safe_load(profile.read_text(encoding="utf-8")) or {}
            b = data.get("brand")
            if isinstance(b, dict):
                b = b.get("dark")
            if isinstance(b, str) and (d / b).exists():
                return d / b
        if (d / "_brand-dark.yml").exists():
            return d / "_brand-dark.yml"
        if (d / "_quarto.yml").exists():
            break
    return light


def is_unified(path: Path | None) -> bool:
    """Whether a brand file carries `light` and `dark` values (a unified brand)."""
    if path is None or not Path(path).exists():
        return False
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    color = data.get("color") or {}
    values = list((color.get("palette") or {}).values()) + [color.get(k) for k in SEMANTIC_COLORS]
    return any(isinstance(v, dict) and "dark" in v for v in values)


def _resolve(value: Any, palette: dict[str, str]) -> str | None:
    if value is None:
        return None
    v = str(value)
    if v in palette:
        return palette[v]
    try:
        return _hex(v)
    except ValueError:
        return None


def load_brand(path: Path | str | None = None, mode: str = "light") -> Tokens:
    """Read a brand file into :class:`Tokens`.

    `mode` selects the `light` or `dark` side of a unified brand file; a
    single-mode file is used as is.
    """
    p = Path(path) if path else find_brand()
    if p is None:
        raise FileNotFoundError("no _brand.yml found; pass a path or set LECTUREKIT_BRAND")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return tokens_from_dict(data, name=None, path=p, mode=mode)


def _mode_value(v: Any, mode: str) -> Any:
    if isinstance(v, dict) and ("light" in v or "dark" in v) and set(v) <= {"light", "dark"}:
        return v.get(mode, v.get("light"))
    return v


def tokens_from_dict(data: dict[str, Any], name: str | None, path: Path | None, mode: str = "light") -> Tokens:
    meta = data.get("meta") or {}
    meta_name = meta.get("name")
    if isinstance(meta_name, dict):
        meta_name = meta_name.get("short") or meta_name.get("full")
    brand_name = name or meta_name or "brand"
    color = data.get("color") or {}
    palette: dict[str, str] = {}
    for k, v in (color.get("palette") or {}).items():
        v = _mode_value(v, mode)
        try:
            palette[str(k)] = _hex(str(v))
        except ValueError:
            pass
    colors = dict(palette)
    for k in SEMANTIC_COLORS:
        if k in color:
            r = _resolve(_mode_value(color[k], mode), palette)
            if r:
                colors[k] = r
    typography = data.get("typography") or {}
    fonts: dict[str, FontFace] = {}
    for f in typography.get("fonts") or []:
        if isinstance(f, dict) and f.get("family"):
            fonts[f["family"]] = FontFace(family=f["family"], source=f.get("source", "system"),
                                         files=list(f.get("files") or []))

    def fam(key: str) -> str | None:
        v = typography.get(key)
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return v.get("family")
        return None

    base = typography.get("base")
    base_size = base.get("size") if isinstance(base, dict) else None
    headings = typography.get("headings")
    heading_weight = headings.get("weight") if isinstance(headings, dict) else None
    return Tokens(
        name=str(brand_name), path=path, colors=colors,
        base_font=fam("base"), heading_font=fam("headings"), mono_font=fam("monospace"),
        fonts=fonts, base_size=base_size, mode=mode,
        heading_weight=None if heading_weight is None else str(heading_weight),
    )


# ---------------------------------------------------------------------- command
def write_tokens(project: Path, brand: Path | None = None, mode: str = "light",
                 out_dir: Path | None = None, manim8_version: str | None = None, select: bool = True) -> list[Path]:
    """Write tokens.tex, tokens.css and tokens.py (and the manim8 styles) for a project."""
    brand_path = brand or brand_for_mode(project, mode, env=False) or (project / "_brand.yml")
    t = load_brand(brand_path, mode=mode)
    out = out_dir or (project / "_lecturekit")
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for fname, text in (("tokens.tex", t.latex()), ("tokens.css", t.css()), ("tokens.py", t.python())):
        (out / fname).write_text(text, encoding="utf-8")
        written.append(out / fname)
    (out / "tokens.json").write_text(json.dumps({"brand": t.name, "mode": t.mode, "colors": t.colors,
                                                 "fonts": {"base": t.base_font, "headings": t.heading_font,
                                                           "monospace": t.mono_font}}, indent=2), encoding="utf-8")
    written.append(out / "tokens.json")
    if manim8_version:
        written += write_manim8_styles(project, manim8_version, brand=brand, mode=mode if brand else None,
                                       select=select)
    return written


# ------------------------------------------------------------------ the manim8 bridge
SKIP_DIRS = {"renders", ".scianim", ".venv", "code", "proposals", "feedback", "node_modules", "__pycache__"}


def manim8_workspace(project: Path) -> Path | None:
    """The project's manim8 workspace, `clips/`, when it exists."""
    ws = Path(project) / "clips"
    return ws if ws.is_dir() else None


def manim8_styles_dir(project: Path) -> Path:
    """Where bridged styles go: the workspace's `clips/styles/` when `clips/` exists, else `<project>/styles/`
    (manim8 searches every `styles/` directory above a project)."""
    ws = manim8_workspace(project)
    return (ws / "styles") if ws else (Path(project) / "styles")


def manim8_presets(project: Path, brand: Path | None = None, mode: str | None = None) -> list[tuple[Path, str]]:
    """(brand file, mode) of each preset a project has: the paper brand, and the dark one where it exists."""
    if brand:
        return [(Path(brand), mode or "light")]
    light = brand_for_mode(project, "light", env=False) or (Path(project) / "_brand.yml")
    presets = [(light, "light")]
    dark = brand_for_mode(project, "dark", env=False)
    if dark is not None and (Path(dark).resolve() != Path(light).resolve() or is_unified(light)):
        presets.append((Path(dark), "dark"))
    return presets


def bridged_style(project: Path, mode: str = "light", brand: Path | None = None) -> str | None:
    """`name@version` of the newest bridged style of the project's preset in `mode`, or None."""
    path = brand or brand_for_mode(project, mode)
    if path is None or not Path(path).exists():
        return None
    name = style_name(load_brand(path, mode=mode), mode)
    best: tuple[int, ...] | None = None
    for base in (Path(project) / "clips" / "styles", Path(project) / "styles"):
        for sheet in base.glob(f"{name}/*/style.yaml"):
            v = sheet.parent.name
            if re.fullmatch(r"\d+\.\d+\.\d+", v):
                key = tuple(int(x) for x in v.split("."))
                best = key if best is None or key > best else best
    return f"{name}@{'.'.join(map(str, best))}" if best else None


def write_manim8_styles(project: Path, version: str, brand: Path | None = None, mode: str | None = None,
                        select: bool = True) -> list[Path]:
    """Write the bridged style of each preset into the workspace's styles, and select the paper one in every
    manim8 project and family of the project. A version is written once: other content under an existing
    version is refused, since manim8 treats a style change as a new version."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"a manim8 style version is X.Y.Z, not {version!r}")
    styles = manim8_styles_dir(project)
    written: list[Path] = []
    paper: str | None = None
    for path, m in manim8_presets(project, brand, mode):
        t = load_brand(path, mode=m)
        name = style_name(t, m)
        text = t.manim8_style(version, name=name)
        dest = styles / name / version / "style.yaml"
        if dest.exists() and dest.read_text(encoding="utf-8") != text:
            raise ValueError(f"{dest} exists with other content; manim8 styles are written once per version, so "
                             f"pass a new version (lk theme --manim8 X.Y.Z)")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        written.append(dest)
        if m == "light":
            paper = name
    if select and paper:
        written += select_manim8_style(project, paper, version)
    return written


def _manim8_files(root: Path, filename: str) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        if filename in filenames:
            found.append(Path(dirpath) / filename)
    return found


def _style_of(path: Path) -> tuple[str | None, str | None]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    st = data.get("style") or {}
    return (st.get("name"), None if st.get("version") is None else str(st.get("version"))) if isinstance(st, dict) \
        else (None, None)


def set_style_block(path: Path, name: str, version: str) -> None:
    """Point the top-level `style:` block of an animation.yaml or family.yaml at `name@version`, keeping the
    rest of the file as written."""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"(?m)^style:[ \t]*\n((?:[ \t]+.*(?:\n|$)|[ \t]*\n)*)", text)
    if m and re.search(r"(?m)^[ \t]+name:", m.group(1)) and re.search(r"(?m)^[ \t]+version:", m.group(1)):
        block = re.sub(r"(?m)^([ \t]+name:)[ \t]*.*$", lambda g: f"{g.group(1)} {name}", m.group(1), count=1)
        block = re.sub(r"(?m)^([ \t]+version:)[ \t]*.*$", lambda g: f'{g.group(1)} "{version}"', block, count=1)
        path.write_text(text[:m.start(1)] + block + text[m.end(1):], encoding="utf-8")
        return
    data = yaml.safe_load(text) or {}
    style = data.get("style") if isinstance(data.get("style"), dict) else {}
    style.update({"name": name, "version": version})
    data["style"] = style
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _propose_style(exe: str, project_dir: Path, name: str, version: str) -> tuple[bool, str]:
    """Select a style through `scianim propose apply`, so that manim8 validates the change and records its diff."""
    from .clips import run_tool
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dt%H%M%S")
    ident = f"prop_lk_style_{stamp}_{name}_{version.replace('.', '_')}"[:69]
    proposal = {
        "schema_version": "1.0",
        "id": ident,
        "kind": "revise_spec",
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "author": "lecturekit (lk theme --manim8)",
        "summary": f"Use the bridged lecturekit style {name}@{version}",
        "rationale": "The deck's brand, mapped onto manim8's palette roles by `lk theme --manim8`, so that the "
                     "clip matches the slides it sits on.",
        "targets": [{"file": "animation.yaml", "patch": [
            {"op": "replace", "path": "/style/name", "value": name},
            {"op": "replace", "path": "/style/version", "value": version},
        ]}],
    }
    with tempfile.TemporaryDirectory(prefix="lk-style-") as tmp:
        f = Path(tmp) / f"{ident}.yaml"
        f.write_text(yaml.safe_dump(proposal, sort_keys=False), encoding="utf-8")
        rc, _, reason = run_tool([exe, "propose", "apply", str(project_dir), str(f)], quiet=True)
    return rc == 0, reason


def select_manim8_style(project: Path, name: str, version: str) -> list[Path]:
    """Select `name@version` in every `clips/families/**/animation.yaml` (through `scianim propose apply` when
    manim8 is installed, else by editing the file) and in every `family.yaml`. Returns the files changed."""
    families = Path(project) / "clips" / "families"
    if not families.is_dir():
        return []
    from .clips import scianim_exe
    exe = scianim_exe(required=False)
    changed: list[Path] = []
    for anim in _manim8_files(families, "animation.yaml"):
        if _style_of(anim) == (name, version):
            continue
        if exe:
            ok, reason = _propose_style(exe, anim.parent, name, version)
            if not ok:
                print(f"lecturekit: could not select {name}@{version} in {anim}: {reason}", file=sys.stderr)
                continue
        else:
            set_style_block(anim, name, version)
        changed.append(anim)
    for fam in _manim8_files(families, "family.yaml"):
        if _style_of(fam) != (name, version):
            set_style_block(fam, name, version)
            changed.append(fam)
    if changed and not exe:
        print("lecturekit: manim8 is not installed; the style was set in animation.yaml directly, without a "
              "proposal record", file=sys.stderr)
    return changed
