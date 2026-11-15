"""The `p:timing` of a slide with movies, as PowerPoint itself writes it.

python-pptx's `add_movie` writes only a `p:video` node: the movie plays when it is clicked. This module writes the
whole `p:timing` instead, after every movie of the slide has been added, so that a slide never carries two (which
PowerPoint reports as a corrupt file: python-pptx issue 954). The forms were compared, element for element, with
files PowerPoint saved (LibreOffice's test data: bnc591147.pptx from PowerPoint 2007 with a movie set to start
automatically, tdf106867.pptx from PowerPoint 2013 with a movie played on a click):

* `autoplay`: the main sequence of "Start: Automatically". One click par that begins with the main sequence
  (`onBegin` of time node 2), one group par, and per movie a Play effect (`presetID 1`, class `mediacall`,
  `playFrom(0.0)` for the movie's length in ms): the first `afterEffect`, the others `withEffect`, so they start
  together on entry. No click of the slide is spent on them.
* always, per movie: the interactive sequence PowerPoint adds to every movie (a click on the movie toggles pause,
  `presetID 2`), then the movie's own `p:video` node (volume 80 %, never started by time).

Time node ids are numbered 1, 2, ... in document order, as PowerPoint numbers them; every `spid` is the shape id of
a movie on the slide. Without `autoplay` the timing is PowerPoint 2013's for a movie played when clicked on.
"""

from __future__ import annotations

from xml.sax.saxutils import quoteattr

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _effect(nid: int, spid: int, dur: int, first: bool) -> str:
    node = "afterEffect" if first else "withEffect"
    return (f'<p:par><p:cTn id="{nid}" presetID="1" presetClass="mediacall" presetSubtype="0" fill="hold" '
            f'nodeType="{node}"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
            f'<p:cmd type="call" cmd="playFrom(0.0)"><p:cBhvr><p:cTn id="{nid + 1}" dur="{dur}" fill="hold"/>'
            f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:cmd></p:childTnLst></p:cTn></p:par>')


def _toggle(nid: int, spid: int) -> str:
    tgt = f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'
    return (f'<p:seq concurrent="1" nextAc="seek"><p:cTn id="{nid}" restart="whenNotActive" fill="hold" '
            f'evtFilter="cancelBubble" nodeType="interactiveSeq"><p:stCondLst><p:cond evt="onClick" delay="0">{tgt}'
            f'</p:cond></p:stCondLst><p:endSync evt="end" delay="0"><p:rtn val="all"/></p:endSync><p:childTnLst>'
            f'<p:par><p:cTn id="{nid + 1}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
            f'<p:par><p:cTn id="{nid + 2}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
            f'<p:par><p:cTn id="{nid + 3}" presetID="2" presetClass="mediacall" presetSubtype="0" fill="hold" '
            f'nodeType="clickEffect"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
            f'<p:cmd type="call" cmd="togglePause"><p:cBhvr><p:cTn id="{nid + 4}" dur="1" fill="hold"/>{tgt}'
            f'</p:cBhvr></p:cmd></p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par></p:childTnLst>'
            f'</p:cTn></p:par></p:childTnLst></p:cTn><p:nextCondLst><p:cond evt="onClick" delay="0">{tgt}</p:cond>'
            f'</p:nextCondLst></p:seq>')


def _video(nid: int, spid: int) -> str:
    return (f'<p:video><p:cMediaNode vol="80000"><p:cTn id="{nid}" fill="hold" display="0"><p:stCondLst>'
            f'<p:cond delay="indefinite"/></p:stCondLst></p:cTn><p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'
            f'</p:cMediaNode></p:video>')


def timing_xml(movies: list[tuple[int, int]], autoplay: bool = True) -> str:
    """The `p:timing` element for the movies of one slide, [(shape id, length in ms), ...] in shape order."""
    if not movies:
        raise ValueError("a timing needs at least one movie")
    for spid, dur in movies:
        if int(spid) < 1 or int(dur) < 1:
            raise ValueError(f"movie {spid}: a shape id and a length of at least 1 ms are needed, not {dur}")
    nid, main = 2, ""                   # 1 is the root; with autoplay, 2 to 4 are the main sequence and its pars
    if autoplay:
        effects = []
        nid = 5
        for i, (spid, dur) in enumerate(movies):
            effects.append(_effect(nid, int(spid), int(dur), first=i == 0))
            nid += 2
        main = ('<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
                '<p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/>'
                '<p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>'
                '<p:par><p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst>'
                f'<p:childTnLst>{"".join(effects)}</p:childTnLst></p:cTn></p:par>'
                '</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn>'
                '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
                '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>'
                '</p:seq>')
    per_movie = []
    for spid, _dur in movies:
        per_movie.append(_toggle(nid, int(spid)))
        nid += 5
        per_movie.append(_video(nid, int(spid)))
        nid += 1
    return (f'<p:timing xmlns:p={quoteattr(P_NS)}><p:tnLst><p:par>'
            '<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
            f'{main}{"".join(per_movie)}'
            '</p:childTnLst></p:cTn></p:par></p:tnLst></p:timing>')
