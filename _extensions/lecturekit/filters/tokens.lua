-- tokens.lua
-- Puts the active brand into each output.
--
--   Beamer: writes _lecturekit/tokens.tex beside the source, with
--           \definecolor{nm<Name>}{HTML}{...} for every brand colour and
--           fontspec lines from the brand's typography (Quarto applies
--           _brand.yml typography to HTML outputs only). beamer/lecturekit.tex
--           inputs that file, so the title frame gets the tokens too.
--   Reveal: inlines <style>:root{--nm-<name>: ...}</style> as the first block
--           of the deck (a <style> element is valid anywhere in the body),
--           appends the deck's foot (short title, slide number) and the
--           pacing budget after the slides, and writes _lecturekit/tokens.css
--           for the review tools.
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
  os.execute(string.format("mkdir -p '%s'", token_dir))
  local f = io.open(p, "w")
  if f then f:write(s); f:close() end
end

local function to_minutes(v)
  if v == nil then return nil end
  local n = tonumber(v)
  if n then return n end
  local m, s = tostring(v):match("^(%d+):(%d%d)$")
  if m then return tonumber(m) + tonumber(s) / 60 end
  return nil
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
        write_file(token_dir .. "/tokens.css", css .. "\n")
        if css ~= "" then
          doc.blocks = insert_after_first_slide_heading(doc.blocks,
            pandoc.RawBlock("html", "<style>" .. css .. "</style>"), slide_level)
        end
        local short = doc.meta["short-title"] and stringify(doc.meta["short-title"])
          or (doc.meta.title and stringify(doc.meta.title)) or ""
        local budget = doc.meta.budget and to_minutes(stringify(doc.meta.budget)) or nil
        doc.blocks:insert(pandoc.RawBlock("html", string.format(
          '<div class="lk-foot"><span class="lk-foot-title">%s</span><span class="lk-foot-number"></span></div>' ..
          '<script>window.LK_BUDGET=%s;</script>', short, budget and tostring(budget) or "null")))
      end
      return doc
    end,
  },
}
