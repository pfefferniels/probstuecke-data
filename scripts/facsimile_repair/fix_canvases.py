#!/usr/bin/env python3
"""One-off repair: point every <surface> to the right BSB canvas.

Commit 6fb5c80 (Feb 2026) renumbered the canvases of many surfaces with
shifts that differ from file to file; several files had never been converted
from the canvas numbering BSB used in 2019 (canvas = 1731 page + 84) or 2023
(page + 68). The canvases below were determined from the printed page numbers
and headings on the scans (see the concordance in scripts/check_facsimile.py)
and, for surfaces with zones, from the IIIF annotation lists of 2019
(<n>/mattheson/facsimile_de.json, removed in 5644b39), whose canvas numbers
are today's + 22. Where a file was encoded with explicit page numbers
(surface/@n, page-named xml:ids in 2023), those pages are restored.

The script
  - sets the canvas number in graphic/@target or graphic/@url,
  - renames surface/@xml:id facs-p<old> to facs-p<new canvas> (ULID ids are kept),
  - repoints every pointer to a surface (pb/@facs, and p/@facs and
    notatedMusic/@facs in the 1719 commentaries) to the surface of the page
    the element is on: for MEI page breaks of the 1731 print the page whose
    zones the following measures use, for other MEI page breaks the n-th
    surface of the print, for TEI elements the page given by the nearest
    preceding pb/@n (the page before the first pb for text before it).
Pointers to zones are not touched: zones move with their surface. Files are
edited by targeted text replacement; nothing is re-serialised.

Usage: python3 scripts/facsimile_repair/fix_canvases.py [--apply]
"""
import re
import sys
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import xmledit as X  # noqa: E402
import check_facsimile as CF  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'


def seq(first_id, n, first_canvas):
    """facs-p<first_id + i> -> first_canvas + i for i < n."""
    return {f'facs-p{first_id + i}': first_canvas + i for i in range(n)}


CANVAS = {
    # --- 1719, commentaries: the pages the encoders listed, shifted back ------
    'encodings/1/mattheson/comments_1st.xml': seq(280, 3, 279),     # pp. 105-107
    'encodings/2/mattheson/comments_1st.xml': seq(286, 5, 285),     # pp. 111-115
    'encodings/4/mattheson/comments_1st.xml': seq(298, 3, 297),     # pp. 123-125
    'encodings/5/mattheson/comments_1st.xml': seq(302, 3, 301),     # pp. 127-129
    'encodings/6/mattheson/comments_1st.xml': seq(304, 2, 306),     # pp. 132-133
    'encodings/8/mattheson/comments_1st.xml': seq(316, 3, 315),     # pp. 141-143
    'encodings/10/mattheson/comments_1st.xml': seq(363, 6, 362),    # pp. 152-157
    'encodings/11/mattheson/comments_1st.xml': {'facs-p372': 371, 'facs-p373': 372, 'facs-p382': 373},  # pp. 161-163
    'encodings/13/mattheson/comments_1st.xml': seq(389, 4, 388),    # pp. 170-173
    'encodings/16/mattheson/comments_1st.xml': seq(415, 6, 408),    # pp. 188-193
    'encodings/17/mattheson/comments_1st.xml': seq(417, 3, 416),    # pp. 196-198
    'encodings/18/mattheson/comments_1st.xml': seq(422, 6, 418),    # pp. 198-203 (surface/@n)
    'encodings/20/mattheson/comments_1st.xml': seq(432, 7, 428),    # pp. 208-214
    'encodings/21/mattheson/comments_1st.xml': seq(437, 7, 433),    # pp. 213-219
    'encodings/22/mattheson/comments_1st.xml': {'facs-p443': 440, 'facs-p444': 441, 'facs-p445': 442,
                                                'facs-p446': 443, 'facs-p447': 444, 'facs-p450': 445},  # pp. 220-225
    'encodings/23/mattheson/comments_1st.xml': {'facs-p450': 446, 'facs-p451': 447,
                                                'facs-p452': 450, 'facs-p453': 451},  # pp. 226-229
    # --- 1719, scores -----------------------------------------------------------
    'encodings/8/mattheson/score.xml': seq(310, 4, 312),            # pp. 138-141
    'encodings/11/mattheson/score.xml': seq(360, 4, 368),           # pp. 158-161
    'encodings/14/mattheson/score-2.xml': {'facs-p393': 392, 'facs-p396': 393,   # pp. 174-175
                                           'facs-p441': 440, 'facs-p442': 441},  # 1731 pp. 378-379
    'encodings/15/mattheson/score.xml': seq(392, 2, 398),           # pp. 178-179
    'encodings/23/mattheson/score.xml': {'facs-p450': 446, 'facs-p451': 447},    # pp. 226-227
    'encodings/24/mattheson/score.xml': seq(456, 3, 452),           # pp. 230-232
    'encodings/20/molinaro/score.xml': {**seq(388, 4, 428), **seq(498, 4, 476)},  # = 20/mattheson
    'encodings/21/molinaro/score.xml': {**seq(399, 2, 435), **seq(505, 2, 483)},  # = 21/mattheson
    # --- 1731 -----------------------------------------------------------------
    'encodings/1/mattheson/comments_de.xml': seq(368, 3, 367),      # pp. 305-307
    'encodings/5/mattheson/comments_de.xml': seq(391, 2, 390),      # pp. 328-329
    'encodings/7/mattheson/comments_de.xml': seq(380, 2, 400),      # pp. 338-339
    'encodings/10/mattheson/comments_de.xml': {'facs-p438': 416, 'facs-p439': 417, 'facs-p443': 421},
    'encodings/11/mattheson/comments_de.xml': seq(447, 3, 425),     # pp. 363-365
    'encodings/12/mattheson/comments_de.xml': seq(452, 4, 430),     # pp. 368-371
    'encodings/13/mattheson/comments_de.xml': seq(458, 4, 436),     # pp. 374-377
    'encodings/14/mattheson/comments_de.xml': seq(464, 2, 442),     # pp. 380-381
    'encodings/16/mattheson/comments_de.xml': {'facs-p478': 456, 'facs-p479': 457, 'facs-p483': 461},
    'encodings/17/mattheson/comments_de.xml': seq(486, 3, 464),     # pp. 402-404
    'encodings/22/mattheson/comments_de.xml': seq(491, 4, 488),     # pp. 426-429
    'encodings/23/mattheson/comments_de.xml': seq(494, 6, 490),     # pp. 428-433
    'encodings/24/mattheson/comments_de.xml': seq(503, 31, 496),    # pp. 434-464
    'encodings/4/mattheson/score.xml': seq(372, 4, 382),            # pp. 320-323
    'encodings/3/hill/score.xml': {'facs-p64': 378, 'facs-p65': 379},  # = 3/mattheson
    'encodings/10/mattheson/measure_annotations.xml': {             # Marcello aria, pp. 356-359
        'surface_01DRXXBW793Y78RN1NJJH4NB9M': 418, 'surface_01DRXXBW81W088TTEG7KJBF5N4': 419,
        'surface_01DRXXBW8SPTS35QF40HT64APP': 420, 'surface_01DRXXBW9KP46SYD696V2YR4R6': 421},
    # graphic/@target is an image URL instead of the canvas
    'encodings/2/mattheson/score.xml': {'facs-p282': 282},
}

# TEI page breaks whose @n is wrong (left as it is; reported): the page they
# actually mark, from their position in the text and the scans.
PB_PAGE = {
    'encodings/5/mattheson/comments_de.xml': {104: 328},              # n="329" twice
    'encodings/6/mattheson/comments_de.xml': {201: 335},              # n="334" twice
    'encodings/7/mattheson/comments_de.xml': {102: 338, 182: 339},    # n="318", "319" (copied from No. 3)
    'encodings/19/mattheson/comments_de.xml': {159: 413},             # n="412" twice
}

# MEI files whose page breaks of a print are matched to its surfaces by order:
# No. 8 (1719) gives the four pages as 136-139 (pp. 138-139 are misprinted
# 136-137; the real pages are 138-141).
BY_ORDER = {('encodings/8/mattheson/score.xml', '1719')}

# TEI elements on another page than the preceding pb says: No. 20 (1719),
# music example 7 is at the top of p. 214, before the pb.
ELEMENT_PAGE = {
    'encodings/20/mattheson/comments_1st.xml': {'music-example7': 214},
}

# Pointers to add where the previous fix (43df75e) had to drop them because
# the file had no surface for the page: No. 20, 1719, §. 1 and the beginning
# of §. 2 are on p. 211 (canvas 431).
ADD = {
    'encodings/20/mattheson/comments_1st.xml': ['p1-1', 'music-example1', 'p1-2', 'music-example2'],
}

CANVAS_IN_URL = re.compile(r'^(https://api\.digitale-sammlungen\.de/iiif/presentation/v2/(bsb\d{8})/canvas/)(\d+)$')
IMAGE_URL = re.compile(r'^https://api\.digitale-sammlungen\.de/iiif/image/v2/(bsb\d{8})_(\d{5})/full/full/0/default\.jpg$')


def local(el):
    return etree.QName(el).localname


def plan(path):
    """Return (surface edits, pointer edits) for one file."""
    rel = path.relative_to(REPO).as_posix()
    table = CANVAS.get(rel, {})
    tree = etree.parse(str(path), CF.PARSER)
    root = tree.getroot()
    is_mei = local(root) == 'mei'

    surfaces = []   # dicts: id, new_id, print, canvas, new_canvas, decls, zone ids
    for s in root.iter('{*}surface'):
        g = next(s.iter('{*}graphic'))
        attr = 'target' if g.get('target') is not None else 'url'
        url = g.get(attr)
        m = CANVAS_IN_URL.match(url) or IMAGE_URL.match(url)
        bsb, canvas = m.group(2 if m.re is CANVAS_IN_URL else 1), int(m.group(3 if m.re is CANVAS_IN_URL else 2))
        sid = s.get(XML_ID)
        new_canvas = table.get(sid, canvas)
        new_id = sid
        if sid in table and re.fullmatch(r'facs-p\d+', sid):
            new_id = f'facs-p{new_canvas}'
        surfaces.append({'id': sid, 'new_id': new_id, 'print': CF.PRINTS[bsb], 'bsb': bsb, 'canvas': canvas,
                         'new_canvas': new_canvas, 'attr': attr, 'url': url,
                         'decls': s.getparent().get('decls') or '',
                         'zones': {z.get(XML_ID) for z in s.iter('{*}zone')}, 'line': s.sourceline,
                         'gline': g.sourceline})
    unknown = set(table) - {s['id'] for s in surfaces}
    if unknown:
        # already applied? then every target canvas is there, under its own id
        done = {(s['id'], s['canvas']) for s in surfaces}
        if all((f'facs-p{c}' if re.fullmatch(r'facs-p\d+', sid) else sid, c) in done for sid, c in table.items()):
            for s in surfaces:
                s['new_canvas'], s['new_id'] = s['canvas'], s['id']
        else:
            raise SystemExit(f'{rel}: unknown surfaces {sorted(unknown)}')
    new_ids = [s['new_id'] for s in surfaces]
    if len(set(new_ids)) != len(new_ids):
        raise SystemExit(f'{rel}: duplicate surface ids after renaming: {new_ids}')
    by_id = {s['id']: s for s in surfaces}
    zone_surface = {z: s for s in surfaces for z in s['zones']}

    def surface_for(print_, canvas):
        hits = [s for s in surfaces if s['print'] == print_ and s['new_canvas'] == canvas]
        return hits[0] if len(hits) == 1 else None

    pointer_edits = []   # (line, local name, old value, new value)
    elements = [el for el in root.iter() if isinstance(el.tag, str)]
    file_print = surfaces[0]['print'] if surfaces and len({s['print'] for s in surfaces}) == 1 else None

    if is_mei:
        # Page breaks: the page named by @n if the file has a surface for it
        # (first occurrence of that @n); otherwise, for the 1731 print, the
        # page whose zones the following measures use, and for the 1719 print
        # the k-th surface of the print for the k-th page break.
        count, seen = {}, set()
        for i, el in enumerate(elements):
            if local(el) != 'pb' or not el.get('facs'):
                continue
            old = el.get('facs')
            target = by_id.get(old.lstrip('#'))
            src = el.get('source') or ''
            print_ = CF.DECLS.get(src) or (target['print'] if target else None)
            if target is not None and CF.DECLS.get(src) != target['print']:
                print_ = target['print']   # wrong @source (reported); the pointer decides
            prints = [s for s in surfaces if s['print'] == print_]
            k = count.get(print_, 0)
            count[print_] = k + 1
            n = el.get('n')
            by_n = surface_for(print_, CF.page_to_canvas(print_, int(n))) if (n or '').isdigit() else None
            new = None
            if (rel, print_) in BY_ORDER:
                new = prints[k]
            elif by_n is not None and (print_, n) not in seen:
                new = by_n
            elif print_ == '1731' and any(s['zones'] for s in prints):
                for el2 in elements[i + 1:]:
                    if local(el2) in ('staff', 'measure') and el2.get('facs'):
                        hits = [zone_surface.get(t.lstrip('#')) for t in el2.get('facs').split()]
                        hits = [h for h in hits if h is not None and h['print'] == '1731']
                        if hits:
                            new = hits[0]
                            break
            elif k < len(prints):
                new = prints[k]
            seen.add((print_, n))
            if new is None:
                raise SystemExit(f'{rel}: no surface for pb line {el.sourceline}')
            value = '#' + new['new_id']
            if value != old:
                pointer_edits.append((el.sourceline, 'pb', old, value))
    else:
        # TEI: page of each element from pb/@n
        first_pb = next((el for el in elements if local(el) == 'pb' and (el.get('n') or '').isdigit()), None)
        if first_pb is None:
            return surfaces, pointer_edits
        overrides = PB_PAGE.get(rel, {})

        def pb_page(pb):
            return overrides.get(pb.sourceline, int(pb.get('n')))

        page = pb_page(first_pb) - 1
        pages_of = {}
        for el in elements:
            if local(el) == 'pb' and (el.get('n') or '').isdigit():
                page = pb_page(el)
            pages_of[el] = page
        for el in elements:
            name = local(el)
            xml_id = el.get(XML_ID)
            add = xml_id in ADD.get(rel, []) and el.get('facs') is None
            old = el.get('facs')
            if old is None and not add:
                continue
            tokens = old.split() if old else []
            if tokens and not all(t.lstrip('#') in by_id for t in tokens):
                if any(t.lstrip('#') in by_id for t in tokens):
                    raise SystemExit(f'{rel}: mixed pointer {old!r}')
                continue   # pointers to zones
            if name == 'pb':
                pages = [pb_page(el)]
            else:
                start = ELEMENT_PAGE.get(rel, {}).get(xml_id, pages_of[el])
                inner = [pb_page(p) for p in el.iter('{*}pb') if (p.get('n') or '').isdigit()]
                pages = [start] + [p for p in inner if p != start]
            targets = []
            for p in pages:
                s = surface_for(file_print, CF.page_to_canvas(file_print, p))
                if s is None:
                    raise SystemExit(f'{rel}: line {el.sourceline} {name} {xml_id}: no surface for p. {p}')
                targets.append('#' + s['new_id'])
            value = ' '.join(targets)
            if value != old:
                pointer_edits.append((el.sourceline, name, old, value))
    return surfaces, pointer_edits


def apply(path, surfaces, pointer_edits):
    text = path.read_text(encoding='utf-8')
    for s in surfaces:
        if s['new_canvas'] == s['canvas'] and s['new_id'] == s['id'] and CANVAS_IN_URL.match(s['url']):
            continue
        span = X.tag_span(text, 'surface', 'xml:id', s['id'])
        tag = text[span[0]:span[1]]
        if s['new_id'] != s['id']:
            tag = X.set_attr(tag, 'xml:id', s['new_id'] + '\0')   # mark: renamed in this run
        text = X.replace_span(text, span, tag)
        gspan = X.tag_at_line(text, 'graphic', s['gline'], must_contain=s['url'])
        gtag = text[gspan[0]:gspan[1]]
        url = f'https://api.digitale-sammlungen.de/iiif/presentation/v2/{s["bsb"]}/canvas/{s["new_canvas"]}'
        text = X.replace_span(text, gspan, X.set_attr(gtag, s['attr'], url))
    text = text.replace('\0', '')
    for line, name, old, new in pointer_edits:
        span = X.tag_at_line(text, name, line)
        tag = text[span[0]:span[1]]
        if old is None:
            tag = X.add_attr(tag, 'facs', new, after='xml:id')
        else:
            if X.get_attr(tag, 'facs') != old:
                raise SystemExit(f'{path}: line {line}: @facs is not {old!r}')
            tag = X.set_attr(tag, 'facs', new)
        text = X.replace_span(text, span, tag)
    path.write_text(text, encoding='utf-8')


def main():
    do_apply = '--apply' in sys.argv
    total_s = total_p = 0
    for path in sorted((REPO / 'encodings').rglob('*.xml'), key=lambda p: [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', p.as_posix())]):
        rel = path.relative_to(REPO).as_posix()
        if '<surface' not in path.read_text(encoding='utf-8'):
            continue
        if 'facsimile/bsb' in path.read_text(encoding='utf-8'):
            continue   # 5/mattheson/comments_en.xml: local images, handled separately
        surfaces, pointer_edits = plan(path)
        changed = [s for s in surfaces if s['new_canvas'] != s['canvas'] or not CANVAS_IN_URL.match(s['url'])]
        if not changed and not pointer_edits:
            continue
        print(rel)
        for s in changed:
            print(f"  surface {s['id']:>14} -> {s['new_id']:<14} canvas {s['canvas']} -> {s['new_canvas']} ({s['print']})")
        for line, name, old, new in pointer_edits:
            print(f'  line {line:<5} {name:<12} facs {old!r} -> {new!r}')
        total_s += len(changed)
        total_p += len(pointer_edits)
        if do_apply:
            apply(path, surfaces, pointer_edits)
    print(f'{total_s} surfaces, {total_p} pointers' + (' changed.' if do_apply else ' to change (dry run).'))


if __name__ == '__main__':
    main()
