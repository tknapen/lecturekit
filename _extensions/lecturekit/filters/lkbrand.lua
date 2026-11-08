-- lkbrand.lua
-- Reads the active brand (_brand.yml, light or dark) that Quarto hands to
-- filters and turns it into tokens for each output. Shared by tokens.lua
-- and tikz.lua.
--
--   colors()      -> { name = "#RRGGBB", ... }   palette entries and semantic names
--   camel(name)   -> LaTeX-safe name part: "role-concept" -> "RoleConcept"
--   latex_block() -> \definecolor{nm<Name>}{HTML}{..} lines and fontspec lines
--   css_block()   -> ":root{--nm-<name>:..;}"
--   font_lines()  -> fontspec lines from the brand's typography

local M = {}

function M.camel(name)
  return (name:gsub("^%l", string.upper):gsub("[-_](%w)", function(c) return c:upper() end))
end

local function sorted_keys(t)
  local keys = {}
  for k in pairs(t) do keys[#keys + 1] = k end
  table.sort(keys)
  return keys
end

function M.data()
  local ok, brand = pcall(function() return param("brand") end)
  if not ok or brand == nil then return nil end
  local mode = "light"
  local ok2, m = pcall(function() return param("brand-mode") end)
  if ok2 and m == "dark" and brand.dark then mode = "dark" end
  return brand[mode] and brand[mode].processedData or nil
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

local function family_of(entry)
  if type(entry) == "string" then return entry end
  if type(entry) == "table" then return entry.family end
  return nil
end

-- files of a `source: file` family, by weight and style: r, b, ri, bi
local function font_files(typography, family)
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
        if path and not by[key] then by[key] = path end
      end
      return by
    end
  end
  return nil
end

local function fontspec_args(by)
  local upright = by.r or by.b or by.ri or by.bi
  if not upright then return nil end
  local dir, base = upright:match("^(.*)/([^/]+)$")
  if not dir then dir, base = ".", upright end
  local function basename(p) return p and (p:match("([^/]+)$")) or nil end
  local o = { "Path=" .. dir .. "/" }
  if by.b then o[#o + 1] = "BoldFont=" .. basename(by.b) end
  if by.ri then o[#o + 1] = "ItalicFont=" .. basename(by.ri) end
  if by.bi then o[#o + 1] = "BoldItalicFont=" .. basename(by.bi) end
  return string.format("{%s}[%s]", base, table.concat(o, ","))
end

function M.font_lines()
  local b = M.data()
  local ty = b and b.typography
  if not ty then return {} end
  local lines = {}
  local base = family_of(ty.base)
  local head = family_of(ty.headings)
  if base then
    local files = font_files(ty, base)
    local args = files and fontspec_args(files) or string.format("{%s}", base)
    lines[#lines + 1] = "\\setmainfont" .. args
    lines[#lines + 1] = "\\setsansfont" .. args
  end
  if head then
    local files = font_files(ty, head)
    local args = files and fontspec_args(files) or string.format("{%s}", head)
    lines[#lines + 1] = "\\newfontfamily\\lkheadfont" .. args
  end
  return lines
end

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

function M.latex_block()
  local parts = { "% colour and font tokens from _brand.yml (written by lecturekit; do not edit)" }
  local c = M.latex_colors()
  if c ~= "" then parts[#parts + 1] = c end
  for _, l in ipairs(M.font_lines()) do parts[#parts + 1] = l end
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
