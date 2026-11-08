# Episode 8: Publish and share

Length: 5 minutes.

## Goal

The continuous build, GitHub Pages, exporting the PDF, and how a colleague forks a project for their own course.

## What the viewer sees

A push. The workflow in `.github/workflows/build.yml` runs: Quarto and TeX, the Python environment with Playwright's Chromium, both example decks built in the paper and the dark preset, the contrast check, `lk review shoot` with a contact sheet, `measure` and `overflow`, the tests, the live decks and PDFs uploaded as artefacts, and the paper build deployed to Pages. The live kickoff deck at its Pages address, linked from the README; the PDF downloaded from the same build. Then a fork: a colleague clones a project repository, installs the pinned engine, and builds a deck with no engine code of their own.

## Commands

```sh
git push                      # .github/workflows/build.yml runs
quarto publish gh-pages       # the manual route, from a project folder
```

The colleague:

```sh
gh repo fork <owner>/<project> --clone
cd <project>
uv venv && source .venv/bin/activate
uv pip install "lecturekit==<the version the project pins>"
lk build 00-kickoff
```

## Points to make

- A project carries its sources and `assets/`, the vendored extension in `_extensions/lecturekit/`, and no development code; the Python kits are installed, not copied. `lk build` refuses a major-version mismatch between the vendored extension and the installed engine rather than produce a subtly different deck.
- The outputs can be committed beside the sources, so that a lecture can be read without the engine; the Pages site is the demonstration link.
- The clips are committed with `clips.json`, so that nobody has to render them to read the deck; a changed `revision` shows a stale one.
- `lk new --vendor-only --force <project>` upgrades a project's extension when a new engine is released.

## Artefacts

- `before/`: the repository before the push.
- `after/build-log.txt`: the workflow run's summary.
- `after/pages-url.txt`: the published addresses of the example decks.
- `after/slides-study.pdf`: the exported PDF.

## Notes

The workflow builds the engine's own examples (`examples/kickoff`, `examples/features`). The public project repository on the released engine (the Coimbra workshop's three decks) is in the plan's work list and does not exist yet; the fork half of the episode is recorded when it does. `quarto publish gh-pages` works today for a single deck.
