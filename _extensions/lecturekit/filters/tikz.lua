-- tikz.lua
-- TikZ figures in the browser; the study PDF sets them inline.
--
-- Four ways to put a figure on a slide:
--
--   \nmfigureh{4.2cm}{assets/figures/name.tex}      a figure file beside the deck, height-capped (raw LaTeX)
--   \nmfigure{assets/figures/name.tex}               the same, width-capped only
--   ![](assets/figures/name.tex){height=4.2cm}       the same file as an image link (.tex or .tikz)
--   ```{.tikz height=3.6cm}                          the picture inline
--   \begin{tikzpicture} ... \end{tikzpicture}
--   ```
--
-- Study PDF: the raw forms stay as they are (lecturekit.tex defines \nmfigureh
-- and \nmfigure, which input the file and scale it down to the text width and
-- the height, never up); the image and fenced forms become \nmfigureh too, the
-- fenced picture through a file in _lecturekit/tikz/.
--
-- Live deck: each picture becomes a standalone document with the deck's fonts
-- and colour tokens (figure-preamble.tex), compiled with xelatex and converted
-- to an SVG with text as paths, so the browser needs no fonts. The SVG keeps
-- the figure's proportion on the study page (1280 px for the 453.54 pt frame)
-- and the slide gets <img class="tikz">; a height cap carries over as
-- max-height at 8.8 px per mm. Figures are rebuilt only when their source
-- changes (the cache key is a hash of the standalone source). A figure that
-- fails to compile becomes a labelled placeholder, so the deck builds; its
-- log stays in _lecturekit/tikz/.

local script_dir = debug.getinfo(1, "S").source:sub(2):match("^(.*)[/\\]") or "."
package.path = script_dir .. "/?.lua;" .. package.path
local brand = require("lkbrand")

local live = quarto.doc.is_format("revealjs")
local study = quarto.doc.is_format("beamer") or quarto.doc.is_format("latex")

local function dirname(p) return p:match("^(.*)[/\\]") or "." end
local function read_file(p)
  local f = io.open(p, "r"); if not f then return nil end
  local s = f:read("a"); f:close(); return s
end
local function write_file(p, s)
  local f = assert(io.open(p, "w")); f:write(s); f:close()
end
local function file_exists(p)
  local f = io.open(p, "r"); if f then f:close(); return true end; return false
end

local input_dir = quarto.doc.input_file and dirname(quarto.doc.input_file) or "."
local cache_dir = input_dir .. "/_lecturekit/tikz"
local preamble_path = pandoc.path.join({ brand.ext_dir, "beamer", "figure-preamble.tex" })
local tikz2svg = pandoc.path.join({ script_dir, "tikz2svg.py" })
local figure_ext = os.getenv("NM_FIGURE_FORMAT") or "svg"

local PX_PER_MM = 8.8

local function standalone(body)
  local pre = read_file(preamble_path) or ""
  return table.concat({
    "\\documentclass[12pt,tikz,border=1pt]{standalone}",
    "\\usepackage{amsmath}",
    "\\usepackage{fontspec}",
    "\\usepackage{unicode-math}",
    table.concat(brand.font_lines(), "\n"),
    brand.latex_colors(),
    "\\usepackage{tikz}",
    brand.tikz_styles(),
    pre,
    "\\begin{document}",
    body,
    "\\end{document}",
    "",
  }, "\n")
end

-- compile a picture (its full LaTeX body) once; returns the cache base path or nil
local function compile(body, label)
  local src = standalone(body)
  local key = pandoc.utils.sha1(src)
  pandoc.system.make_directory(cache_dir, true)
  local base = cache_dir .. "/" .. key
  if not file_exists(base .. ".pdf") then
    write_file(base .. ".tex", src)
    local ok = pcall(pandoc.pipe, "xelatex",
      { "-interaction=batchmode", "-halt-on-error", "-output-directory", cache_dir, base .. ".tex" }, "")
    if not ok or not file_exists(base .. ".pdf") then
      io.stderr:write(string.format("ERROR (lecturekit) TikZ figure '%s' failed to compile; see %s.log\n", label, base))
      return nil
    end
  end
  local target = base .. "." .. figure_ext
  if not file_exists(target) then
    -- the Python that lk build runs on (it sets QUARTO_PYTHON), so pymupdf is found without an activated venv
    local python = os.getenv("QUARTO_PYTHON") or "python3"
    local ok = pcall(pandoc.pipe, python, { tikz2svg, base .. ".pdf", target }, "")
    if not ok or not file_exists(target) then
      io.stderr:write(string.format("ERROR (lecturekit) conversion to %s failed for TikZ figure '%s' (is pymupdf installed?)\n", figure_ext, label))
      return nil
    end
  end
  return base
end

local function relative(path)
  local prefix = input_dir .. "/"
  if path:sub(1, #prefix) == prefix then return path:sub(#prefix + 1) end
  return path
end

local function cap_px(height)
  if not height then return nil end
  local cm = tonumber(tostring(height):match("^([%d%.]+)cm$"))
  local mm = tonumber(tostring(height):match("^([%d%.]+)mm$"))
  if cm then mm = cm * 10 end
  if mm then return math.floor(mm * PX_PER_MM + 0.5) end
  return tonumber(tostring(height):match("^([%d%.]+)px$"))
end

local function live_image(base, height, label)
  local attr = pandoc.Attr("", { "tikz" })
  local px = cap_px(height)
  if px then attr.attributes.style = string.format("max-height:%dpx", px) end
  return pandoc.Image({}, relative(base .. "." .. figure_ext), label or "", attr)
end

local function placeholder_block(height, label)
  if live then
    local px = cap_px(height) or 352
    return pandoc.RawBlock("html",
      string.format('<div class="lk-placeholder" style="height:%dpx">figure missing: %s</div>', px, label))
  end
  return pandoc.RawBlock("latex", string.format("\\lkplaceholder{%s}{figure: %s}", height or "4cm", label))
end

-- a picture body from a file beside the deck
local function picture_from_file(path)
  if not path:match("%.te?x$") and not path:match("%.tikz$") then path = path .. ".tex" end
  local full = pandoc.path.is_absolute(path) and path or (input_dir .. "/" .. path)
  local body = read_file(full)
  return body, path
end

-- --------------------------------------------------------------------------
-- raw LaTeX blocks: \nmfigureh{h}{file}, \nmfigure{file}, \input{file}, or an inline tikzpicture
-- --------------------------------------------------------------------------
local function RawBlock(el)
  if not live or (el.format ~= "latex" and el.format ~= "tex") then return nil end
  local text = el.text
  local path = text:match("^%s*\\input{([^}]+)}%s*$") or text:match("^%s*\\nmfigure{([^}]+)}%s*$")
    or text:match("^%s*\\nmfigureh{[^}]+}{([^}]+)}%s*$")
  local height = text:match("^%s*\\nmfigureh{([^}]+)}{[^}]+}%s*$")
  local body, label = text, "inline tikz"
  if path then
    body, label = picture_from_file(path)
    if not body then
      io.stderr:write("lecturekit: cannot read figure file " .. path .. "\n")
      return placeholder_block(height, path)
    end
  end
  if not body:find("\\begin{tikzpicture}", 1, true) then return nil end
  local base = compile(body, label)
  if not base then return placeholder_block(height, label) end
  return pandoc.Para({ live_image(base, height, label) })
end

-- --------------------------------------------------------------------------
-- image links to figure files and fenced {.tikz} blocks
-- --------------------------------------------------------------------------
local function Image(img)
  local src = img.src
  if not (src:match("%.tikz$") or src:match("%.tex$")) then return nil end
  local height = img.attributes.height
  if study then
    return pandoc.RawInline("latex", string.format("\\nmfigureh{%s}{%s}", height or "\\textheight", src))
  end
  local body = picture_from_file(src)
  if not body then
    io.stderr:write("lecturekit: cannot read figure file " .. src .. "\n")
    return pandoc.RawInline("html", string.format('<div class="lk-placeholder">figure missing: %s</div>', src))
  end
  local base = compile(body, src)
  if not base then
    return pandoc.RawInline("html", string.format('<div class="lk-placeholder">figure failed: %s</div>', src))
  end
  local out = live_image(base, height, pandoc.utils.stringify(img.caption))
  for _, c in ipairs(img.classes) do if c ~= "tikz" then out.classes:insert(c) end end
  return out
end

local function CodeBlock(el)
  if not el.classes:includes("tikz") then return nil end
  local label = el.attributes.label or el.identifier or "inline tikz"
  local height = el.attributes.height
  if study then
    -- the picture goes to a file so that \nmfigureh can input and scale it
    pandoc.system.make_directory(cache_dir, true)
    local path = cache_dir .. "/" .. pandoc.utils.sha1(el.text) .. ".tikz"
    if not file_exists(path) then write_file(path, el.text .. "\n") end
    return pandoc.RawBlock("latex", string.format("\\nmfigureh{%s}{%s}", height or "\\textheight", relative(path)))
  end
  local base = compile(el.text, label)
  if not base then return placeholder_block(height, label) end
  return pandoc.Para({ live_image(base, height, label) })
end

return { { RawBlock = RawBlock, Image = Image, CodeBlock = CodeBlock } }
