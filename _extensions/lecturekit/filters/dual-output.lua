-- dual-output.lua
-- The lecturekit dialect: one Markdown source, a Reveal.js live deck and a
-- Beamer study PDF.
--
-- What it does, in order:
--   1. reads the deck's options (budget, eyebrow preset, slide level);
--   2. drops `.study-only` content from the live deck and `.live-only`
--      content from the study PDF, whether marked on a Div or on a slide
--      heading (the heading and its whole slide go);
--   3. reads the role class and `time=` attribute on every slide heading,
--      emits the eyebrow for that output, sums the times and prints the
--      plan against the deck's budget (also written to timing.txt beside
--      the source);
--   4. rewrites `.movie` blocks into a <video> for the live deck and a
--      still image for the study PDF, resolving clip names through
--      assets/clips/clips.json when present;
--   5. leaves the pacing data on each heading for the live deck.
--
-- Colour tokens, fonts and the live foot are emitted by tokens.lua, which
-- runs after Quarto's filters. Everything here runs at `pre-quarto`, before
-- Quarto's own slide handling.

local stringify = pandoc.utils.stringify

local is_live = quarto.doc.is_format("revealjs")
local is_study = quarto.doc.is_format("beamer") or quarto.doc.is_format("latex")

-- --------------------------------------------------------------------------
-- Presets: the eyebrow label for each role class, per preset.
-- --------------------------------------------------------------------------
local PRESETS = {
  course = {
    order = { "concept", "caveat", "example", "anchor", "question" },
    labels = { concept = "Concept", caveat = "Caveat", example = "Example",
               anchor = "Anchor", question = "Question" },
  },
  prf = {
    order = { "where", "how", "what", "when" },
    labels = { where = "WHERE", how = "HOW", what = "WHAT", when = "WHEN" },
    -- the prf preset reuses the role colours of the course preset
    colors = { where = "concept", how = "example", what = "anchor", when = "question" },
  },
  none = { order = {}, labels = {} },
}

local opts = {
  budget = nil,
  preset = "course",
  slide_level = 2,
  short_title = nil,
  timing_file = "timing.txt",
}

-- --------------------------------------------------------------------------
-- Helpers
-- --------------------------------------------------------------------------
local function has_class(el, name)
  return el.classes ~= nil and el.classes:includes(name)
end

local function role_of(header)
  local preset = PRESETS[opts.preset] or PRESETS.course
  for _, cls in ipairs(header.classes) do
    if preset.labels[cls] then return cls end
    -- a role of another preset is still a role: label it with its own name
    for _, p in pairs(PRESETS) do
      if p.labels[cls] then return cls end
    end
  end
  return nil
end

local function role_label(role)
  local preset = PRESETS[opts.preset] or PRESETS.course
  if preset.labels[role] then return preset.labels[role] end
  for _, p in pairs(PRESETS) do
    if p.labels[role] then return p.labels[role] end
  end
  return role
end

local function role_color(role)
  local preset = PRESETS[opts.preset] or PRESETS.course
  if preset.colors and preset.colors[role] then return preset.colors[role] end
  return role
end

local function to_minutes(v)
  if v == nil then return nil end
  local n = tonumber(v)
  if n then return n end
  -- accept "2:30" as minutes:seconds
  local m, s = tostring(v):match("^(%d+):(%d%d)$")
  if m then return tonumber(m) + tonumber(s) / 60 end
  return nil
end

local function fmt_minutes(x)
  if x == nil then return "   -" end
  local whole = math.floor(x)
  local sec = math.floor((x - whole) * 60 + 0.5)
  if sec == 60 then whole, sec = whole + 1, 0 end
  if sec == 0 then return string.format("%3d'", whole) end
  return string.format("%3d'%02d", whole, sec)
end

local function dirname(p)
  return p:match("^(.*)[/\\]") or "."
end

local function file_exists(p)
  local f = io.open(p, "r")
  if f then f:close() return true end
  return false
end

local function read_file(p)
  local f = io.open(p, "r")
  if not f then return nil end
  local s = f:read("a")
  f:close()
  return s
end

-- Camel-case a token name for LaTeX: "role-concept" -> "RoleConcept".
local function camel(name)
  return (name:gsub("^%l", string.upper):gsub("[-_](%w)", function(c) return c:upper() end))
end

-- --------------------------------------------------------------------------
-- Pass 1: options from metadata
-- --------------------------------------------------------------------------
local function read_options(meta)
  if meta.budget then opts.budget = to_minutes(stringify(meta.budget)) end
  if meta["eyebrow-preset"] then opts.preset = stringify(meta["eyebrow-preset"]) end
  if meta["slide-level"] then opts.slide_level = tonumber(stringify(meta["slide-level"])) or 2 end
  if meta["short-title"] then
    opts.short_title = stringify(meta["short-title"])
  elseif meta.title then
    opts.short_title = stringify(meta.title)
  end
  if meta["timing-file"] then opts.timing_file = stringify(meta["timing-file"]) end
  return meta
end

-- --------------------------------------------------------------------------
-- Pass 2: drop the other output's content.
-- A Div with .study-only or .live-only goes as a whole. A slide heading with
-- either class takes its slide with it: every block up to the next heading
-- of the same or a higher level.
-- --------------------------------------------------------------------------
local function drop_class()
  if is_live then return "study-only" end
  if is_study then return "live-only" end
  return nil
end

local function prune_blocks(blocks)
  local drop = drop_class()
  if not drop then return blocks end
  local out = pandoc.List()
  local skipping_level = nil
  for _, b in ipairs(blocks) do
    if skipping_level then
      if b.t == "Header" and b.level <= skipping_level then
        skipping_level = nil
      else
        goto continue
      end
    end
    if b.t == "Header" and has_class(b, drop) then
      skipping_level = b.level
      goto continue
    end
    if b.t == "Div" and has_class(b, drop) then
      goto continue
    end
    out:insert(b)
    ::continue::
  end
  return out
end

-- Recursively prune inside Divs too (columns, fragments ...).
local function prune_div(div)
  local drop = drop_class()
  if drop and has_class(div, drop) then return {} end
  div.content = prune_blocks(div.content)
  return div
end

-- --------------------------------------------------------------------------
-- Pass 3: roles, times, eyebrows, timing report
-- --------------------------------------------------------------------------
local plan = {}        -- { {title=, role=, time=, cumulative=} ... }
local total = 0

local function eyebrow_live(role, label)
  return pandoc.RawBlock("html",
    string.format('<div class="lk-eyebrow lk-role-%s" data-role="%s">%s</div>',
      role_color(role), role, label))
end

local function eyebrow_study(role, label)
  return pandoc.RawBlock("latex",
    string.format("\\lkrole{%s}{%s}", camel(role_color(role)), label))
end

local function annotate_blocks(blocks)
  local out = pandoc.List()
  for _, b in ipairs(blocks) do
    out:insert(b)
    if b.t == "Header" and b.level == opts.slide_level then
      local role = role_of(b)
      local t = to_minutes(b.attributes["time"])
      if t then total = total + t end
      plan[#plan + 1] = { title = stringify(b.content), role = role, time = t, cumulative = total }
      local label = b.attributes["eyebrow"] or (role and role_label(role)) or nil
      -- the heading carries the data for the pacing clock and the CSS
      if is_live then
        b.attributes["data-planned"] = string.format("%.2f", total)
        if t then b.attributes["data-time"] = string.format("%.2f", t) end
        if role then b.attributes["data-role"] = role end
      end
      b.attributes["time"] = nil
      b.attributes["eyebrow"] = nil
      if label and role then
        if is_live then out:insert(eyebrow_live(role, label)) end
        if is_study then out:insert(eyebrow_study(role, label)) end
      elseif label then
        if is_live then out:insert(eyebrow_live("plain", label)) end
        if is_study then out:insert(eyebrow_study("plain", label)) end
      end
    end
  end
  return out
end

local function timing_report()
  if #plan == 0 then return end
  local lines = {}
  local which = is_live and "live" or (is_study and "study" or "?")
  lines[#lines + 1] = string.format("lecturekit timing (%s): %d slides, %s planned%s",
    which, #plan, fmt_minutes(total),
    opts.budget and string.format(", budget %s", fmt_minutes(opts.budget)) or "")
  for i, s in ipairs(plan) do
    lines[#lines + 1] = string.format("  %2d  %-9s %s  %s  %s", i, s.role or "-",
      fmt_minutes(s.time), fmt_minutes(s.cumulative), s.title)
  end
  if opts.budget then
    local diff = total - opts.budget
    if math.abs(diff) < 0.01 then
      lines[#lines + 1] = "  on budget"
    elseif diff > 0 then
      lines[#lines + 1] = string.format("  OVER budget by %s", fmt_minutes(diff))
    else
      lines[#lines + 1] = string.format("  under budget by %s", fmt_minutes(-diff))
    end
  end
  local text = table.concat(lines, "\n")
  io.stderr:write(text .. "\n")
  local input = quarto.doc.input_file
  if input and opts.timing_file and opts.timing_file ~= "" then
    local path = dirname(input) .. "/" .. opts.timing_file
    local f = io.open(path, "w")
    if f then f:write(text .. "\n") f:close() end
  end
end

-- --------------------------------------------------------------------------
-- Pass 4: movie blocks
--   ::: {.movie clip="bar_bold" still="assets/clips/bar_bold.png" aspect=1.78 height=4.2cm}
--   The caption (any content inside the Div) is kept under the clip.
--   `clip` is a path to an .mp4/.webm, or a name looked up in
--   assets/clips/clips.json (written by `lk clips`), with keys
--   { "<name>": { "video": ..., "still": ..., "width": .., "height": ..,
--                 "duration": .., "revision": .. } }.
-- --------------------------------------------------------------------------
local clips_index = nil

local function load_clips_index()
  if clips_index ~= nil then return clips_index end
  clips_index = {}
  local input = quarto.doc.input_file
  if not input then return clips_index end
  local path = dirname(input) .. "/assets/clips/clips.json"
  local s = read_file(path)
  if s then
    local ok, data = pcall(pandoc.json.decode, s)
    if ok and type(data) == "table" then clips_index = data end
  end
  return clips_index
end

local function resolve_clip(attrs)
  local clip = attrs["clip"] or attrs["src"]
  local info = { video = nil, still = attrs["still"], aspect = attrs["aspect"], name = clip }
  if clip and not clip:match("%.%w+$") then
    local idx = load_clips_index()
    local e = idx[clip]
    if e then
      info.video = e.video or e.mp4
      info.still = info.still or e.still or e.png
      if e.width and e.height and not info.aspect then
        info.aspect = string.format("%.4f", e.width / e.height)
      end
      info.duration = e.duration
    end
  else
    info.video = clip
  end
  if info.video and not info.still and info.video:match("%.%w+$") then
    local guess = info.video:gsub("%.%w+$", ".png")
    local input = quarto.doc.input_file
    if input and file_exists(dirname(input) .. "/" .. guess) then info.still = guess end
  end
  return info
end

local function movie_div(div)
  local info = resolve_clip(div.attributes)
  local height = div.attributes["height"]
  local caption = div.content
  if is_live then
    local style = ""
    if info.aspect then style = string.format(' style="aspect-ratio:%s"', info.aspect) end
    if height then
      -- 1 cm of the Beamer frame is 80 px of the 1280 x 720 live frame
      local cm = tonumber(tostring(height):match("^([%d%.]+)cm$"))
      local px = cm and cm * 80 or tonumber(tostring(height):match("^([%d%.]+)px$"))
      if px then style = style:gsub('"$', string.format(";max-height:%dpx\"", px)) end
      if style == "" and px then style = string.format(' style="max-height:%dpx"', px) end
    end
    local html
    if info.video then
      pcall(quarto.doc.add_resource, info.video)
      if info.still then pcall(quarto.doc.add_resource, info.still) end
      html = string.format(
        '<div class="lk-movie"%s><video class="lk-clip" src="%s"%s muted playsinline preload="auto" data-autoplay></video></div>',
        style, info.video, info.still and string.format(' poster="%s"', info.still) or "")
    else
      html = string.format('<div class="lk-movie lk-placeholder"%s>clip missing: %s</div>',
        style, info.name or "?")
    end
    local out = pandoc.List({ pandoc.RawBlock("html", html) })
    if #caption > 0 then
      out:insert(pandoc.Div(caption, pandoc.Attr("", { "lk-movie-caption" })))
    end
    return out
  end
  if is_study then
    local h = height or "4.2cm"
    local tex
    if info.still then
      tex = string.format("\\lkfigureh{%s}{%s}", h, info.still)
    else
      tex = string.format("\\lkplaceholder{%s}{clip: %s}", h, info.name or "?")
    end
    local out = pandoc.List({ pandoc.RawBlock("latex", tex) })
    if #caption > 0 then
      out:insert(pandoc.Div(caption, pandoc.Attr("", { "lk-movie-caption" })))
    end
    return out
  end
  return div
end

-- --------------------------------------------------------------------------
-- Filter
-- --------------------------------------------------------------------------
return {
  { Meta = read_options },
  {
    Pandoc = function(doc)
      doc.blocks = prune_blocks(doc.blocks)
      return doc
    end,
  },
  { Div = prune_div },
  {
    Div = function(div)
      if has_class(div, "movie") then return movie_div(div) end
      return nil
    end,
  },
  {
    Pandoc = function(doc)
      doc.blocks = annotate_blocks(doc.blocks)
      timing_report()
      return doc
    end,
  },
}
