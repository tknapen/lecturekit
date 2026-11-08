-- tikz.lua
-- TikZ figures for both outputs, compiled once and cached.
--
-- Two ways to put a figure on a slide:
--
--   ```{.tikz height=4.2cm}
--   \begin{tikzpicture} ... \end{tikzpicture}
--   ```
--
--   ![](assets/figures/pipeline.tikz){height=4.2cm}      a file written by make_assets.py
--
-- The picture is compiled with xelatex into a standalone PDF using the deck's
-- fonts and the brand colour tokens (nmInk, nmConcept, ...), then converted
-- to SVG for the live deck (filters/tikz2svg.py, PyMuPDF). The study PDF
-- includes the PDF through \lkfigureh, which never upscales; the live deck
-- gets an <img> with the same maximum height, at 80 px per cm.
--
-- Cache: _lecturekit/tikz/<sha1>.{tex,pdf,svg} beside the source. A figure
-- that fails to compile becomes a labelled placeholder so the deck builds;
-- the log is kept beside the cache entry.

local is_live = quarto.doc.is_format("revealjs")
local is_study = quarto.doc.is_format("beamer") or quarto.doc.is_format("latex")

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
local ext_dir = dirname(debug.getinfo(1, "S").source:sub(2))      -- .../filters
local preamble_path = ext_dir .. "/../beamer/figure-preamble.tex"
local tikz2svg = ext_dir .. "/tikz2svg.py"

package.path = ext_dir .. "/?.lua;" .. package.path
local brand = require("lkbrand")

local function standalone_tex(body)
  local pre = read_file(preamble_path) or ""
  return table.concat({
    "\\documentclass[tikz,border=2pt]{standalone}",
    "\\usepackage{fontspec}",
    table.concat(brand.font_lines(), "\n"),
    "\\usepackage{xcolor}",
    brand.latex_colors(),
    pre,
    "\\begin{document}",
    body,
    "\\end{document}",
    "",
  }, "\n")
end

local function compile(body, label)
  local src = standalone_tex(body)
  local key = pandoc.utils.sha1(src)
  os.execute(string.format("mkdir -p '%s'", cache_dir))
  local base = cache_dir .. "/" .. key
  if not file_exists(base .. ".pdf") then
    write_file(base .. ".tex", src)
    local ok = pcall(pandoc.pipe, "xelatex",
      { "-interaction=batchmode", "-halt-on-error", "-output-directory", cache_dir, base .. ".tex" }, "")
    if not ok or not file_exists(base .. ".pdf") then
      io.stderr:write(string.format("lecturekit: TikZ figure '%s' failed; see %s.log\n", label, base))
      return nil
    end
  end
  if is_live and not file_exists(base .. ".svg") then
    local ok = pcall(pandoc.pipe, "python3", { tikz2svg, base .. ".pdf", base .. ".svg" }, "")
    if not ok or not file_exists(base .. ".svg") then
      io.stderr:write(string.format("lecturekit: SVG conversion failed for '%s'\n", label))
      return nil
    end
  end
  return base
end

local function relative(path)
  -- paths in the output are relative to the source directory
  local prefix = input_dir .. "/"
  if path:sub(1, #prefix) == prefix then return path:sub(#prefix + 1) end
  return path
end

-- the SVG's intrinsic size in pt, from its root element
local function svg_size_pt(path)
  local s = read_file(path)
  if not s then return nil end
  local head = s:sub(1, 600)
  local w = tonumber(head:match('width="([%d%.]+)'))
  local h = tonumber(head:match('height="([%d%.]+)'))
  if w and h then return w, h end
  return nil
end

local PX_PER_PT = 80 / 28.4528   -- 1 cm of the Beamer frame is 80 px of the live frame

local function height_px(h)
  if not h then return nil end
  local cm = tonumber(tostring(h):match("^([%d%.]+)cm$"))
  if cm then return math.floor(cm * 80 + 0.5) end
  return tonumber(tostring(h):match("^([%d%.]+)px$"))
end

local function live_style(base, h)
  local parts = { "width:auto" }
  local _, hpt = svg_size_pt(base .. ".svg")
  if hpt then parts[#parts + 1] = string.format("height:%dpx", math.floor(hpt * PX_PER_PT + 0.5)) end
  local px = height_px(h)
  if px then parts[#parts + 1] = string.format("max-height:%dpx", px) end
  return table.concat(parts, ";")
end

local function figure_blocks(base, attrs, label, caption)
  local h = attrs["height"]
  if is_live then
    local style = string.format(' style="%s"', live_style(base, h))
    local html = string.format('<div class="lk-figure"><img class="lk-tikz" src="%s" alt="%s"%s></div>',
      relative(base .. ".svg"), label, style)
    return pandoc.RawBlock("html", html)
  end
  if is_study then
    return pandoc.RawBlock("latex", string.format("\\lkfigureh{%s}{%s}", h or "4.2cm", relative(base .. ".pdf")))
  end
  return nil
end

local function placeholder(attrs, label)
  local h = attrs["height"] or "4.2cm"
  if is_live then
    local px = height_px(h) or 336
    return pandoc.RawBlock("html",
      string.format('<div class="lk-figure lk-placeholder" style="height:%dpx">figure missing: %s</div>', px, label))
  end
  if is_study then
    return pandoc.RawBlock("latex", string.format("\\lkplaceholder{%s}{figure: %s}", h, label))
  end
end

local function CodeBlock(el)
  if not el.classes:includes("tikz") then return nil end
  local label = el.attributes["label"] or el.identifier or "inline tikz"
  local base = compile(el.text, label)
  if not base then return placeholder(el.attributes, label) end
  return figure_blocks(base, el.attributes, label)
end

local function Image(img)
  local src = img.src
  if not (src:match("%.tikz$") or src:match("%.tikz%.tex$")) then return nil end
  local path = input_dir .. "/" .. src
  local body = read_file(path)
  if not body then
    io.stderr:write("lecturekit: TikZ file not found: " .. src .. "\n")
    return nil
  end
  local base = compile(body, src)
  if not base then
    -- an Image is inline; wrap the placeholder into a Span-compatible form
    if is_live then
      local px = height_px(img.attributes["height"]) or 336
      return pandoc.RawInline("html",
        string.format('<div class="lk-figure lk-placeholder" style="height:%dpx">figure missing: %s</div>', px, src))
    else
      return pandoc.RawInline("latex",
        string.format("\\lkplaceholder{%s}{figure: %s}", img.attributes["height"] or "4.2cm", src))
    end
  end
  if is_live then
    img.src = relative(base .. ".svg")
    local style = live_style(base, img.attributes["height"])
    img.attributes["height"] = nil
    img.classes:insert("lk-tikz")
    img.attributes["style"] = style
    return img
  end
  if is_study then
    return pandoc.RawInline("latex",
      string.format("\\lkfigureh{%s}{%s}", img.attributes["height"] or "4.2cm", relative(base .. ".pdf")))
  end
end

return { { CodeBlock = CodeBlock, Image = Image } }
