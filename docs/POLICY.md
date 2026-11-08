# Presentation policy

Agreed 14 October 2026 for the 2026 run of the course these rules were written for, and carried into lecturekit as the rules of every deck. They decide how much goes on a slide, what is revealed when, how the live deck and the study PDF divide the material, and what the typography and the colours mean. LAYOUT.md covers the geometry these rules rest on, with the command that checks each; WORKFLOW.md the method. Where a rule has a check, it is named after the rule.

## The budget

A slot is two hours. With a break and the usual start, that is about 95 to 100 minutes of teaching, and the heuristic keeps the prepared core to 80 to 85 percent of that, so the live deck is planned for about 80 minutes and the rest is questions, stories and improvisation. At 20 to 25 live slides that is 3.5 to 4 minutes per content slide, which is the right pace for a conceptual course: one claim per slide, stated in the title, with time to think.

A lecture therefore has: title, learning goals, 17 to 21 content slides, takeaways, a self-check, references. A lecture outline's five to seven sections map to three or four slides each. A 15 minute talk, the worked example, has seven.

Put the planned minutes on each slide heading, `{role=concept time=4}`, and a `budget:` in the deck header. The build prints the plan against the budget after every render and writes the per-slide list to `_build/timing.txt`; in the browser deck the same numbers drive the pacing clock in the speaker view (S), which turns red when the lecture runs more than a minute behind its plan. Planning first and timing a rehearsal against it is how topics fit. Check: `lk build`.

## Reveals

The default is a complete slide. Everything the slide argues is visible when it appears, because the title already states the claim and the audience reads ahead anyway; a click per bullet adds a pause per bullet and about a hundred clicks per lecture.

Reveal only where the order is the explanation:

- A worked example, one step at a time.
- A question, then its answer.
- A figure that builds in stages.
- An argument with a turn, where the last line changes the reading of the earlier ones.

When revealing, reveal thoughts rather than lines: two or three lines that belong together appear together. Group them by nesting the supporting lines under a lead bullet inside an `incremental` list (a nested list reveals with its parent), or wrap each group in `::: {.fragment}`. One item at a time is for self-check questions and nothing else. The study PDF always shows the complete slide; answers must appear in shared or `study-only` text, never only behind a fragment. Check: `lk review frags <live.html>` lists the steps of every slide; the study PDF is read for the answers.

## Getting the topics in

The live deck is the spine; the study PDF is the whole argument. Material that matters but would not survive the live budget goes into `study-only` slides: a derivation, a second example, the answer guidance for the self-check, an optional enrichment clearly labelled as such. Students study from the PDF and the exam covers the PDF. A lecture with 22 live slides can have 30 to 35 study pages without the live hour feeling crowded.

If a topic still does not fit, cut a slide rather than compress one: a slide that needs more than five minutes is two claims, and a slide under two minutes is a caption for a neighbour.

Suggested role mix per lecture, as guidance rather than a rule: one goals, three to five concept, two or three example, one or two caveat, one question, one summary, the rest explanation.

## Media

- Figures from papers keep their files unchanged; the multiply blend turns their white into the slide background on paper slides. The same rule applies to video.
- An animation made for a slide leaves the title to the slide; the clip shows the mechanism and nothing else.
- Render clips at 1280 by 720 with a white background; the blend handles paper slides. Rendering on the paper colour directly is also fine for a clip that will only ever sit on a paper slide.
- Every clip has a static equivalent in the study PDF. Check: a `.movie` without a still and without a `.live-only` wrapper stops the build (AUTHORING.md); `lk clips` writes the still of every kit clip.

## Type size, numbering and the figure-to-text ratio

Added 14 October 2026 after the first full lecture build.

- Body text is 12 pt on 15 pt leading in the study PDF (the frame title 20 pt), which the browser deck mirrors at 30 px on a 1280 px slide. The earlier 15 pt body was too large: it held five lines next to a figure and made every figure small. The study page now takes about nine lines of text without a figure, or a figure of 4 to 5 cm plus two lines.
- Figures carry the slide. On a figure slide the figure takes 50 to 60 percent of the height and the text under it is one or two lines; the explanation goes on a study-only slide that follows. A reused paper figure that students must read (a neural trace, a behavioural curve) gets the height, and the title is kept to one line so that it can.
- Numbered points are for ordered steps only (a worked example, a procedure). Goals, takeaways and self-check questions use plain bullets; a slide of text should not read as a numbered list. Since 14 October 2026 the two-digit numerals in the role colour are reserved for ordered steps.
- Clips stand alone on their live slide (title plus clip). The one- or two-line caption and the static stages are study-only, so the live slide is the mechanism and the voice, and the study page is the argument.
- Figure files live beside the deck (`assets/figures/name.tex`, one `tikzpicture` each, generated by the deck's `make_assets.py` from the same numbers as the clips) and are placed with `\nmfigureh{4cm}{assets/figures/name.tex}` (height cap; `\nmfigure{...}` caps the width only). Design figures at the width of the slide (12 to 13 cm) with footnotesize labels so that they are not scaled down. Check: `lk review figs <deck>` prints each figure's natural size.
- Reused raster figures are sized with a print height (`{height=46mm}`). The browser deck turns that height, and the height of `\nmfigureh`, into a `max-height` at 8.8 px per mm, so the ratio set for the page holds on the screen. Check: `lk review measure <live.html>`.

## No paragraph slides

Added 15 October 2026, after the lecture 2 review.

- No slide, live or study-only, carries a paragraph. A study page is a figure plus at most four bullets, a formula plus bullets, a table plus bullets, or bullets alone; the sentences go to the notes or to the lecturer. Study-only explanation slides written as prose read as generated text and are not read.
- A bullet is one line where it can be (about 60 characters at 12 pt, about 70 at the live font) and two at most. A page holds about nine bullet lines without a figure; with a figure of 3 cm, four lines; with 4 cm, two. A one-line title buys an extra line and a half, so a figure page gets a short title. Check: `lk review measure` counts the wrapping bullets per slide.
- Each explanation slide earns its place with a figure that the prose would have described: a figure of the quantity under discussion (the noise-free solutions of a differential equation, the correct and error distributions, the two curves one parameter predicts) is generated from the same simulations as the clips and placed with `\nmfigureh`. Where the words were a description of a model, the model becomes a diagram (units, inputs, couplings).
- Citations stay visible on the page, in a bullet, not in the notes; a narrative citation (`@Key`) is shorter than a parenthetical one when the sentence is about the paper.

## Rules added 27 October 2026

Four rules from the review of lecture 1, which apply to every deck from here on.

1. Colour emphasis in the text. Each slide colours the words that carry it: `[words]{.blue}` for the term or claim to keep (the concept being introduced, the thing to remember), `[words]{.red}` for the trap, the contrast, what is not the case or what still has to be shown. One to three coloured phrases per slide; bold stays for labels (the name of a grading component, a step in a list), italics for the usual typographic uses. The colours are the course blue (`nmInput`, #0072B2) and the caveat red (`nmCaveat`, #A33A32); the filter turns the spans into `\textcolor` on the page and into `.blue` and `.red` classes in the browser. Choosing the words is part of writing the slide: ask what the one phrase is that the audience should still see when the slide is gone, and what the one phrase is that they get wrong.
2. A visual on every slide. Every slide carries a figure, an image or a diagram; a slide of bullets alone is a draft. Images are easy to find and make a deck far more inviting: the paper's own figures when the licence allows (CC BY papers, PLOS, eLife, PMC author manuscripts), Wikimedia Commons for portraits and historical photographs, a logo or headshot from the organisation's own site for a named person or product, and the deck's own TikZ figures for anything schematic. Record the source in the slide notes and in `MANIFEST.md`. A row of images is `::: {.row live-height=200px}` around one paragraph of images with `{height=20mm}`. Check: `lk review shoot --sheet` shows every slide on one sheet.
3. Titles on one line. A slide title fits one line in both outputs: 30 characters is the limit in the serif capitals (the build warns beyond that; `lk review measure` and `lk review shoot` report wrapped titles). A title that wraps and leaves a single word on its second line is shortened, which gives the rest of the slide its room back. Say the claim in fewer words rather than hyphenate or shrink.
4. Citations in italics. Every in-text citation, parenthetical or author-in-text, is set in italics in both outputs. Nothing to do in the source.

## Engagement

Added 30 October 2026. Every lecture is built with its engagement plan, not given one afterwards. Each deck folder has an `ENGAGEMENT.md` that uses the lecture's own architecture: one or two devices that run through the whole slot (the room producing data in the first ten minutes and the lecture returning to it; predict-then-reveal before every clip stage), then a prompt per slide. The same prompt is the first line of the slide's speaker notes, beginning "Ask:", so it is on the laptop screen in the speaker view. Prompts cost about a minute each and replace explanation rather than add to it; the deck's `time=` plan is adjusted so the total still fits, and the plan names which prompts to keep if time runs short. Prompts are shows of hands, a number shouted, thirty seconds with a neighbour, a prediction before a clip; nothing that needs the board or a count. A recorded lecture has pause prompts instead (`role=pause`): the slide tells the viewer to stop the recording and think, and the study pages carry the answer.

## Typography and emphasis

The course standard of 13 October 2026, with the fonts of 26 October 2026: TeX Gyre Heros (a Helvetica) for sans and TeX Gyre Pagella (a Palatino) for serif, with TeX Gyre Pagella Math, all bundled with the engine and loaded by file, so a build is the same on every machine. A project may name other families in its brand file (THEMING.md); the rules stay.

- The serif, regular weight: slide titles and prominent summary takeaways. Display slide titles and the title-page main title in capitals; keep subtitles, body text and takeaway sentences in natural case. The theme applies capitals at rendering time, preserving authored wording and mathematical notation. Titles are tracked at 2 percent of the em, labels at 8 percent. Keep titles concise enough to avoid crowding.
- The sans: body text, learning-role labels, citations and diagram labels. Markdown `**strong**` is set in the real bold face.
- TeX Gyre Pagella Math: mathematical notation. Preserve mathematical conventions; italic variables do not imply rhetorical emphasis.
- Bold means "retain this." Mark a key term on first introduction or a short essential phrase. Usually one or two phrases per slide; never entire paragraphs. Learning goals can remain regular weight because their layout already marks them as important.
- Italics signal nuance: a short qualification, a verbal contrast, or a book title. Avoid whole explanatory paragraphs in italics. Citations are italic by rule.
- Colour identifies a teaching role or a direct correspondence with a figure. It does not simply mean "more important." Body text stays charcoal, including on coloured-role slides.
- Avoid stacking bold, italic and colour on a phrase. Titles remain regular-weight serif even when coloured. Avoid underlining and all-caps body emphasis; small uppercase role labels are a navigation convention.
- Essential reasoning and answers belong in the student study materials, not exclusively in speaker notes.

## Slide roles

Six structural elements carry the page, none decorative: the title block (role label in small letterspaced capitals, a 14 mm rule in the role colour, the title in letterspaced capitals); the running foot on every content slide (a hairline across the text width, the deck's short title at the left, "page / total" at the right, in muted small capitals; the title page keeps the foot's height and prints nothing); numbered points with two-digit numerals in the role colour and charcoal text, for ordered steps only; the title page, left aligned like every frame (eyebrow, title in capitals, a short charcoal rule, the subtitle in muted serif, author and date in sans); letterspaced capitals from two dedicated font families; and the same structure in the browser deck, with the type scale of the PDF relative to the slide.

The roles, with their tokens (the paper preset's values) and recurring treatment:

| Role | Token / hex | Recurring treatment |
| --- | --- | --- |
| Ordinary explanation (`explanation`) | `nmInk` / `202B33` | Charcoal heading, white background; title states the claim |
| Core concept or definition (`concept`) | `nmConcept` / `175B8E` | Deep blue heading and explicit "Core concept" label; preserve a definition or distinction |
| Caveat or limitation (`caveat`) | `nmCaveat` / `A33A32` | Brick red heading and "Caveat" label; a short red vertical rule beside caveat callouts (`\caveatnote`) |
| Worked example (`example`) | `nmExample` / `956000` | Dark amber heading and "Worked example" label; numbered steps |
| Learning goals (`goals`) | `nmAnchor` / `006C65` | Teal heading and label on warm paper; observable learning outcomes as plain bullets |
| Summary (`summary`) | `nmAnchor` / `006C65` | Teal heading and "Takeaways" label on warm paper; prominent conclusion (`\takehome`) followed by the essentials |
| Question or self-check (`question`) | `nmQuestion` / `70508C` | Purple heading and explicit question label; retrieval prompts on white |
| Next part (`section`), pause (`pause`) | `nmAnchor`, `nmQuestion`, on paper | Dividers and pause prompts of a recorded lecture |
| The workshop's objectives (`detection`, `estimation`, `discrimination`) | `nmConcept`, `nmState`, `nmContext` | The eyebrow names the objective (MAPS, ESTIMATION, DISCRIMINATION), with its icon in the role colour |
| The four dimensions (`where`, `how`, `what`, `when`) | `nmInk` | Eyebrow and title in the heading colour, an icon each; colour stays with the models in the figures |

Warm paper is `nmPaper` / `F3F2EE`; secondary text is `nmMuted` / `566573`; the hairline is `nmHairline` / `C8C3BA`. Use labels and recurring composition alongside colour, so roles remain legible in grayscale. Keep a single primary teaching role per slide. An otherwise ordinary slide can contain a short caveat callout.

Red means "interpret with care," not necessarily "incorrect." Misconceptions must explicitly say "Incorrect" or "Misconception." Summaries state conclusions; concept anchors preserve definitions or distinctions. Do not replace either with a list of topic names.

## Colour meanings

Teaching-role tokens apply to slide headings, labels and coloured spans. Mark tokens (`nmInput` #0072B2, `nmState` #007F73, `nmUpdate` #C45A00, `nmContext` #7A5195) retain their scientific meanings inside figures and clips: what enters a model, what it holds, what changes, what surrounds. Use explicit labels or legends there. A blue curve does not automatically represent a core concept, nor does an orange error signal mean a worked example. Keep body text charcoal unless a short phrase directly identifies a labelled element in a figure (`.teal`, `.purple`, `.orange` spans).

Project tokens, the model colours of the worked example among them (`gauss`, `DoG`, `CSS`, `DN`, `future`), are the project's own and keep one meaning across a project's decks; they travel through the same brand file as the engine's tokens and are checked by the same tool. Check: `lk review contrast <_brand.yml> [--mode dark]` for legibility on every surface; the meaning is reviewed by eye.

## In one table

| Rule | Check |
| --- | --- |
| The plan fits the budget | `lk build`; `_build/timing.txt`; the pacing clock at rehearsal |
| Reveal only where the order is the explanation; answers in the PDF | `lk review frags`; the study PDF |
| Titles under 30 characters, on one line | the build's warning; `lk review measure`; `lk review shoot` |
| A visual on every slide, as large as the slide allows | `lk review shoot --sheet`; `lk review measure`; `lk review figs` |
| Bullets of one line; no paragraph slides | `lk review measure`; `lk review overflow` |
| Every clip has a static equivalent | the build stops without one; `lk clips` writes the still |
| Colour means something; colours legible on the surfaces | `lk review contrast`; review by eye |
| Verified claims only; every image with its origin | `FACTS.md` and `MANIFEST.md`, signed off by the lecturer (WORKFLOW.md) |
