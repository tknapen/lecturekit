# Export to PowerPoint

Some venues take a PowerPoint file and nothing else. `lk export pptx` turns a built live deck into a `.pptx` that
keeps its look, steps through the same reveals, plays the same clips and carries the speaker notes. It reads the
deck that `lk build` wrote and never builds; build first.

```sh
lk build . --to live                       # or --profile dark
lk export pptx                             # the project found from here; slides.pptx beside slides-live.html
lk export pptx . --profile dark            # the dark build (_build-dark)
lk export pptx _build/slides-live.html --out talk.pptx --slides 3,5-7
```

It needs the `export` extra (`pip install "lecturekit[export]"`, then `playwright install chromium`; INSTALL.md).

| Option | What it does |
| --- | --- |
| `DIR` or `DECK.html` | A project folder (default: the project found from the working directory), one of its build folders (`_build-dark` exports the dark deck), or a built live deck. |
| `--profile dark` | The build of that Quarto profile, read from `_quarto-dark.yml` (with a project folder). |
| `--out FILE` | The file to write; default `slides.pptx` beside the live deck. |
| `--video auto\|click\|still` | How the clips play (below); default `auto`. |
| `--slides 3,5-7` | Only these deck slides, numbered as the foot numbers them. |
| `--scale N` | Device pixels per CSS pixel of the pictures: 2 (the default) gives 2560 by 1440. |

A profile without a `_quarto-<profile>.yml` is refused. When a `.qmd` or `_quarto*.yml` of the project is newer
than the built deck, the command says so and names the `lk build` command; it exports the deck as built.

The command prints one line per deck slide (its steps, clips and movies), then the totals and what to check in
PowerPoint.

## How a deck becomes slides

Each slide at each reveal step becomes one PowerPoint slide: a slide with three fragments gives four PowerPoint
slides, the first with none shown. The presenter steps through the PowerPoint slides with the same keys as through
the reveals of the live deck, one slide per step.

Each PowerPoint slide is a picture of the step: the page in a headless Chromium at 1280 by 720 CSS pixels, the
frame of `lk review`, with transitions off and the clips hidden. The picture fills the 16:9 slide (13.333 by 7.5
inches); the slide's background takes the page colour. The clips are placed on top by the exporter, each in the
rectangle where the live deck shows its picture (the video's box, with `object-fit: contain` for the file's own
proportions):

- An ordinary clip that comes on stage at a step (on the slide's first step, or with the fragment that shows it, or
  as the next step of an `.r-stack` sequence) is a movie with frame 0 as its poster.
- A clip that was already on stage at the step before is a still of its last frame, where the live clip has
  usually ended. A clip still playing when the key comes is cut short to its last frame.
- A clip in parts is one movie per part, cut frame-exactly from the stop before to the stop it holds on, both
  frames included. Its poster is the first of these frames and its last frame is the hold, which is also the next
  part's poster, so the parts join without a jump. With `start=key` the slide opens on a still of frame 0.

The notes of each step are the notes the speaker view shows at that step: the notes of the current fragment (the
stop's "Ask:" or "Say:" at a hold), else the slide's own. Where two fragments share an index, the notes of both are
taken. They are plain text, one line per paragraph or list item.

The picture carries alt text: the role label or eyebrow, the title and the text visible at the step. Each movie and
still carries the clip's label.

## The three video modes

What follows is what the file asks PowerPoint to do, in the form PowerPoint itself writes for it; it has not been
checked in PowerPoint (see "Test it in PowerPoint before the talk").

- `auto` (the default): each movie is set to start by itself when its slide appears, as PowerPoint writes for
  "Start: Automatically", and a click on it is set to pause and resume it. Two clips that come on stage together are
  set to start together. The next key is meant to go to the next slide.
- `click`: the same movies, set to start on a click on them, as PowerPoint writes for "When Clicked On". Useful
  where a clip must wait for the speaker. The click is a mouse click on the movie itself: a clicker's key goes to
  the next slide and leaves the movie on its poster, frame 0, which for many clips is an empty stage.
- `still`: no movie at all; each clip is a still of the frame it would end on (an ordinary clip's last frame, the
  hold of a clip in parts). The file is small and plays anywhere; a fallback when movies fail on the venue's machine.

## What carries over

- The look, as a picture of the page at twice the frame's resolution: fonts, colours, figures, mathematics, role
  labels and the foot (the deck's slide numbers, not PowerPoint's).
- Every reveal step, every clip and every hold of a clip in parts, in order.
- The speaker notes, in PowerPoint's notes and Presenter View.
- A flash slide shows its image (the brief exposure itself does not carry over).
- A clip on a goals, summary, section or pause slide, which the live deck blends into the paper colour by
  multiplication (`.paper`; AUTHORING.md): its frames are multiplied by the colour of the page under it, which is
  what the blend shows there. Such a clip is always re-encoded. The export shows what the browser shows, faults
  included: the PowerPoint hides a clip that the deck's blend hides (on a dark page), and leaves white a clip that
  the deck leaves white (one that comes with a reveal step, or as a later step of an `.r-stack`, on such a slide:
  the browser does not blend inside a shown fragment).

## What does not carry over

- Editable text and links. Every slide is a picture; a link is text in it, and the command counts the links.
  References that scroll in the live deck show their top only (the command says so).
- lecturekit's keys (Space, R) and the pacing clock of the speaker view.
- A key pressed while a part plays: lecturekit plays on to the next stop; PowerPoint goes to the next slide at once,
  where the next part starts from its own beginning, so the rest of the part is skipped.
- Going back. PowerPoint shows a movie slide from its poster again; lecturekit holds the last frame.
- Reveal's slide transitions.

## The file's own layouts

The file has python-pptx's eleven standard layouts, widened to the 16:9 slide; the exported slides use the blank one.
A slide added in PowerPoint gets these layouts, not the deck's look. The notes page shows the slide at 16:9.

## The files PowerPoint gets

The movies are H.264 in MP4 with yuv420p pixels and their index first, and without sound: the live deck plays every
clip muted. A clip that already is such a file is embedded as it is; one with its index at the end or with a sound
track is copied with the index in front and the sound left out (no re-encoding); any other is re-encoded. The format is read
with ffprobe where it is installed, else from ffmpeg's own report, so this holds with the `export` extra alone. A
part of a clip in parts is always re-encoded, cut by frame number, and checked to have exactly its frames. A clip
used on several slides is stored once in the file. The timing of each slide is written in the form PowerPoint
itself writes (compared with files saved by PowerPoint 2007 and 2013); whether PowerPoint plays it as intended is
what the test below is for.

## Test it in PowerPoint before the talk

The export is checked with python-pptx, the Office XML schemas and LibreOffice; PowerPoint itself has not been run
on it. Before the talk, on the machine and the PowerPoint version of the venue if possible:

1. Open the file: it must open without a repair prompt.
2. Start the slide show from the first slide and step through every slide with the clicker or the arrow keys.
3. On each clip slide: the movie starts by itself (`auto`), its first picture is the poster, and when it ends it
   stays on its last frame. If PowerPoint rewinds to the poster instead, set "Rewind after playing" off on those
   movies in PowerPoint's Playback tab, or export the whole file again with `--video still`.
4. On a clip in parts: the parts join without a jump from one slide to the next.
5. Open Presenter View: the notes of each step are there.
6. If a movie stays black or does not play, export again with `--video still` and say which clip and which
   PowerPoint version (Windows or Mac) failed.

LibreOffice (`soffice --headless --convert-to pdf slides.pptx`) is a quick check that the file is well formed and
that the pictures and posters sit where they should; it says nothing about how PowerPoint plays the movies.
