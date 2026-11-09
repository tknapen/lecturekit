-- dual-output.lua
-- One source: shared content, explicit output alternatives, identical teaching roles.
--
-- The dialect of the course and workshop decks, running inside Quarto's two
-- lecturekit formats (revealjs for the room, beamer for study). What it does:
--
--   * reads the deck metadata beyond the title block: shorttitle (the running
--     foot), eyebrow (the line above the main title), budget (minutes),
--     citation-size;
--   * drops .study-only content from the live deck and .live-only content
--     from the study PDF, whether marked on a fenced Div or on a slide
--     heading (the heading takes its whole slide);
--   * reads role= and time= on every slide heading (## level): the role
--     becomes the eyebrow label and colour in both outputs (a CSS class and
--     data attributes live, the nmrole frame option in Beamer), the minutes
--     go to the timing report and the speaker view's pacing clock;
--   * inserts the per-slide foot of the live deck (short title, n / total);
--   * rewrites .movie Divs into clips without browser controls that the
--     live runtime (reveal/live-head.html) plays, and into the clip's still
--     (study) when assets/clips/clips.json or still= names one; otherwise it
--     insists on a .live-only wrapper and a study alternative, as the policy
--     requires; a dark build reads assets/clips/dark/clips.json first;
--   * rewrites a clip in parts (stops= on a clip= movie of a format 2 entry)
--     into one video, a still per boundary and an empty fragment per key,
--     which reveal/segments.html follows, each fragment with the notes of
--     its hold; and into a strip of the holds (study, \lkstrip); checks that
--     the clip stands alone as its slide's reveal;
--   * carries print heights (height=42mm, \nmfigureh{4cm}) over to the live
--     deck as max-height at 8.8 px per mm; composites images on warm-paper
--     slides with multiply; lays out .row image rows; .small, .incremental;
--   * colours emphasis spans ([words]{.blue}, .red, .teal, .purple, .orange,
--     .gauss, .grey, and the role names) by CSS class live and \textcolor in
--     Beamer; sets citations smaller when asked;
--   * writes the timing report (timing.txt in the output directory) and
--     prints it after the render.
--
-- TikZ figures (\nmfigureh{...}{file}, \input{file}, ![](file.tex), fenced
-- {.tikz} blocks) are handled by tikz.lua, which runs after this filter;
-- colour and font tokens from _brand.yml by tokens.lua.
--
-- Its checks stop the render. Quarto (1.11) redefines the global error() as a
-- logger that returns, so the filter never calls it: fail() below writes the
-- reason to stderr as an ERROR line and raises through Lua's own assert(),
-- which Pandoc reports as a filter failure and Quarto as a failed render.

local script_dir = debug.getinfo(1, "S").source:sub(2):match("^(.*)[/\\]") or "."
package.path = script_dir .. "/?.lua;" .. package.path
local brand = require("lkbrand")

local stringify = pandoc.utils.stringify
local live = quarto.doc.is_format("revealjs")
local study = quarto.doc.is_format("beamer") or quarto.doc.is_format("latex")

-- --------------------------------------------------------------------------
-- Roles: the eyebrow label of each. Beamer carries the same table in
-- lecturekit.tex (the nmrole frame option); keep the two in step.
-- --------------------------------------------------------------------------
local roles = {
  explanation = 'EXPLANATION', concept = 'CORE CONCEPT', caveat = 'CAVEAT / INTERPRET WITH CARE',
  example = 'WORKED EXAMPLE', goals = 'LEARNING GOALS', summary = 'TAKEAWAYS',
  question = 'CHECK YOUR UNDERSTANDING',
  section = 'NEXT PART',            -- a divider for a recording cut into parts
  pause = 'PAUSE THE RECORDING',    -- a recorded lecture's prompt to stop and think
  -- the three objectives of the pRF workshop decks: the eyebrow names the objective, with its icon and colour
  detection = 'MAPS', estimation = 'ESTIMATION', discrimination = 'DISCRIMINATION',
  -- the four dimensions of the advanced-models lecture
  where = 'WHERE', how = 'HOW', what = 'WHAT', when = 'WHEN',
}
-- roles whose slides sit on warm paper
local paper_roles = { goals = true, summary = true, section = true, pause = true }

-- --------------------------------------------------------------------------
-- Helpers
-- --------------------------------------------------------------------------
-- A check that stops the render: an ERROR line naming lecturekit (lk build looks for it), then a real Lua error.
-- Quarto's error() only logs; assert() is Lua's own and raises.
local function fail(msg)
  io.stderr:write('ERROR (lecturekit) ' .. msg .. '\n')
  assert(false, 'lecturekit: ' .. msg)
end

-- a problem that does not stop the build: lk build lists it, and lk build --strict fails on it
local function warn(msg)
  io.stderr:write('WARNING (lecturekit) ' .. msg .. '\n')
end

local function has(el, cls) return el.classes ~= nil and el.classes:includes(cls) end
local function excluded(el)
  return (live and has(el, 'study-only')) or (study and has(el, 'live-only'))
end
local function html_escape(s) return (tostring(s):gsub('[&<>"]', { ['&'] = '&amp;', ['<'] = '&lt;', ['>'] = '&gt;', ['"'] = '&quot;' })) end
local function dirname(p) return p:match('^(.*)[/\\]') or '.' end
local function basename_noext(p) return ((p:match('([^/\\]+)$') or p):gsub('%.[^.]+$', '')) end
local function file_exists(p) local f = io.open(p, 'r'); if f then f:close() return true end return false end
local function read_file(p) local f = io.open(p, 'r'); if not f then return nil end local s = f:read('a'); f:close(); return s end
local function write_file(p, s)
  pandoc.system.make_directory(dirname(p), true)
  local f = assert(io.open(p, 'w')); f:write(s); f:close()
end
local function to_latex(inlines)
  return (pandoc.write(pandoc.Pandoc({ pandoc.Plain(inlines) }), 'latex'):gsub('%s+$', ''))
end
local function meta_inlines(v)
  if type(v) == 'table' and v.t == 'MetaInlines' then return v end
  return pandoc.Inlines(pandoc.Str(stringify(v)))
end

local input_file = quarto.doc.input_file or 'slides.qmd'
local input_dir = dirname(input_file)
local input_stem = basename_noext(input_file)
local token_dir = input_dir .. '/_lecturekit'

-- 8.8 px per mm: a 720 px slide for a 90 mm frame, plus a tenth for the smaller body type
local PX_PER_MM = 8.8

-- --------------------------------------------------------------------------
-- Deck state
-- --------------------------------------------------------------------------
local short_title = ''
local total_slides, slide_index, current_role = 1, 1, 'explanation'
local current_title = '(title slide)'
local timing, budget_min = {}, nil
local cite_small = false
local paper_hex = brand.colors().paper or '#F3F2EE'

-- --------------------------------------------------------------------------
-- clips.json: the seam between a deck and whatever rendered its clips
-- --------------------------------------------------------------------------
-- An entry (CLIPS.md): video, still, width, height, fps, duration, source, revision, producer, job, checkpoints.
-- A JSON null decodes to pandoc.json.null, a userdata that Lua takes as true; every field is read through str()
-- or num(), which take a value of the wrong type, null included, as absent.
local function str(v) if type(v) == 'string' and v ~= '' then return v end return nil end
local function num(v) if type(v) == 'number' then return v end return nil end

-- '-' and '_' are one character in a clip name: `bar-bold` and `bar_bold` name one clip
local function norm_name(name) return (tostring(name):gsub('-', '_')) end

-- the preset of this build: dark when the brand mode is dark (the dark profile sets brand-mode: dark)
local dark = brand.mode() == 'dark'

local function read_index(rel)
  local s = read_file(input_dir .. '/' .. rel)
  if not s then return nil end
  local ok, data = pcall(pandoc.json.decode, s, false)
  if not ok or type(data) ~= 'table' then fail(rel .. ' is not a JSON object of clips: run lk clips again') end
  local by_norm = {}
  for key, entry in pairs(data) do
    if type(key) == 'string' and type(entry) == 'table' then
      local n = norm_name(key)
      if by_norm[n] and by_norm[n].key ~= key then
        fail(rel .. ' names one clip twice: "' .. by_norm[n].key .. '" and "' .. key .. '" ("-" and "_" are the same)')
      end
      by_norm[n] = { key = key, entry = entry, index = rel }
    end
  end
  return by_norm
end

-- the indexes to look in, in order: the dark preset's own first in a dark build, then the paper one
local clip_indexes = nil
local function indexes()
  if clip_indexes then return clip_indexes end
  clip_indexes = {}
  local order = dark and { 'assets/clips/dark/clips.json', 'assets/clips/clips.json' } or { 'assets/clips/clips.json' }
  for _, rel in ipairs(order) do
    local idx = read_index(rel)
    if idx then clip_indexes[#clip_indexes + 1] = idx end
  end
  return clip_indexes
end

local function lookup_clip(name)
  local n = norm_name(name)
  for _, idx in ipairs(indexes()) do
    if idx[n] then return idx[n].entry, idx[n].index end
  end
  return nil
end

-- The stop candidates of a format 2 entry (CLIPS.md): the entries of `stops` with an id and a frame, in frame order.
local function stop_candidates(e)
  local out = {}
  for _, c in ipairs(type(e.stops) == 'table' and e.stops or {}) do
    if type(c) == 'table' and str(c.id) and num(c.frame) then out[#out + 1] = c end
  end
  table.sort(out, function(a, b) return a.frame < b.frame end)
  return out
end

-- The still of a hold of a format 2 entry, by id: a stop candidate, `start` (the poster, frame 0) or `end`.
local function hold_still(e, id)
  if id == 'start' then return str(e.poster) end
  if id == 'end' then return type(e['end']) == 'table' and str(e['end'].still) or str(e.still) end
  for _, c in ipairs(stop_candidates(e)) do if c.id == id then return str(c.still) end end
  return nil
end

-- src, still and aspect ("W:H") of a .movie Div, from its attributes and clips.json; nil and the reason when the
-- block cannot be resolved. still= is a path, or the id of one of the entry's checkpoints (a format 2 entry: of a
-- stop candidate, or start or end).
local function resolve_clip(attrs)
  local info = { src = str(attrs.src), still = str(attrs.still), aspect = str(attrs.aspect),
                 name = str(attrs.clip) or str(attrs.src) or '(unnamed)' }
  local clip = str(attrs.clip)
  if clip then
    local e, where = lookup_clip(clip)
    if e then
      info.index, info.entry = where, e
      info.src = info.src or str(e.video) or str(e.mp4)
      local checkpoints = type(e.checkpoints) == 'table' and e.checkpoints or {}
      local bare = info.still and info.still:match('^[%a][%w_]*$')
      if bare and num(e.format) == 2 and hold_still(e, info.still) then
        info.still = hold_still(e, info.still)
      elseif info.still and str(checkpoints[info.still]) then
        info.still = str(checkpoints[info.still])
      elseif bare then
        local ids = {}
        for k, v in pairs(checkpoints) do if str(v) then ids[#ids + 1] = k end end
        if num(e.format) == 2 then
          for _, c in ipairs(stop_candidates(e)) do ids[#ids + 1] = c.id end
          ids[#ids + 1] = 'start'; ids[#ids + 1] = 'end'
        end
        table.sort(ids)
        return nil, 'still="' .. info.still .. '" names no checkpoint of clip "' .. clip .. '" in ' .. where
          .. ' (it has ' .. (#ids > 0 and table.concat(ids, ', ') or 'none') .. ')'
      end
      info.still = info.still or str(e.still) or str(e.png)
      local w, h = num(e.width), num(e.height)
      if not info.aspect and w and h then info.aspect = string.format('%d:%d', w, h) end
    elseif not info.src then
      return nil, 'Clip "' .. clip .. '" is not in ' .. (dark and 'assets/clips/dark/clips.json or ' or '')
        .. 'assets/clips/clips.json (run lk clips) and no src= is given'
    end
  end
  -- a dark build plays the dark render of a src= clip when one exists: assets/clips/x.mp4 -> assets/clips/dark/x.mp4
  if dark and not clip and info.src and info.src:match('^assets/clips/[^/]+$') then
    local alt = info.src:gsub('^assets/clips/', 'assets/clips/dark/')
    if file_exists(input_dir .. '/' .. alt) then
      info.src = alt
      if info.still and info.still:match('^assets/clips/[^/]+$') then
        local salt = info.still:gsub('^assets/clips/', 'assets/clips/dark/')
        if file_exists(input_dir .. '/' .. salt) then info.still = salt end
      end
    end
  end
  if info.src and not info.still then
    local guess = info.src:gsub('%.%w+$', '.png')
    if file_exists(input_dir .. '/' .. guess) then info.still = guess end
  end
  -- in a dark build, a clip that is not a dark render was drawn on the paper colours
  info.paper_in_dark = dark and info.src ~= nil and not info.src:match('^assets/clips/dark/')
  return info
end

-- --------------------------------------------------------------------------
-- A clip in parts: stops=, start=, study= and .stop on a clip= movie
-- --------------------------------------------------------------------------
-- A format 2 entry lists stop candidates, each a frame of the one video with its still and its measured rest; the
-- deck chooses among them with stops="id ...". The boundaries of a clip are frame 0, the chosen stops and its last
-- frame. Live, the clip plays one part per key press and holds exactly on the boundary that ends it: the filter
-- emits the video without Reveal's autoplay, one still per boundary and one empty fragment (a cue) per key, and the
-- runtime (reveal/segments.html) makes the video agree with the number of visible cues. With start=auto part 1
-- plays when the slide appears; with start=key the slide opens on frame 0 and the first key starts part 1. The study
-- PDF prints the holds as a strip (\lkstrip), the end alone (study=final) or the holds named in study=.
local MAX_STOPS, MIN_REST, MAX_PANELS = 5, 3, 6

local function words(s)
  local out = {}
  for w in tostring(s or ''):gmatch('%S+') do out[#out + 1] = w end
  return out
end
local function segmented(el) return el.t == 'Div' and has(el, 'movie') and el.attributes.stops ~= nil end
local function json_num(x) return (string.format('%.6f', x):gsub('0+$', ''):gsub('%.$', '')) end
local function secs(x) return string.format('%.1f', x) end
local function latex_text(s) return to_latex(pandoc.Inlines(tostring(s))) end

-- Speaker notes of the slides that hold a clip in parts, taken out of the slide by the slide pass: the runtime shows
-- each cue's notes, which replace the slide's, so every cue carries a copy.
local seg_slide_notes = {}
local auto_play_media = false
local deck_incremental = false

-- The plan of a clip in parts: its boundaries, the notes of each hold and the panels of its study page. Every check
-- that concerns the movie alone fails here; the slide-level ones are in the slide pass below.
local function seg_plan(el, info, where)
  local attrs, name = el.attributes, str(el.attributes.clip) or '?'
  if str(attrs.src) then fail('stops= needs the clip= form, not src=' .. where) end
  if auto_play_media then
    fail('stops= needs Reveal to leave the clip alone, and auto-play-media: true starts every clip on entry' .. where)
  end
  local e = info.entry
  if not e or num(e.format) ~= 2 then
    fail('stops= needs a clips.json entry of format 2, with frames and stop candidates (run lk clips again, or lk '
      .. 'clips adopt for an external file)' .. where)
  end
  local fps = num(e.fps)
  if not fps or fps <= 0 then fail('The clips.json entry has no fps' .. where) end
  local start = attrs.start or 'auto'
  if start ~= 'auto' and start ~= 'key' then fail('start= is auto or key, not ' .. start .. where) end
  local cands, by_id = stop_candidates(e), {}
  for _, c in ipairs(cands) do by_id[c.id] = c end
  local function known()
    local ids = {}
    for _, c in ipairs(cands) do ids[#ids + 1] = c.id end
    return #ids > 0 and table.concat(ids, ', ') or 'none'
  end
  local ids = words(attrs.stops)
  if attrs.stops == 'all' then ids = {}; for _, c in ipairs(cands) do ids[#ids + 1] = c.id end end
  if #ids == 0 then fail('stops= names no stop (the clip has ' .. known() .. ')' .. where) end
  if #ids > MAX_STOPS then
    fail('stops= names ' .. #ids .. ' stops; a clip holds at ' .. MAX_STOPS .. ' at most (split the clip, or choose)' .. where)
  end
  local en = type(e['end']) == 'table' and e['end'] or {}
  local end_frame = num(en.frame) or (num(e.frames) and num(e.frames) - 1)
  if not end_frame then fail('The clips.json entry has no end frame' .. where) end
  local poster = str(e.poster)
  if not poster then fail('The clips.json entry has no poster (frame 0)' .. where) end
  local bounds = { { f = 0, t = 0, still = poster, ref = 'start', label = 'start' } }
  local last = 0
  for _, id in ipairs(ids) do
    local c = by_id[id]
    if not c then fail('stops= names "' .. id .. '", which is not a stop of clip "' .. name .. '" (it has ' .. known() .. ')' .. where) end
    if c.frame <= last then fail('stops= names "' .. id .. '" out of order: name the stops in time order' .. where) end
    if c.frame >= end_frame then fail('The stop "' .. id .. '" is on the last frame' .. where) end
    local rest = num(c.rest_before)
    if not rest or rest < MIN_REST then
      fail('The stop "' .. id .. '" has ' .. (rest and (string.format('%d', math.floor(rest)) .. ' frame(s)') or 'no measured rest') .. ' of unchanged picture before it; '
        .. 'a stop needs ' .. MIN_REST .. ', because the player pauses up to two frames early' .. where)
    end
    if not str(c.still) then fail('The stop "' .. id .. '" has no still' .. where) end
    last = c.frame
    bounds[#bounds + 1] = { f = c.frame, t = num(c.pts) or c.frame / fps, still = str(c.still), ref = id,
                            label = str(c.label) or (id:gsub('_', ' ')), notes = str(c.notes) }
  end
  local end_still = str(en.still) or str(e.still)
  if not end_still then fail('The clips.json entry has no still of its last frame' .. where) end
  bounds[#bounds + 1] = { f = end_frame, t = num(en.pts) or end_frame / fps, still = end_still, ref = 'end',
                          label = str(en.label) or 'end', notes = str(en.notes) }
  for _, b in ipairs(bounds) do
    if not file_exists(input_dir .. '/' .. b.still) then fail('The still ' .. b.still .. ' does not exist' .. where .. ': run lk clips') end
  end
  -- the .stop blocks: the speaker notes of a hold; the rest of the body is the caption
  local holds = { ['end'] = true }
  for i = 2, #bounds - 1 do holds[bounds[i].ref] = true end
  if start == 'key' then holds.start = true end
  local stop_notes, caption, prompts = {}, pandoc.List(), 0
  for _, b in ipairs(el.content) do
    if b.t == 'Div' and has(b, 'stop') then
      local ref = str(b.attributes.ref)
      if not ref or not holds[ref] then
        local names = {}
        for i = 2, #bounds - 1 do names[#names + 1] = bounds[i].ref end
        names[#names + 1] = 'end'
        if start == 'key' then table.insert(names, 1, 'start') end
        fail('.stop ref="' .. tostring(ref) .. '" names no hold of this clip (its holds: ' .. table.concat(names, ', ')
          .. (ref == 'start' and '; with start=auto part 1 plays on entry, so frame 0 is not a hold' or '') .. ')' .. where)
      end
      if stop_notes[ref] then fail('Two .stop blocks for the hold "' .. ref .. '"' .. where) end
      stop_notes[ref] = b.content
      if stringify(b.content):find('Ask:', 1, true) then prompts = prompts + 1 end
    else
      caption:insert(b)
    end
  end
  -- the study page: the holds after each part, the end alone, or the holds study= names
  local study = attrs.study or 'strip'
  local panels = {}
  if study == 'strip' then
    for i = 2, #bounds do panels[#panels + 1] = bounds[i] end
  elseif study == 'final' then
    panels[1] = bounds[#bounds]
  else
    local at = {}
    for _, id in ipairs(words(study)) do
      local p
      if id == 'start' then p = bounds[1] elseif id == 'end' then p = bounds[#bounds]
      elseif by_id[id] then
        local c = by_id[id]
        p = { f = c.frame, still = str(c.still), label = str(c.label) or (id:gsub('_', ' ')) }
        if not p.still or not file_exists(input_dir .. '/' .. p.still) then fail('The stop "' .. id .. '" has no still' .. where) end
      else
        fail('study= is strip, final or a list of holds (start, end, ' .. known() .. '), and "' .. id .. '" is none of them' .. where)
      end
      if not at[p.f] then at[p.f] = true; panels[#panels + 1] = p end
    end
    table.sort(panels, function(a, b) return a.f < b.f end)
  end
  if #panels > MAX_PANELS then
    fail('study= prints ' .. #panels .. ' panels; a strip holds ' .. MAX_PANELS .. ' at most: name fewer holds in study=' .. where)
  end
  local parts = {}
  for i = 2, #bounds do parts[#parts + 1] = (bounds[i].f - bounds[i - 1].f) / fps end
  local sha = str(e.sha256) or ''
  return { name = name, fps = fps, key = start == 'key', start = start, bounds = bounds, stop_notes = stop_notes,
           caption = caption, panels = panels, parts = parts, prompts = prompts,
           seconds = num(e.duration) or (end_frame + 1) / fps, ver = sha:gsub('^sha256:', ''):sub(1, 8) }
end

-- The notes of state k (k cues visible): the .stop text of the hold it ends on ("Ask:" first, POLICY.md), the part
-- that plays, what the producer says is on screen, then the slide's own notes.
local function hold_notes(plan, k, slide_notes)
  local b = plan.key and k or k + 1
  local bound, nparts = plan.bounds[b + 1], #plan.bounds - 1
  local out = pandoc.List()
  if plan.stop_notes[bound.ref] then
    out:insert(pandoc.Div(plan.stop_notes[bound.ref]:clone(),
      pandoc.Attr('', { 'lk-stop-notes' }, { ['data-lk-ref'] = bound.ref })))
  end
  local head
  if b == 0 then
    head = string.format('Frame 0: part 1 of %d (%s seconds) plays on the next key.', nparts, secs(plan.parts[1]))
  else
    head = string.format('Part %d of %d, %s seconds: holds on %s.', b, nparts, secs(plan.parts[b]),
      bound.ref == 'end' and (bound.label == 'end' and 'the last frame' or bound.label) or bound.label)
  end
  out:insert(pandoc.Para(pandoc.Inlines(head)))
  if bound.notes then out:insert(pandoc.Para(pandoc.Inlines('On screen: ' .. bound.notes))) end
  for _, n in ipairs(slide_notes or {}) do out:insert(n:clone()) end
  return pandoc.Div(out, pandoc.Attr('', { 'notes' }))
end

local function seg_live(el, info, plan, where)
  local name = html_escape(plan.name)
  local paper = (paper_roles[current_role] or has(el, 'paper')) and not has(el, 'keepwhite')
  local v = plan.ver ~= '' and ('?v=' .. plan.ver) or ''
  local js, imgs = {}, {}
  for i, b in ipairs(plan.bounds) do
    local bi = i - 1
    js[#js + 1] = string.format('{"f":%d,"t":%s,"r":"%s"}', b.f, json_num(b.t), b.ref)
    local s = plan.key and bi or bi - 1                 -- the state that holds on this boundary
    imgs[#imgs + 1] = '<img class="lk-still' .. (paper and ' paper' or '') .. '" data-lk-b="' .. bi .. '"'
      .. (s >= 0 and (' data-lk-s="' .. s .. '"') or '') .. ' data-src="' .. html_escape(b.still .. v) .. '" alt="">'
  end
  local w, h = (info.aspect or ''):match('^(%d+):(%d+)$')
  local style = ''
  if w and math.abs(tonumber(w) / tonumber(h) - 16 / 9) > 0.01 then style = ' style="aspect-ratio:' .. w .. '/' .. h .. '"' end
  local src = info.src
  if not src or not src:match('^[%w%._/%-]+$') then fail('Use a relative movie path without spaces: ' .. tostring(src) .. where) end
  -- data-lk-src, not src: only the main window loads the clip (the speaker view's previews show the stills)
  local html = '<div class="live-only lk-seg" data-lk-seg="' .. name .. '" data-lk-fps="' .. json_num(plan.fps)
    .. '" data-lk-start="' .. plan.start .. '" data-lk-v="' .. html_escape(plan.ver) .. "\" data-lk-bounds='"
    .. '[' .. table.concat(js, ',') .. "]'" .. style .. '>'
    .. '<video' .. (paper and ' class="paper"' or '') .. ' muted playsinline preload="none" disablepictureinpicture aria-label="'
    .. html_escape(el.attributes.label or 'Animation') .. '" data-lk-src="' .. src .. '" poster="'
    .. html_escape(plan.bounds[1].still .. v) .. '"></video>' .. table.concat(imgs) .. '</div>'
  local out = pandoc.List({ pandoc.RawBlock('html', html) })
  if #plan.caption > 0 then out:insert(pandoc.Div(plan.caption, pandoc.Attr('', { 'movie-caption' }))) end
  local slide_notes = seg_slide_notes[el.attributes['lk-seg-slide'] or ''] or {}
  out:insert(hold_notes(plan, 0, slide_notes))
  local ncues = #plan.bounds - (plan.key and 1 or 2)
  for k = 1, ncues do
    -- attributes as a list of pairs, so that they are written in this order on every build
    out:insert(pandoc.Div({ hold_notes(plan, k, slide_notes) }, pandoc.Attr('', { 'fragment', 'lk-cue' },
      { { 'data-lk-for', plan.name }, { 'data-lk-k', tostring(k) } })))
  end
  return out
end

-- \lkstrip{height}{columns}{rows}{panels}: 2 or 3 panels in one row, 4 in two rows of 2, 5 and 6 in two rows of 3;
-- the whole strip within the height (lecturekit.tex)
local function strip_latex(panels, height)
  if #panels == 1 then return string.format('\\lkimageh{%s}{%s}', height or '4cm', panels[1].still) end
  local n = #panels
  local cols = n <= 3 and n or (n == 4 and 2 or 3)
  local cells = {}
  for i, p in ipairs(panels) do
    cells[#cells + 1] = string.format('\\lkpanel{%s}{%d}{%s}', p.still, i, latex_text(p.label))
    if i < n then cells[#cells + 1] = (i % cols == 0) and '\\lkstriprow' or '\\lkstripgap' end
  end
  return string.format('\\lkstrip{%s}{%d}{%d}{%%\n%s}', height or '4.8cm', cols, math.ceil(n / cols), table.concat(cells, '%\n'))
end

local function seg_movie(el, info, where)
  local plan = seg_plan(el, info, where)
  local t = timing[#timing]
  if t then
    t.clips = t.clips or {}
    t.clips[#t.clips + 1] = plan
  end
  if study then
    local out = pandoc.List({ pandoc.RawBlock('latex', strip_latex(plan.panels, el.attributes.height)) })
    out:extend(plan.caption)
    return out, false
  end
  return seg_live(el, info, plan, where), false
end

-- A movie without stops=: no .stop block, no start=; study= is final, or names holds of a format 2 entry.
local function unsegmented_checks(el, info, where)
  for _, b in ipairs(el.content) do
    if b.t == 'Div' and has(b, 'stop') then fail('A .stop block needs stops= on its movie' .. where) end
  end
  if el.attributes.start then fail('start= needs stops= (a clip in parts)' .. where) end
  local study_attr = el.attributes.study
  if not study_attr or study_attr == 'final' then return nil end
  if study_attr == 'strip' then fail('study=strip needs stops=; name the holds instead, study="id ..."' .. where) end
  local e = info.entry
  if not e or num(e.format) ~= 2 then fail('study="' .. study_attr .. '" needs a clips.json entry of format 2' .. where) end
  local panels, at = {}, {}
  for _, id in ipairs(words(study_attr)) do
    local still = hold_still(e, id)
    if not still or not file_exists(input_dir .. '/' .. still) then
      fail('study= names "' .. id .. '", which is no hold of the clip with a still (start, end or a stop candidate)' .. where)
    end
    local f = 0
    if id == 'end' then f = math.huge
    elseif id ~= 'start' then for _, c in ipairs(stop_candidates(e)) do if c.id == id then f = c.frame end end end
    local label = id == 'start' and 'start' or id == 'end' and (type(e['end']) == 'table' and str(e['end'].label) or 'end')
    if not label then
      for _, c in ipairs(stop_candidates(e)) do if c.id == id then label = str(c.label) or (id:gsub('_', ' ')) end end
    end
    if not at[f] then at[f] = true; panels[#panels + 1] = { f = f, still = still, label = label } end
  end
  table.sort(panels, function(a, b) return a.f < b.f end)
  if #panels > MAX_PANELS then
    fail('study= prints ' .. #panels .. ' panels; a strip holds ' .. MAX_PANELS .. ' at most: name fewer holds in study=' .. where)
  end
  return panels
end

-- The slide pass, before the element pass: a clip in parts stands alone as the slide's reveal. It fails on two of
-- them on one slide, one inside a .fragment or an .r-stack, and any other fragment on the slide (a .fragment, an
-- .incremental list, a fragment span, a `. . .` pause). It takes the slide's speaker notes out of the slide, for the
-- movie to compose each hold's notes from (hold_notes).
local function scan_slide(blocks, ctx, found)
  for _, b in ipairs(blocks) do
    if b.t == 'Div' then
      if not has(b, 'study-only') then
        if segmented(b) then
          found.movies[#found.movies + 1] = { el = b, fragment = ctx.fragment, stack = ctx.stack }
        elseif not has(b, 'notes') then
          if has(b, 'fragment') then found.frags = found.frags + 1 end
          if has(b, 'incremental') then found.frags = found.frags + 1 end
          scan_slide(b.content, { fragment = ctx.fragment or has(b, 'fragment'), stack = ctx.stack or has(b, 'r-stack'),
                                  nonincremental = ctx.nonincremental or has(b, 'nonincremental') }, found)
        end
      end
    elseif b.t == 'BulletList' or b.t == 'OrderedList' then
      if deck_incremental and not ctx.nonincremental then found.frags = found.frags + 1 end
      for _, item in ipairs(b.content) do scan_slide(item, ctx, found) end
    elseif b.t == 'BlockQuote' then
      scan_slide(b.content, ctx, found)
    else
      if (b.t == 'Para' or b.t == 'Plain') and stringify(b) == '. . .' then found.frags = found.frags + 1 end
      pcall(function() b:walk({ Span = function(s) if has(s, 'fragment') then found.frags = found.frags + 1 end end }) end)
    end
  end
end

-- the slide's notes Divs, outside study-only blocks and the movie, taken out of the block list into `into`; the
-- movie is tagged with the key of its slide's notes
local function take_notes(blocks, into, tag)
  local kept = pandoc.List()
  for _, b in ipairs(blocks) do
    if b.t == 'Div' and has(b, 'notes') then
      into:extend(b.content)
    else
      if segmented(b) then
        b.attributes['lk-seg-slide'] = tag
      elseif b.t == 'Div' and not has(b, 'study-only') then
        b.content = take_notes(b.content, into, tag)
      end
      kept:insert(b)
    end
  end
  return kept
end

local function segment_slides(doc)
  local slides, cur = {}, { blocks = pandoc.List(), title = '(title slide)' }
  slides[1] = cur
  for _, b in ipairs(doc.blocks) do
    if (b.t == 'Header' and b.level <= 2) or b.t == 'HorizontalRule' then
      cur = { blocks = pandoc.List(), head = b, title = b.t == 'Header' and stringify(b.content) or cur.title }
      slides[#slides + 1] = cur
    else
      cur.blocks:insert(b)
    end
  end
  local any = false
  for i, s in ipairs(slides) do
    local found = { movies = {}, frags = 0 }
    scan_slide(s.blocks, {}, found)
    if #found.movies > 0 then
      any = true
      local m = found.movies[1]
      local where = ' (movie "' .. (str(m.el.attributes.clip) or str(m.el.attributes.src) or '?') .. '" on slide "' .. s.title .. '")'
      if #found.movies > 1 then fail('Two clips in parts on one slide ("' .. s.title .. '"): a clip in parts stands alone on its slide') end
      if m.fragment then fail('A clip in parts inside a .fragment' .. where .. ': its parts are the steps; take the .fragment away') end
      if m.stack then fail('A clip in parts inside an .r-stack' .. where .. ': a clip in parts is one clip, not a step of a sequence') end
      if found.frags > 0 then
        fail('A clip in parts and another reveal on one slide' .. where .. ': its parts are the slide\'s only steps '
          .. '(take the .fragment, .incremental list or pause away, or move it to its own slide)')
      end
      local notes = pandoc.List()
      s.blocks = take_notes(s.blocks, notes, tostring(i))
      seg_slide_notes[tostring(i)] = notes
    end
  end
  if not any then return nil end
  local out = pandoc.List()
  for _, s in ipairs(slides) do
    if s.head then out:insert(s.head) end
    out:extend(s.blocks)
  end
  doc.blocks = out
  return doc
end

-- --------------------------------------------------------------------------
-- Pass 1: metadata, then the slide-level exclusion of whole slides
-- --------------------------------------------------------------------------
local function Meta(m)
  local short = m.shorttitle or m['short-title'] or m.title
  if short then short_title = stringify(short) end
  if m.budget then budget_min = tonumber(stringify(m.budget)) end
  if m['citation-size'] then cite_small = stringify(m['citation-size']) == 'small' end
  local function truthy(v) return v == true or (v ~= nil and type(v) ~= 'boolean' and stringify(v) == 'true') end
  auto_play_media = truthy(m['auto-play-media'])
  deck_incremental = truthy(m.incremental)
  local eb = m.eyebrow or m.series
  if live then
    local attrs = m['title-slide-attributes'] or pandoc.MetaMap({})
    if eb then attrs['data-eyebrow'] = pandoc.MetaString(stringify(eb)) end
    if budget_min then attrs['data-budget'] = pandoc.MetaString(tostring(budget_min)) end
    m['title-slide-attributes'] = attrs
  end
  if study then
    -- Beamer reads the short title, eyebrow and citation size from a file named after the job
    local lines = {}
    if m.shorttitle or m['short-title'] then
      lines[#lines + 1] = '\\nmShortTitle{' .. to_latex(meta_inlines(m.shorttitle or m['short-title'])) .. '}'
    end
    if eb then lines[#lines + 1] = '\\nmEyebrow{' .. to_latex(meta_inlines(eb)) .. '}' end
    if cite_small then lines[#lines + 1] = '\\lkCitationSmalltrue' end
    write_file(token_dir .. '/' .. input_stem .. '-deck.tex',
      '% deck metadata for Beamer, written by lecturekit; do not edit\n' .. table.concat(lines, '\n') .. '\n')
  end
  return m
end

local function prune(doc)
  local kept, skip = pandoc.List(), false
  for _, b in ipairs(doc.blocks) do
    if b.t == 'Header' and b.level == 2 then
      skip = excluded(b)
      if not skip then total_slides = total_slides + 1 end
    end
    if not skip then kept:insert(b) end
  end
  doc.blocks = kept
  return doc
end

-- --------------------------------------------------------------------------
-- Pass 2: elements, top down
-- --------------------------------------------------------------------------
local function Image(el)
  -- A height in print units (height=22mm, height=4cm) sizes the study page; the live deck gets the same height
  -- as a max-height at 8.8 px per mm, so figure and text keep the ratio set for the page.
  if live and el.attributes.height then
    local mm = tonumber(el.attributes.height:match('^([%d%.]+)mm$'))
    local cm = tonumber(el.attributes.height:match('^([%d%.]+)cm$'))
    if cm then mm = cm * 10 end
    if mm then
      el.attributes.style = string.format('max-height:%dpx', math.floor(mm * PX_PER_MM + 0.5))
      el.attributes.height = nil
    end
  end
  -- An image inside a {.row live-height=300px} div takes that browser height instead.
  if live and el.attributes['live-height'] then
    el.attributes.style = 'max-height:' .. el.attributes['live-height']; el.attributes['live-height'] = nil
  end
  -- Figures on warm-paper slides are composited with multiply, so their white background becomes the slide
  -- background. {.keepwhite} opts out; {.paper} forces it elsewhere.
  if has(el, 'keepwhite') or not (paper_roles[current_role] or has(el, 'paper')) then return el end
  if live then el.classes:insert('paper'); return el end
  return { pandoc.RawInline('latex', '\\begin{paperfigure}'), el, pandoc.RawInline('latex', '\\end{paperfigure}') }
end

local function movie(el)
  local info, why = resolve_clip(el.attributes)
  local where = ' (movie "' .. (str(el.attributes.clip) or str(el.attributes.src) or '?') .. '" on slide "' .. current_title .. '")'
  if not info then fail(why .. where) end
  if live and info.paper_in_dark then
    warn('the dark preset plays ' .. info.src .. ', a clip drawn for the paper preset' .. where
      .. ': render a dark one with lk clips --mode dark (it goes to assets/clips/dark/)')
  end
  if segmented(el) then return seg_movie(el, info, where) end
  local panels = unsegmented_checks(el, info, where)
  local label = el.attributes.label or 'Animation'
  if study and panels then
    local out = pandoc.List({ pandoc.RawBlock('latex', strip_latex(panels, el.attributes.height)) })
    out:extend(el.content)
    return out, false
  end
  if study then
    local h = el.attributes.height or '4cm'
    if info.still then
      if not file_exists(input_dir .. '/' .. info.still) then
        fail('The still ' .. info.still .. ' does not exist' .. where .. ': run lk clips, or name another still=')
      end
      local out = pandoc.List({ pandoc.RawBlock('latex', string.format('\\lkimageh{%s}{%s}', h, info.still)) })
      out:extend(el.content)
      return out, false
    end
    if str(el.attributes.clip) then
      fail('No still for the study PDF' .. where .. ': its clips.json entry has none and still= names none; '
        .. 'run lk clips (a manim8 clip takes a checkpoint), or give still=')
    end
    fail('Wrap a movie in .live-only and supply a study alternative (or a still= / clips.json entry)' .. where)
  end
  local src = info.src
  if not src or not src:match('^[%w%._/%-]+$') then fail('Use a relative movie path without spaces: ' .. tostring(src) .. where) end
  local classes = {}
  if (paper_roles[current_role] or has(el, 'paper')) and not has(el, 'keepwhite') then classes[#classes + 1] = 'paper' end
  -- aspect="4:3" or "1:1": a clip that is not 16:9 (for a column); the wrapper takes the clip's own shape (theme.scss).
  -- Any other aspect="W:H" (a clip cropped to its content) is set on the wrapper by the Div handler.
  local aspect = info.aspect
  if aspect then
    if not aspect:match('^%d+:%d+$') then fail('Movie aspect must be W:H in whole numbers, not ' .. aspect .. where) end
    if aspect == '4:3' or aspect == '1:1' then classes[#classes + 1] = 'aspect-' .. aspect:gsub(':', '-') end
  end
  local cls = #classes > 0 and ' class="' .. table.concat(classes, ' ') .. '"' or ''
  local poster = info.still and (' poster="' .. html_escape(info.still) .. '"') or ''
  -- data-lk-autoplay: the runtime (live-head.html) starts the clip when its slide or step is shown and stops it
  -- when it is not; Reveal's own data-autoplay is not used, since it plays every step of a sequence at once.
  -- muted keeps the browser's autoplay policy out of the way (the clips are silent). No browser controls: a click
  -- or the space bar pauses and resumes, R replays.
  local video = '<video' .. cls .. ' data-lk-autoplay muted preload="auto" playsinline aria-label="'
    .. html_escape(label) .. '"' .. poster .. ' src="' .. src .. '"></video>'
  if not el.attributes['lk-boxed'] then
    -- no .live-only wrapper in the source (the clip= form): supply the box that sizes the clip, with its shape
    local w, h = (aspect or ''):match('^(%d+):(%d+)$')
    local style = ''
    if w and aspect ~= '4:3' and aspect ~= '1:1' and math.abs(tonumber(w) / tonumber(h) - 16 / 9) > 0.01 then
      style = ' style="aspect-ratio:' .. w .. '/' .. h .. '"'
    end
    video = '<div class="live-only"' .. style .. '>' .. video .. '</div>'
  end
  local out = pandoc.List({ pandoc.RawBlock('html', video) })
  if #el.content > 0 then out:insert(pandoc.Div(el.content, pandoc.Attr('', { 'movie-caption' }))) end
  return out, false
end

local function Div(el)
  if excluded(el) or (study and has(el, 'notes')) then return {}, false end
  if study and has(el, 'incremental') then el.classes = pandoc.List() end
  if has(el, 'small') and study then
    -- {.small} sets its contents (a wide table, say) in \small on the page; the browser gets the class
    local out = pandoc.List({ pandoc.RawBlock('latex', '\\begingroup\\small') }); out:extend(el.content)
    out:insert(pandoc.RawBlock('latex', '\\endgroup')); return out
  end
  if has(el, 'row') then
    -- A row of images: side by side in the browser (theme.scss .row); live-height=300px overrides the print-derived
    -- max-height of each image in the browser only. Top-down traversal: the Div hands the height to its images.
    local h = el.attributes['live-height']
    if live and h and h:match('^%d+px$') then
      el = el:walk({ Image = function(im) im.attributes['live-height'] = h; return im end })
    end
    el.attributes['live-height'] = nil
    return el
  end
  if live and has(el, 'live-only') then
    -- the movies inside know they have their sizing box
    el = el:walk({ Div = function(d) if has(d, 'movie') then d.attributes['lk-boxed'] = '1' end; return d end })
  end
  if live and (has(el, 'live-only') or has(el, 'r-stack')) and not el.attributes.style then
    -- A clip cropped to its content declares its shape (aspect="1838:850"); the box that sizes it, the .live-only
    -- wrapper of a single clip or the r-stack of a sequence, takes that shape instead of 16:9.
    local direct = false
    for _, b in ipairs(el.content) do if b.t == 'Div' and has(b, 'movie') then direct = true end end
    if direct or has(el, 'r-stack') then
      local found
      el:walk({ Div = function(d)
        if not found and has(d, 'movie') then
          local info = resolve_clip(d.attributes)
          if info and info.aspect then found = info.aspect end
        end
      end })
      local w, h = (found or ''):match('^(%d+):(%d+)$')
      if w and found ~= '4:3' and found ~= '1:1' and math.abs(tonumber(w) / tonumber(h) - 16 / 9) > 0.01 then
        el.attributes.style = 'aspect-ratio:' .. w .. '/' .. h
      end
    end
  end
  if has(el, 'movie') then return movie(el) end
  return el
end

-- Colour emphasis: [words]{.blue} for the term or claim to keep, [words]{.red} for the trap, the contrast, what
-- is not the case. .teal, .purple and .orange tie a word to a figure drawn in the mark colours; .gauss to the
-- Gaussian pRF's blue of the workshop figures; .grey to the muted grey of a reference curve. The role names
-- colour a word in a role's colour. The browser gets the class (theme.scss), the page \textcolor.
local span_colours = {
  blue = 'nmInput', red = 'nmCaveat', teal = 'nmState', purple = 'nmContext', orange = 'nmUpdate',
  gauss = 'nmGauss', grey = 'nmMuted', muted = 'nmMuted',
  concept = 'nmConcept', caveat = 'nmCaveat', example = 'nmExample', anchor = 'nmAnchor', question = 'nmQuestion',
  ['mark-input'] = 'nmInput', ['mark-state'] = 'nmState', ['mark-update'] = 'nmUpdate', ['mark-context'] = 'nmContext',
}
local function Span(el)
  local colour
  for _, c in ipairs(el.classes) do if span_colours[c] then colour = span_colours[c]; break end end
  if not colour or live then return el end
  local out = pandoc.List({ pandoc.RawInline('latex', '\\textcolor{' .. colour .. '}{') })
  out:extend(el.content); out:insert(pandoc.RawInline('latex', '}')); return out
end

-- Every in-text citation, parenthetical or author-in-text, is set in italics in both outputs (rule of 27 October
-- 2026): the browser through .citation in theme.scss, the page by wrapping the citation here, before citeproc
-- renders it in place. citation-size: small in the deck header also sets them smaller, so the claim carries the line.
local function Cite(el)
  if live then
    if not cite_small then return nil end
    return pandoc.Span({ el }, pandoc.Attr('', { 'cite-small' })), false
  end
  local open = cite_small and '{\\footnotesize\\itshape ' or '{\\itshape '
  return { pandoc.RawInline('latex', open), el, pandoc.RawInline('latex', '}') }, false
end

local function role_of(el)
  local role = el.attributes.role
  if not role then
    for _, c in ipairs(el.classes) do if roles[c] then role = c; break end end
  end
  role = role or 'explanation'
  if not roles[role] then fail('Unknown slide role: ' .. role .. ' (' .. stringify(el.content) .. ')') end
  return role
end

local function Header(el)
  if el.level ~= 2 then return el end
  local title = stringify(el.content)
  current_title = title
  if utf8.len(title) > 32 then io.stderr:write('Title may wrap (over 30 characters): ' .. title .. '\n') end
  local role = role_of(el)
  el.attributes.role = nil
  el.classes = el.classes:filter(function(c) return roles[c] == nil end)
  current_role = role
  local label = el.attributes.label or el.attributes.eyebrow or roles[role]
  el.attributes.label = nil; el.attributes.eyebrow = nil
  -- flash=500 on a heading: the browser shows the slide's image for that many milliseconds, then blanks it
  local flash = el.attributes.flash; el.attributes.flash = nil
  if live and flash then el.attributes['data-flash'] = flash; el.attributes['data-transition'] = 'none' end
  local minutes = tonumber(el.attributes.time); el.attributes.time = nil
  timing[#timing + 1] = { title, minutes, role }
  if live then
    if minutes then el.attributes['data-timing'] = tostring(math.floor(minutes * 60)) end
    el.classes:insert('role-' .. role)
    el.attributes['data-role'] = role
    el.attributes['data-role-label'] = label
    if paper_roles[role] then el.attributes['data-background-color'] = paper_hex end
    slide_index = slide_index + 1
    local foot = pandoc.RawBlock('html', '<div class="nm-foot" aria-hidden="true"><span>' .. html_escape(short_title) ..
      '</span><span>' .. slide_index .. ' / ' .. total_slides .. '</span></div>')
    return { el, foot }
  end
  el.attributes.frameoptions = 'nmrole=' .. role .. (el.attributes.frameoptions and ',' .. el.attributes.frameoptions or '')
  if label ~= roles[role] then
    return { el, pandoc.RawBlock('latex', '\\slidecue{' .. to_latex(pandoc.Inlines(pandoc.Str(label))) .. '}') }
  end
  return el
end

-- --------------------------------------------------------------------------
-- Pass 3: the timing report
-- --------------------------------------------------------------------------
local function timing_report(doc)
  if #timing == 0 then return doc end
  local planned, untimed, lines = 0, 0, {}
  lines[#lines + 1] = string.format('%5s %6s  %-12s %s', 'min', 'at', 'role', 'slide')
  for _, t in ipairs(timing) do
    if t[2] then planned = planned + t[2] else untimed = untimed + 1 end
    lines[#lines + 1] = string.format('%5s %6g  %-12s %s', t[2] and string.format('%g', t[2]) or '-', planned, t[3], t[1])
    -- a clip in parts: its parts and prompts; the clip's seconds plus a minute per prompt (POLICY.md) against time=
    for _, c in ipairs(t.clips or {}) do
      local durations = {}
      for _, d in ipairs(c.parts) do durations[#durations + 1] = secs(d) end
      local need = c.seconds + 60 * c.prompts
      local over = t[2] and need > t[2] * 60
      lines[#lines + 1] = string.format('%5s %6s  %-12s clip %s: %s s, %d parts (%s s), %d prompt%s%s', '', '', '', c.name,
        secs(c.seconds), #c.parts, table.concat(durations, ' '), c.prompts, c.prompts == 1 and '' or 's', over and '  CLIP>TIME' or '')
      if over then
        warn(string.format('CLIP>TIME slide "%s": clip %s runs %s s and its %d prompt%s take a minute each, %s s in all, '
          .. 'over time=%g (%s s): give the slide more time or the clip fewer stops', t[1], c.name, secs(c.seconds), c.prompts,
          c.prompts == 1 and '' or 's', secs(need), t[2], secs(t[2] * 60)))
      end
    end
  end
  lines[#lines + 1] = string.format('slides %d  planned %g min  untimed %d%s', #timing, planned, untimed,
    budget_min and string.format('  budget %g min  %s', budget_min, planned > budget_min and 'OVER' or 'ok') or '')
  local text = table.concat(lines, '\n')
  io.stderr:write(string.format('lecturekit timing (%s):\n%s\n', live and 'live' or 'study', text))
  if live then
    local out_dir = input_dir
    local proj_dir, proj_out = quarto.project.directory, quarto.project.output_directory
    if proj_dir and proj_out then
      local abs_input = pandoc.path.is_absolute(input_dir) and input_dir or pandoc.path.join({ pandoc.system.get_working_directory(), input_dir })
      local rel = pandoc.path.make_relative(abs_input, proj_dir)
      out_dir = (rel == '.' or rel == '') and proj_out or pandoc.path.join({ proj_out, rel })
    end
    pcall(write_file, out_dir .. '/timing.txt', text .. '\n')
  end
  return doc
end

return {
  { Meta = Meta },
  { Pandoc = prune },
  { Pandoc = segment_slides },
  { traverse = 'topdown', Image = Image, Div = Div, Span = Span, Cite = Cite, Header = Header },
  { Pandoc = timing_report },
}
