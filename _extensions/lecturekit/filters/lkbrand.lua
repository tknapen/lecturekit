-- lkbrand.lua
-- Reads the active brand (_brand.yml, light or dark) that Quarto hands to
-- filters and turns it into tokens for each output. Shared by dual-output.lua,
-- tikz.lua and tokens.lua.
--
--   mode()           -> "dark" or "light": the brand mode of this build
--   colors()         -> { name = "#RRGGBB", ... }  palette entries and semantic names
--   camel(name)      -> LaTeX-safe name part: "role-concept" -> "RoleConcept"
--   latex_colors()   -> \definecolor{nm<Name>}{HTML}{..} lines
--   font_lines()     -> fontspec lines: the serif (headings) family as the main
--                       font, the sans (base) family as the sans font, the two
--                       letterspaced families of the theme, and the math font
--   latex_block()    -> colours and fonts together (tokens.tex)
--   css_block()      -> ":root{--nm-<name>:..;}"
--
-- Fonts: a family declared in _brand.yml with `source: file` is loaded from
-- its files (resolved against the brand file's directory). The engine's own
-- families, TeX Gyre Heros, TeX Gyre Pagella and Roboto, are bundled in the
-- extension's fonts/ directory and used by file whatever the source says, so
-- that a build needs no installed font. Any other family is loaded by name
-- through fontspec and must be installed on the machine.

local M = {}

local script_dir = debug.getinfo(1, "S").source:sub(2):match("^(.*)[/\\]") or "."
M.ext_dir = pandoc.path.directory(script_dir)
M.fonts_dir = pandoc.path.join({ M.ext_dir, "fonts" })

function M.camel(name)
  return (name:gsub("^%l", string.upper):gsub("[-_](%w)", function(c) return c:upper() end))
end

local function sorted_keys(t)
  local keys = {}
  for k in pairs(t) do keys[#keys + 1] = k end
  table.sort(keys)
  return keys
end

-- "dark" when the build's brand mode is dark (brand-mode: dark, as the dark profile sets it), else "light"
local function mode()
  local ok, m = pcall(function() return param("brand-mode") end)
  if ok and m == "dark" then return "dark" end
  return "light"
end
M.mode = mode

function M.raw()
  local ok, b = pcall(function() return param("brand") end)
  if not ok or b == nil then return nil end
  local m = mode()
  if not b[m] then m = "light" end
  return b[m]
end

function M.data()
  local b = M.raw()
  return b and b.processedData or nil
end

function M.brand_dir()
  local b = M.raw()
  return b and (b.brandDir or b.projectDir) or nil
end

function M.colors()
  local out = {}
  local b = M.data()
  if not b or not b.color then return out end
  for name, value in pairs(b.color) do
    if type(value) == "string" and name ~= "palette" then out[name] = value end
  end
  if type(b.color.palette) == "table" then
    for name, value in pairs(b.color.palette) do
      if type(value) == "string" then out[name] = value end
    end
  end
  return out
end

-- --------------------------------------------------------------------------
-- Fonts
-- --------------------------------------------------------------------------
local BUNDLED = {
  ["TeX Gyre Heros"] = { dir = "", r = "texgyreheros-regular.otf", b = "texgyreheros-bold.otf",
                         ri = "texgyreheros-italic.otf", bi = "texgyreheros-bolditalic.otf" },
  ["TeX Gyre Pagella"] = { dir = "", r = "texgyrepagella-regular.otf", b = "texgyrepagella-bold.otf",
                           ri = "texgyrepagella-italic.otf", bi = "texgyrepagella-bolditalic.otf" },
  ["Roboto"] = { dir = "roboto", r = "Roboto-Regular.ttf", b = "Roboto-Bold.ttf",
                 ri = "Roboto-Italic.ttf", bi = "Roboto-BoldItalic.ttf" },
}
M.MATH_FONT = "texgyrepagella-math.otf"

local function family_of(entry)
  if type(entry) == "string" then return entry end
  if type(entry) == "table" then return entry.family end
  return nil
end

local function absolute(path, base)
  if pandoc.path.is_absolute(path) then return path end
  if base then return pandoc.path.join({ base, path }) end
  return path
end

-- the files of a `source: file` family in the brand, by face: r, b, ri, bi
local function brand_faces(typography, family)
  if not typography or type(typography.fonts) ~= "table" then return nil end
  for _, f in ipairs(typography.fonts) do
    if type(f) == "table" and f.family == family and f.source == "file" and type(f.files) == "table" then
      local by = {}
      for _, file in ipairs(f.files) do
        local path = type(file) == "string" and file or file.path
        local weight = type(file) == "table" and tostring(file.weight or "400") or "400"
        local style = type(file) == "table" and (file.style or "normal") or "normal"
        local bold = (weight == "bold" or weight == "semibold" or (tonumber(weight) or 400) >= 600)
        local key = (bold and "b" or "r") .. (style == "italic" and "i" or "")
        if path and not by[key] then by[key] = absolute(path, M.brand_dir()) end
      end
      if by.r or by.b then return by end
    end
  end
  return nil
end

-- faces of a family: from the brand's files, else from the bundle, else nil (load by name)
function M.faces(family, typography)
  local by = brand_faces(typography, family)
  if by then return by end
  local bundled = BUNDLED[family]
  if bundled then
    local dir = bundled.dir ~= "" and pandoc.path.join({ M.fonts_dir, bundled.dir }) or M.fonts_dir
    return { r = pandoc.path.join({ dir, bundled.r }), b = pandoc.path.join({ dir, bundled.b }),
             ri = pandoc.path.join({ dir, bundled.ri }), bi = pandoc.path.join({ dir, bundled.bi }) }
  end
  return nil
end

-- "{upright file}[Path=dir/,BoldFont=..,ItalicFont=..,BoldItalicFont=..,<extra>]" or "{Family}[<extra>]"
function M.fontspec_args(family, typography, extra)
  local by = M.faces(family, typography)
  local opts = {}
  if by then
    local upright = by.r or by.b
    local dir, base = pandoc.path.directory(upright), pandoc.path.filename(upright)
    opts[#opts + 1] = "Path=" .. dir .. "/"
    if by.b then opts[#opts + 1] = "BoldFont=" .. pandoc.path.filename(by.b) end
    if by.ri then opts[#opts + 1] = "ItalicFont=" .. pandoc.path.filename(by.ri) end
    if by.bi then opts[#opts + 1] = "BoldItalicFont=" .. pandoc.path.filename(by.bi) end
    if upright:match("%.otf$") then opts[#opts + 1] = "Ligatures=TeX" end
    if extra then opts[#opts + 1] = extra end
    return string.format("{%s}[%s]", base, table.concat(opts, ","))
  end
  if extra then return string.format("{%s}[%s]", family, extra) end
  return string.format("{%s}", family)
end

-- the two families of a brand: serif (headings) and sans (body); the engine's defaults when absent
function M.families()
  local b = M.data()
  local ty = b and b.typography or {}
  local serif = family_of(ty.headings) or "TeX Gyre Pagella"
  local sans = family_of(ty.base) or "TeX Gyre Heros"
  return serif, sans, ty
end

function M.font_lines()
  local serif, sans, ty = M.families()
  local lines = {
    "\\setmainfont" .. M.fontspec_args(serif, ty),
    "\\setsansfont" .. M.fontspec_args(sans, ty),
    -- Letterspaced capitals: titles breathe at 2% of the em, small labels at 8%. Separate families on purpose:
    -- \addfontfeature on a family with a fixed NFSSFamily rewrites that family globally.
    "\\newfontfamily\\nmSerifCaps" .. M.fontspec_args(serif, ty, "LetterSpace=2.0"),
    "\\newfontfamily\\nmSansCaps" .. M.fontspec_args(sans, ty, "LetterSpace=8.0"),
    string.format("\\setmathfont{%s}[Path=%s/]", M.MATH_FONT, M.fonts_dir),
  }
  return lines
end

-- CSS @font-face rules for the bundled families the brand names, for the live deck when the brand does not
-- declare files itself (Quarto writes its own rules for `source: file` families)
function M.font_face_css(url_prefix)
  local serif, sans, ty = M.families()
  local out = {}
  for _, fam in ipairs({ serif, sans }) do
    if BUNDLED[fam] and not brand_faces(ty, fam) then
      local b = BUNDLED[fam]
      local dir = b.dir ~= "" and (b.dir .. "/") or ""
      for key, weight, style in (function() local i = 0; local t = { { "r", 400, "normal" }, { "b", 700, "normal" }, { "ri", 400, "italic" }, { "bi", 700, "italic" } }
        return function() i = i + 1; if t[i] then return t[i][1], t[i][2], t[i][3] end end end)() do
        local file = b[key]
        local fmt = file:match("%.otf$") and "opentype" or "truetype"
        out[#out + 1] = string.format('@font-face{font-family:"%s";src:url("%s%s%s") format("%s");font-weight:%d;font-style:%s;}',
          fam, url_prefix, dir, file, fmt, weight, style)
      end
    end
  end
  return table.concat(out, "\n")
end

-- --------------------------------------------------------------------------
-- Blocks
-- --------------------------------------------------------------------------
function M.latex_colors()
  local colors = M.colors()
  local lines = {}
  for _, k in ipairs(sorted_keys(colors)) do
    local hex = colors[k]:gsub("^#", "")
    if #hex == 6 then
      lines[#lines + 1] = string.format("\\definecolor{nm%s}{HTML}{%s}", M.camel(k), hex:upper())
    end
  end
  return table.concat(lines, "\n")
end

-- the named TikZ styles of beamer/tikz-styles.tex, for the study PDF and the standalone figures alike
function M.tikz_styles()
  local f = io.open(pandoc.path.join({ M.ext_dir, "beamer", "tikz-styles.tex" }), "r")
  if not f then return "" end
  local s = f:read("a"); f:close()
  return s
end

function M.latex_block()
  local parts = { "% colour and font tokens from _brand.yml (written by lecturekit; do not edit)" }
  local c = M.latex_colors()
  if c ~= "" then parts[#parts + 1] = c end
  for _, l in ipairs(M.font_lines()) do parts[#parts + 1] = l end
  parts[#parts + 1] = "\\usepackage{tikz}\\usetikzlibrary{arrows.meta,positioning,calc,fit,backgrounds,shapes.geometric,decorations.pathreplacing}"
  parts[#parts + 1] = M.tikz_styles()
  return table.concat(parts, "\n") .. "\n"
end

function M.css_block()
  local colors = M.colors()
  local keys = sorted_keys(colors)
  if #keys == 0 then return "" end
  local lines = { ":root{" }
  for _, k in ipairs(keys) do
    lines[#lines + 1] = string.format("--nm-%s:%s;", k, colors[k])
  end
  lines[#lines + 1] = "}"
  return table.concat(lines, "")
end

return M
