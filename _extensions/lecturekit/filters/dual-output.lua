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
--   * rewrites .movie Divs into autoplaying clips without browser controls
--     (live) and into the clip's still (study) when assets/clips/clips.json
--     or still= names one; otherwise it insists on a .live-only wrapper and
--     a study alternative, as the policy requires;
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
local function has(el, cls) return el.classes ~= nil and el.classes:includes(cls) end
local function excluded(el)
  return (live and has(el, 'study-only')) or (study and has(el, 'live-only'))
end
local function html_escape(s) return (s:gsub('[&<>"]', { ['&'] = '&amp;', ['<'] = '&lt;', ['>'] = '&gt;', ['"'] = '&quot;' })) end
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
local timing, budget_min = {}, nil
local cite_small = false
local paper_hex = brand.colors().paper or '#F3F2EE'

-- --------------------------------------------------------------------------
-- clips.json: the seam between a deck and whatever rendered its clips
-- --------------------------------------------------------------------------
local clips_index = nil
local function clips()
  if clips_index then return clips_index end
  clips_index = {}
  local s = read_file(input_dir .. '/assets/clips/clips.json')
  if s then
    local ok, data = pcall(pandoc.json.decode, s)
    if ok and type(data) == 'table' then clips_index = data end
  end
  return clips_index
end

-- src, still and aspect ("W:H") of a .movie Div, from its attributes and clips.json
local function resolve_clip(attrs)
  local info = { src = attrs.src, still = attrs.still, aspect = attrs.aspect, name = attrs.clip or attrs.src }
  if attrs.clip then
    local e = clips()[attrs.clip]
    if e then
      info.src = info.src or e.video or e.mp4
      info.still = info.still or e.still or e.png
      if not info.aspect and e.width and e.height then
        info.aspect = string.format('%d:%d', e.width, e.height)
      end
    elseif not info.src then
      error('Clip "' .. attrs.clip .. '" is not in assets/clips/clips.json (run lk clips) and no src= is given')
    end
  end
  if info.src and not info.still then
    local guess = info.src:gsub('%.%w+$', '.png')
    if file_exists(input_dir .. '/' .. guess) then info.still = guess end
  end
  return info
end

-- --------------------------------------------------------------------------
-- Pass 1: metadata, then the slide-level exclusion of whole slides
-- --------------------------------------------------------------------------
local function Meta(m)
  local short = m.shorttitle or m['short-title'] or m.title
  if short then short_title = stringify(short) end
  if m.budget then budget_min = tonumber(stringify(m.budget)) end
  if m['citation-size'] then cite_small = stringify(m['citation-size']) == 'small' end
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
  local info = resolve_clip(el.attributes)
  local label = el.attributes.label or 'Animation'
  if study then
    local h = el.attributes.height or '4cm'
    if info.still then
      local out = pandoc.List({ pandoc.RawBlock('latex', string.format('\\lkimageh{%s}{%s}', h, info.still)) })
      out:extend(el.content)
      return out, false
    end
    error('Wrap a movie in .live-only and supply a study alternative (or a still= / clips.json entry): ' .. tostring(info.name))
  end
  local src = info.src
  if not src or not src:match('^[%w%._/%-]+$') then error('Use a relative movie path without spaces: ' .. tostring(src)) end
  local classes = {}
  if (paper_roles[current_role] or has(el, 'paper')) and not has(el, 'keepwhite') then classes[#classes + 1] = 'paper' end
  -- aspect="4:3" or "1:1": a clip that is not 16:9 (for a column); the wrapper takes the clip's own shape (theme.scss).
  -- Any other aspect="W:H" (a clip cropped to its content) is set on the wrapper by the Div handler.
  local aspect = info.aspect
  if aspect then
    if not aspect:match('^%d+:%d+$') then error('Movie aspect must be W:H in whole numbers, not ' .. aspect) end
    if aspect == '4:3' or aspect == '1:1' then classes[#classes + 1] = 'aspect-' .. aspect:gsub(':', '-') end
  end
  local cls = #classes > 0 and ' class="' .. table.concat(classes, ' ') .. '"' or ''
  local poster = info.still and (' poster="' .. html_escape(info.still) .. '"') or ''
  -- data-autoplay: Reveal starts the clip when its slide is shown and pauses it on leaving; muted keeps the
  -- browser's autoplay policy out of the way (the clips are silent). No browser controls: a click or the space
  -- bar pauses and resumes, R replays (live-head.html).
  local video = '<video' .. cls .. ' data-autoplay muted preload="auto" playsinline aria-label="'
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
          local ok, info = pcall(resolve_clip, d.attributes)
          if ok and info.aspect then found = info.aspect end
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
  if not roles[role] then error('Unknown slide role: ' .. role .. ' (' .. stringify(el.content) .. ')') end
  return role
end

local function Header(el)
  if el.level ~= 2 then return el end
  local title = stringify(el.content)
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
  { traverse = 'topdown', Image = Image, Div = Div, Span = Span, Cite = Cite, Header = Header },
  { Pandoc = timing_report },
}
