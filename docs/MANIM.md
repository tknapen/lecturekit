# The Manim kit

Every deck's clips import `lecturekit.manim` instead of carrying their own copy of the style. A deck's `anim/kit.py` is a two-line shim that `lk new` writes:

```python
from lecturekit.manim import *
HERE = Path(__file__).resolve().parent; DATA = HERE.parent / 'assets' / 'data'
```

and every clip starts with `from kit import *`, which gives it the modules below, with `HERE` and `DATA` as the deck's `anim/` and `assets/data/`. `lk clips` renders the scenes (CLIPS.md). Manim Community 0.22 needs Pillow below 11.3: `pip install lecturekit[clips]`.

## nmstyle: the house style

The clips carry no titles; the slide supplies the claim. Importing the kit sets the render to 1280 by 720 at 30 frames per second, a frame of 16 by 9 scene units, and the slide colour as background; `clip_size()` or `NM_CLIP_SIZE` change the size and keep the frame 9 units high.

Colours come from the deck's `_brand.yml`, found upwards from the working directory or named by `LECTUREKIT_BRAND` (`LECTUREKIT_MODE=dark` selects the dark side of a unified file), so a clip re-rendered after a restyle follows the new palette; the paper preset's values are the fall-back. The constants: `INK`, `MUTED`, `HAIR`, `PAPER`, `SLIDE`; `BLUE` (the concept blue), `TEAL` (state), `ORANGE` (update), `PURPLE` (context), `RED` and `CAVEAT`; `INPUT`, `EXAMPLE`, `ANCHOR`, `QUESTION`; the model colours `GAUSS`, `DOG`, `CSS`, `DN` and `FUTURE` (drawn dotted); `COLORS`, the whole dictionary, and `token(name)` for a project token that has no constant.

Fonts are the bundled TeX Gyre faces of the extension (and Roboto), registered with Pango; `SERIF` and `SANS` are the brand's heading and body families, so the dark preset's Roboto wins when it is active. `label(s, size=22, color=INK, serif=False)` is a `Text` in the house font. `Frame(left, bottom, width, height, u_range, w_range)` maps data coordinates to scene coordinates: call it with `(u, w)`, `inv(point)` goes back, `scale` gives scene units per data unit, `axes(u_ticks, w_ticks, u_label, w_label)` draws thin L-shaped axes in muted, `polyline(points, colour, width)` a trace. `normal_pdf(x, mu, sd)` is the Gaussian.

## nmnet: networks

`Net(sizes, width, height, radius, center)`: units as circles in layers, edges whose width and colour carry the weight (positive in blue, negative in orange). `set_weights(Ws)` and `weights_anim(Ws)` with `Ws[l]` of shape (n_{l+1}, n_l); `set_activations(acts)` and `activations_anim(acts)` with values in [0, 1] as fill; `forward(acts)` a teal sweep, `backward(deltas)` an orange one; `clear_rings()`, `label_layer(l, text)`, `label_units(l, texts)`. `unit_diagram(n_in, ...)` draws one unit: inputs, weights, sum, nonlinearity.

## nmpix: pixel grids

`PixelGrid(arr, size, cmap='grey'|'div', show_values)`: an array as squares, grey or diverging (blue positive, orange negative); `window(r, c, k)` a rectangle around a k by k patch, `fill_anim(r, c, v)`, `set_value(r, c, v)`, `blank()`, `cell(r, c)`. `colour_for(v, cmap)`, `conv2d(img, kernel)` (cross-correlation, as networks use it), `maxpool(img, p)`.

## nmfield: flows

For a two-dimensional dynamical system `f(u, w)` in a `Frame`: `arrows(fr, f)` and `streams(fr, f)` draw the field, `integrate(f, start, T)` (RK4) and `trajectory(fr, f, start, T)` a path from a start, `fixed_point(fr, u, w, stable)` a filled or open dot.

## nmprf: population receptive fields

Written for the Coimbra pRF workshop's lecture 2 and reused by the course's lectures 7 and 8.

- `clip_size((1920, 1080))` sets the render size; `NM_CLIP_SIZE` (for example `1440x1080`, set by `lk clips --size`) overrides it, and the frame stays 9 units high (16 by 9 at 16:9, 12 by 9 at 4:3).
- `VisualField(centre, radius, deg=8, look=(0, 0), square=False)`: a window onto the visual field in degrees. `pt`, `pts`, `outline`, `fixation`, `scale_bar`; `image(arr, colour, neg=None)` draws a numpy map (row 0 at the lowest y) as an image with a model-coloured ramp, transparent outside a circular window; light-grey apertures `bar(pos, w, theta)` (theta the motion direction; `pos` measured from `look`, the window's centre), `disc`, `ring`, `half(x, y, r, side)` with side `L`, `R`, `lower`, `upper` or `both`, and `square_patch`; `clipped(shape)` cuts a filled shape (a growing disc, say) to the window; `prf(x0, y0, s)` draws a pRF outline in ink.
- numpy fields: `grid`, `gauss2d` (peak 1), `gauss2d_density`, `dog2d`, `gabor2d` (with a `carrier` weight for morphing an envelope into a Gabor); `colour_ramp(arr, colour, neg=...)` returns an RGBA image (white at zero, the colour at the maximum, `neg` for negative values); `tint(colour, pct)` is TikZ's `colour!pct`.
- `HeightSurface(Z, half_width, scale, height, colorscale=[(colour, z), ...], shade=False)`: a 3-D surface over a square grid for a `ThreeDScene`, made of quads that `set_heights(Z)` reshapes and recolours in place, cheap enough to animate a parameter frame by frame (a colour scale that splits at zero colours a difference of Gaussians by sign; `shade=False` keeps the colours, faces are drawn back to front). `prf_surface(f, ...)` is the older `Surface`-based version, about ten times slower to animate.
- `FeatureStack(maps, size, step, shear, squash, center)`: feature maps as image planes in an oblique view (a 2-D scene: each map is a sheared image), with `plane_point`, `plane_outline`, `ellipse_on` (a pooling field drawn onto a plane) and `map_on` (an RGBA image on a plane, such as a translucent Gaussian). A vertical `step` such as `(0, -0.75)` stacks the maps as levels, plane 0 on top.
- `TracePanel(frame, t)`: traces that draw up to the time in a `ValueTracker` (`series`), and a cursor with a dot on each trace (`cursor`).
- `Dial(tracker, lo, hi, name, ticks=..., readout_at=None)`: an arc gauge with a needle and a readout `name = value` (`lo` may exceed `hi`, for a dial that turns a value down); `readout_at` moves the readout, for example `DOWN * 0.75` under a small dial's arc. Add `dial.live()` with it, after moving the dial: `live()` brings the moving parts to the dial's place.
- `Bars(frame)`: bars by slot (`bar(j, v0, v1, colour)`, stacked by passing the top of the bar below as `v0`), dashed outlines for predictions (`outline`) and labels under the slots (`under`).
- `baseline(label)` and `on_baseline(label, y)`: align `Text` labels of different words by their baselines (a row of names under windows, a legend), since 'odd' and 'grating' have different boxes.
- `APERTURE` is the light grey of stimulus apertures (ink at 20 percent). The model colours are the brand's: `GAUSS`, `DOG`, `CSS`, `DN` and `FUTURE` (drawn dotted); data and the voxel are `INK`. Blue is the Gaussian, so apertures are never blue.

## Provenance

The designs of `nmnet`, `nmpix` and `nmfield` follow scenes from 3Blue1Brown's videos (github.com/3b1b/videos): the network drawings of the 2017 neural-network series, the 2022 convolution video, the 2019 differential-equations series. They are used as storyboards only, as decided on 1 November 2026: the code is written fresh for Manim Community 0.22, each module's docstring names the scene it follows, and `NOTICE.md` carries the entry. The kickoff example's clip uses `nmprf` and `nmstyle` only.
