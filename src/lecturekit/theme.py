"""The theme: `_brand.yml` read once, tokens written for every consumer.

A deck's look is defined in one place, Quarto's `_brand.yml`. Quarto applies
it to the live deck itself. Everything else that needs the same values reads
it through this module:

* the Beamer side, as `\\definecolor{nm<Name>}` lines and fontspec lines
  (`tokens.tex`), also written by the Lua filter at render time;
* the live deck, as `--nm-<name>` CSS variables (`tokens.css`);
* Python code (TikZ figures, Manim clips), as `tokens.py` or directly through
  :func:`load_brand`;
* manim8, as a versioned style that inherits `default@0.5.0`.

Names: a palette entry `ink` becomes `nmInk`, `--nm-ink` and `INK`; a
multi-word entry `role-concept` becomes `nmRoleConcept`, `--nm-role-concept`
and `ROLE_CONCEPT`.
"""

from __future__ import annotations

import json
import os
import re
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

    def manim8_style(self, version: str, inherits: str = "default@0.5.0") -> str:
        """A manim8 style version mapping the brand onto manim8's palette roles.

        manim8's rule is that a style change is a new version, never an edit;
        the caller chooses the version string.
        """
        c = self.colors
        def pick(*names: str, default: str) -> str:
            for n in names:
                if n in c:
                    return c[n]
            return default
        palette = {
            "background": pick("slide", "background", default="#FFFFFF"),
            "foreground": pick("ink", "foreground", default="#202B33"),
            "secondary_text": pick("muted", default="#566573"),
            "muted": pick("hairline", "muted", default="#C8C3BA"),
            "primary_signal": pick("input", "concept", default="#0072B2"),
            "normalization_pool": pick("update", "example", default="#C45A00"),
            "emphasis": pick("concept", "primary", default="#175B8E"),
            "warning": pick("caveat", "danger", default="#A33A32"),
            "comparison": pick("context", "question", default="#7A5195"),
            "neutral": pick("muted", default="#566573"),
        }
        # project tokens beyond the roles travel as extra palette entries
        for name in sorted(c):
            key = name.replace("-", "_")
            if key not in palette and name not in SEMANTIC_COLORS:
                palette[key] = c[name]
        typography = {}
        head = self.heading_font or self.base_font
        fonts = [f for f in (self.base_font, "TeX Gyre Heros", "Helvetica", "sans-serif") if f]
        for role, fam in (("title", head), ("body", self.base_font), ("annotation", self.base_font),
                          ("axis_label", self.base_font), ("tick_label", self.base_font), ("caption", self.base_font)):
            if fam:
                typography[role] = {"font_family": fam, "font_fallbacks": [f for f in fonts if f != fam]}
        doc = {
            "schema_version": "1.0",
            "name": re.sub(r"[^a-z0-9_-]", "-", self.name.lower()),
            "version": version,
            "description": f"lecturekit brand {self.name!r} ({self.mode}) mapped onto manim8 palette roles; "
                           "written by `lk theme --manim8`, a new version per change.",
            "inherits": inherits,
            "palette": palette,
            "typography": typography,
        }
        return yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)


# ---------------------------------------------------------------------- loading
def find_brand(start: Path | None = None) -> Path | None:
    """The nearest `_brand.yml` walking up from `start` (or `LECTUREKIT_BRAND`)."""
    env = os.environ.get("LECTUREKIT_BRAND")
    if env:
        return Path(env)
    here = (start or Path.cwd()).resolve()
    for d in [here, *here.parents]:
        p = d / "_brand.yml"
        if p.exists():
            return p
    return None


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
    return Tokens(
        name=str(brand_name), path=path, colors=colors,
        base_font=fam("base"), heading_font=fam("headings"), mono_font=fam("monospace"),
        fonts=fonts, base_size=base_size, mode=mode,
    )


# ---------------------------------------------------------------------- command
def write_tokens(project: Path, brand: Path | None = None, mode: str = "light",
                 out_dir: Path | None = None, manim8_version: str | None = None) -> list[Path]:
    """Write tokens.tex, tokens.css and tokens.py (and a manim8 style) for a project."""
    brand_path = brand or (project / "_brand.yml")
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
        style_dir = project / "styles" / re.sub(r"[^a-z0-9_-]", "-", t.name.lower()) / manim8_version
        style_dir.mkdir(parents=True, exist_ok=True)
        (style_dir / "style.yaml").write_text(t.manim8_style(manim8_version), encoding="utf-8")
        written.append(style_dir / "style.yaml")
    return written
