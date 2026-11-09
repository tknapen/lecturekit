"""Checkpoints: the frames of a kit clip where a deck may hold it on a key press.

    class Sweep(Scene):
        def construct(self):
            ...
            self.play(bar.animate.shift(4 * RIGHT), run_time=3)
            checkpoint(self, "first_sweep", label="rightward sweep", rest=0.6)
            self.play(bar.animate.shift(4 * LEFT), run_time=3)

`checkpoint(self, id, label=None, rest=0.0)` waits half the rest, opens a Manim section of type
`lecturekit.checkpoint` named by the id, and waits the other half. The stop is the first frame of that section;
`lk clips` renders kit scenes with `--save_sections` and finds the frame by adding up the frames of the sections
before it. The rest before the stop is what hides a browser's early pause (the live deck pauses a frame or two
before the stop, and up to 0.3 s before it without `requestVideoFrameCallback`), so `rest=0.6` is the usual value:
0.3 s before, 0.3 s after. `lk clips` measures the rests on the pixels, and a deck refuses a stop with less than
three frames of unchanged picture before it.

The id is a slug (`[a-z][a-z0-9_]*`, at most 64 characters) other than `start`, `end` and `all`, which the deck's
`stops=` and `.stop ref=` give a meaning of their own; the label is plain text of 1 to 40 characters, the id with
spaces by default. A checkpoint is a candidate: the deck chooses which ones are stops (`stops="first_sweep"`).

This module imports nothing of Manim, so that its rules can be tested without it.
"""

from __future__ import annotations

import json
import os
import re

__all__ = ["checkpoint"]

#: the Manim section type of a checkpoint (Manim leaves section types to third-party tools)
CHECKPOINT_SECTION = "lecturekit.checkpoint"
#: `lk clips` names a file here; each checkpoint appends its id, label and rest to it as one JSON line
CHECKPOINTS_ENV = "NM_CHECKPOINTS_FILE"
STOP_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
RESERVED = ("start", "end", "all")
LABEL_MAX = 40


def checkpoint(self, id, label=None, rest=0.0):
    """Mark the frame where a deck may hold this clip: wait `rest / 2` seconds, open a section of type
    `lecturekit.checkpoint` named `id`, wait `rest / 2` more. Called as `checkpoint(self, "id")` in `construct`."""
    sid = str(id)
    if not STOP_ID.match(sid) or sid in RESERVED:
        raise ValueError(f"checkpoint id {sid!r}: a slug ([a-z][a-z0-9_]*, at most 64 characters) other than "
                         f"{', '.join(RESERVED)}")
    if label is not None:
        label = str(label)
        if not 1 <= len(label) <= LABEL_MAX or "\n" in label:
            raise ValueError(f"checkpoint {sid}: the label is plain text of 1 to {LABEL_MAX} characters, one line")
    rest = float(rest)
    if rest < 0:
        raise ValueError(f"checkpoint {sid}: rest is {rest:g} s; it cannot be negative")
    seen = self.__dict__.setdefault("_lk_checkpoints", [])
    if sid in seen:
        raise ValueError(f"checkpoint {sid} is set twice in {type(self).__name__}")
    seen.append(sid)
    if rest > 0:
        self.wait(rest / 2)
    self.next_section(sid, section_type=CHECKPOINT_SECTION)
    path = os.environ.get(CHECKPOINTS_ENV)
    if path:
        record = {"id": sid, "label": label, "rest": rest, "scene": type(self).__name__}
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({k: v for k, v in record.items() if v is not None}) + "\n")
    if rest > 0:
        self.wait(rest / 2)
