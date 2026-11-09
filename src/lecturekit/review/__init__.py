"""The review loop as commands.

These were scratch scripts in a session folder; they are the part of the
method that makes review rounds fast, so they live here with arguments and
documentation. Each one answers one question about a built deck:

* :mod:`shoot`    what does every slide look like (PNG per slide, fragments optional)
* :mod:`frags`    which fragments does each slide have, and is a clip's fragment misplaced
* :mod:`measure`  how much of the 720 px does each slide use, what overflows the foot line
* :mod:`contrast` do the brand's text and role colours reach WCAG AA on its surfaces
* :mod:`overflow` what did Beamer complain about (overfull boxes) in the study PDF
* :mod:`figs`     what do the TikZ figures of a deck look like, before they are placed
"""
