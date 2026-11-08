# Examples

- `kickoff/`: the worked example of the method, the Coimbra workshop's opening deck: storyboard, plan, eight TikZ
  figures from `make_assets.py`, one clip on the Manim kit, `FACTS.md` and `MANIFEST.md`, both outputs, both presets.
- `features/`: every construct of the dialect on one small deck; the engine's test deck and the scaffold's model.

Each is a Quarto project whose `_extensions` entry is a symlink to the engine's extension, so that it builds from
this checkout; a project made with `lk new` holds a copy instead.
