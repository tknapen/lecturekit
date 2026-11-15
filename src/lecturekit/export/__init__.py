"""A built deck in another format, for a venue that will not take the live deck.

* :mod:`pptx`    `lk export pptx`: a PowerPoint file that keeps the look, the reveals, the clips and the notes

The pure parts (which clip is a movie or a still at each step, the rectangles, the notes text, the timing XML) are
in :mod:`plan` and :mod:`timing`, apart from the browser (:mod:`walk`) and ffmpeg (:mod:`media`).
"""

FORMATS = ("pptx",)
