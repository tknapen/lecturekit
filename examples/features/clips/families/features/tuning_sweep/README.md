# tuning_sweep

The feature deck's manim8 clip: two scenes, 6 s at 1280 by 720 and 30 fps, in the bridged lecturekit style.

- `gain` (0 to 3 s): the gain `g` of a tuning curve rises from 1 to 2; the peak doubles in place.
- `width` (3 to 6 s): the width `s` rises from 0.8 to 1.6; the curve spreads, the peak stays at 2.

Content: a toy analytic curve, `r(x) = g exp(-x² / (2 s²))`, chosen to show the two kinds of change. It is not a
model fitted to data and not a measurement, and the plot labels it so. Nothing in it needs a source.

The deck names it `clip="tuning_sweep"`; `lk clips examples/features --only tuning_sweep` renders it, and
`--mode dark` renders the dark preset. The checkpoints are `gain_low`, `gain_high` and `widened`; the still is
`widened`, the latest.
