# tuning_sweep

The feature deck's manim8 clip: two scenes, 6 s at 1280 by 720 and 30 fps, in the bridged lecturekit style.

- `gain` (0 to 3 s): the gain `g` of a tuning curve rises from 1 to 2; the peak doubles in place.
- `width` (3 to 6 s): the width `s` rises from 0.8 to 1.6; the curve spreads, the peak stays at 2.

Content: a toy analytic curve, `r(x) = g exp(-x² / (2 s²))`, chosen to show the two kinds of change. It is not a
model fitted to data and not a measurement, and the plot labels it so. Nothing in it needs a source.

The deck names it `clip="tuning_sweep"`; `lk clips examples/features --only tuning_sweep` renders it, and
`--mode dark` renders the dark preset. The checkpoints are `gain_low`, `gain_high` and `widened`; the still is
`widened`, the latest.

`gain_low` (1.2 s, "gain 1") and `gain_high` (2.3 s, "gain 2") are stops (ADR-045), so a deck can hold the clip
there: `clips.json` lists them as candidates, and the feature deck's slide "A manim8 clip in parts" chooses both.
manim8 wants 0.3 s with nothing moving before a stop, and the closing fade of `gain` starts at 2.35 s (3 s less
the style's 0.65 s transition), so the sweep of the gain was moved and shortened: it ran from 0.9 s for 1.3 s and
now runs from 1.3 s for 0.7 s. That leaves 0.35 s after the reveal (0 to 0.85 s) before `gain_low`, which moved
from 0.88 s to 1.2 s, a tenth of a second before the sweep starts, so the hold does not show the sweep's readout;
and 0.3 s after the sweep before `gain_high`. The width scene is unchanged.
