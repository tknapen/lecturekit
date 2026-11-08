-- tokens.lua
-- Puts the active brand into each output.
--
--   Beamer: writes _lecturekit/tokens.tex beside the source, with
--           \definecolor{nm<Name>}{HTML}{...} for every brand colour and the
--           fontspec lines (main, sans, the letterspaced families, math).
--           beamer/lecturekit.tex inputs that file first, so the title frame
--           gets the tokens too.
--   Reveal: inlines <style>:root{--nm-<name>: ...}</style> as the first block
--           of the deck (a <style> element is valid anywhere in the body),
--           adds @font-face rules for the bundled families when the brand
--           names them without files, and writes _lecturekit/tokens.css for
--           the review tools.
--
-- Why not header-includes or quarto.doc.include_text: in Quarto 1.11 the
-- finalize stage rewrites header-includes set by an earlier filter, and
-- include_text does not reach the Reveal output. Files and body blocks do.

local script_dir = debug.getinfo(1, "S").source:sub(2):match("^(.*)[/\\]") or "."
package.path = script_dir .. "/?.lua;" .. package.path
local brand = require("lkbrand")

local stringify = pandoc.utils.stringify
local is_live = quarto.doc.is_format("revealjs")
local is_study = quarto.doc.is_format("beamer") or quarto.doc.is_format("latex")

local function dirname(p) return p:match("^(.*)[/\\]") or "." end
local input_dir = quarto.doc.input_file and dirname(quarto.doc.input_file) or "."
local token_dir = input_dir .. "/_lecturekit"

local function write_file(p, s)
  pandoc.system.make_directory(token_dir, true)
  local f = io.open(p, "w")
  if f then f:write(s); f:close() end
end

-- the extension directory as seen from the output: Quarto copies the
-- extension's fonts next to the output only when they are referenced, so the
-- live deck points at the project's vendored copy instead
local function fonts_url()
  local proj = quarto.project.directory
  local ext = brand.ext_dir
  if proj and ext:sub(1, #proj) == proj then
    -- the deck's output sits at the same depth as its source within the project
    local rel_ext = ext:sub(#proj + 2)
    local abs_input = pandoc.path.is_absolute(input_dir) and input_dir or pandoc.path.join({ pandoc.system.get_working_directory(), input_dir })
    local rel_input = pandoc.path.make_relative(abs_input, proj)
    local up = ""
    if rel_input ~= "." and rel_input ~= "" then
      for _ in rel_input:gmatch("[^/]+") do up = up .. "../" end
    end
    return up .. rel_ext .. "/fonts/"
  end
  return "file://" .. brand.fonts_dir .. "/"
end

-- insert a block right after the first slide heading (or at the top)
local function insert_after_first_slide_heading(blocks, block, level)
  for i, b in ipairs(blocks) do
    if b.t == "Header" and b.level <= level then
      blocks:insert(i + 1, block)
      return blocks
    end
  end
  blocks:insert(1, block)
  return blocks
end

return {
  {
    Pandoc = function(doc)
      local slide_level = doc.meta["slide-level"] and tonumber(stringify(doc.meta["slide-level"])) or 2
      if is_study then
        write_file(token_dir .. "/tokens.tex", brand.latex_block())
      elseif is_live then
        local css = brand.css_block()
        local faces = brand.font_face_css(fonts_url())
        write_file(token_dir .. "/tokens.css", css .. "\n" .. faces .. "\n")
        local style = css .. faces
        if style ~= "" then
          doc.blocks = insert_after_first_slide_heading(doc.blocks,
            pandoc.RawBlock("html", "<style>" .. style .. "</style>"), slide_level)
        end
      end
      return doc
    end,
  },
}
