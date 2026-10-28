#!/usr/bin/env python3
"""One-off repair: move the zones of the 1731 print to the current BSB images.

All zones were drawn in 2019 on the images BSB served then (1998 px wide).
BSB has since replaced the images of the Grosse General-Bass-Schule
(bsb10598495) with a new digitisation: the pages are cropped and scaled
differently, so the old pixel coordinates no longer hit the music. Per page
the old coordinates map to the current image by a uniform scale and a shift,

    x' = s * x + tx,  y' = s * y + ty,

with s between 0.99 and 1.06 and shifts of up to 70 px. The parameters of
every page are in page_transforms.tsv, by group of files:

  score                 MEI scores (Mattheson, the copies by Hill, Molinaro and
                        score-2.xml): rows of zones fitted to the staves of the
                        current image, horizontal shift from the barlines
  commentary            TEI commentaries: shift from the text column, the
                        paragraph headings and the first line of the page
  measure_annotations   10/mattheson/measure_annotations.xml, made by an
                        automatic measure detector on the same pages: zones
                        fitted to the staff pairs, overlaps on barlines

The parameters were estimated with registration tools outside the repository
and checked on overlays of every page. Zones are clamped to the image. A
surface whose graphic already has the size of the current image is taken as
done, so the script can be run again without moving zones twice.

The script also sets surface/@lrx/@lry and graphic/@width/@height to the size
of the current image (canvas_sizes.tsv, from the IIIF info.json of every
canvas), keeping each file's convention (lrx = width or width - 1, "px").
By default it does so for the surfaces whose zones it moves; with
--all-sizes for every surface that points to a BSB canvas.

Usage: python3 scripts/facsimile_repair/rescale_zones.py [--all-sizes] [--apply]
"""
import csv
import re
import sys
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xmledit as X  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'
# the canvas (until image_urls.py) or the image of the page
CANVAS_RE = re.compile(r'https://api\.digitale-sammlungen\.de/iiif/(?:presentation/v2/(bsb\d+)/canvas/(\d+)|image/v2/(bsb\d+)_(\d+)/full/full/0/default\.jpg)$')
BSB_1731 = 'bsb10598495'


def read_tsv(name):
    with open(HERE / name, encoding='utf-8') as f:
        lines = [ln for ln in f if not ln.startswith('#')]
    return list(csv.DictReader(lines, delimiter='\t'))


def sizes():
    return {(r['bsb'], int(r['canvas'])): (int(r['width']), int(r['height'])) for r in read_tsv('canvas_sizes.tsv')}


def transforms():
    return {(r['group'], int(r['canvas'])): (float(r['s']), float(r['tx']), float(r['ty']))
            for r in read_tsv('page_transforms.tsv')}


def group_of(rel, root):
    if rel.endswith('/measure_annotations.xml'):
        return 'measure_annotations'
    return 'commentary' if etree.QName(root).localname == 'TEI' else 'score'


def graphic_span(text, surface_span):
    """Span of the <graphic> start tag that belongs to the surface starting at surface_span."""
    m = re.compile(r'<(?:\w+:)?graphic\b[^<>]*>').search(text, surface_span[1])
    nxt = re.compile(r'<(?:\w+:)?(?:zone|surface)\b|</(?:\w+:)?surface>').search(text, surface_span[1])
    if not m or (nxt and nxt.start() < m.start()):
        raise ValueError(f'no graphic after surface at {surface_span}')
    return m.span()


def with_unit(old, value):
    return f'{value}px' if old.endswith('px') else str(value)


def resize_surface(text, sid, size):
    """Set the surface and graphic size; return (text, changed)."""
    w, h = size
    sspan = X.tag_span(text, 'surface', 'xml:id', sid)
    stag = text[sspan[0]:sspan[1]]
    gspan = graphic_span(text, sspan)
    gtag = text[gspan[0]:gspan[1]]
    gw, gh = X.get_attr(gtag, 'width'), X.get_attr(gtag, 'height')
    off_x = int(X.get_attr(stag, 'lrx')) - int(gw.rstrip('px')) if gw else 0
    off_y = int(X.get_attr(stag, 'lry')) - int(gh.rstrip('px')) if gh else 0
    new_s = X.set_attr(X.set_attr(stag, 'lrx', str(w + off_x)), 'lry', str(h + off_y))
    new_g = gtag
    if gw:
        new_g = X.set_attr(new_g, 'width', with_unit(gw, w))
    if gh:
        new_g = X.set_attr(new_g, 'height', with_unit(gh, h))
    if (new_s, new_g) == (stag, gtag):
        return text, False
    # the graphic follows the surface: replace it first
    text = X.replace_span(text, gspan, new_g)
    text = X.replace_span(text, sspan, new_s)
    return text, True


def declared_size(text, sid):
    sspan = X.tag_span(text, 'surface', 'xml:id', sid)
    gtag = text[slice(*graphic_span(text, sspan))]
    gw, gh = X.get_attr(gtag, 'width'), X.get_attr(gtag, 'height')
    return (int(gw.rstrip('px')), int(gh.rstrip('px'))) if gw and gh else None


def move_zone(text, zid, T, size):
    s, tx, ty = T
    w, h = size
    span = X.tag_span(text, 'zone', 'xml:id', zid)
    tag = text[span[0]:span[1]]
    clamped = 0
    new = tag
    for attr, t, limit in (('ulx', tx, w), ('uly', ty, h), ('lrx', tx, w), ('lry', ty, h)):
        v = X.get_attr(tag, attr)
        if v is None:
            print(f'  {zid}: no @{attr} (left out)')
            continue
        n = round(s * int(v) + t)
        if n < 0 or n > limit:
            clamped = max(clamped, -n if n < 0 else n - limit)
            n = min(max(n, 0), limit)
        new = X.set_attr(new, attr, str(n))
    return X.replace_span(text, span, new), clamped


def main():
    do_apply = '--apply' in sys.argv
    all_sizes = '--all-sizes' in sys.argv
    SIZES = sizes()
    TRANS = transforms()
    used = set()
    totals = {'zones': 0, 'clamped': 0, 'surfaces': 0, 'files': 0}
    for path in sorted((REPO / 'encodings').rglob('*.xml')):
        rel = path.relative_to(REPO).as_posix()
        text = path.read_text(encoding='utf-8')
        if '<facsimile' not in text:
            continue
        root = etree.fromstring(text.encode('utf-8'))
        group = group_of(rel, root)
        new_text = text
        nz = nc = ns = 0
        for surface in root.iter('{*}surface'):
            graphic = next(surface.iter('{*}graphic'), None)
            url = (graphic.get('target') or graphic.get('url') or '') if graphic is not None else ''
            m = CANVAS_RE.match(url)
            if not m:
                continue          # not a BSB canvas (legacy local images of 5/mattheson/comments_1731_en.xml)
            bsb, canvas = m.group(1) or m.group(3), int(m.group(2) or m.group(4))
            sid = surface.get(XML_ID)
            zones = [z for z in surface.iter('{*}zone')]
            if zones and declared_size(new_text, sid) == SIZES[(bsb, canvas)]:
                print(f'{rel}: {sid} already has the size of the current image; zones left as they are')
                zones = []
                used.add((group, canvas))
            if zones:
                if bsb != BSB_1731:
                    raise SystemExit(f'{rel}: zones on {bsb} canvas {canvas}: no transformation known')
                T = TRANS.get((group, canvas))
                if T is None:
                    raise SystemExit(f'{rel}: no transformation for {group} canvas {canvas}')
                used.add((group, canvas))
                for z in zones:
                    new_text, clamped = move_zone(new_text, z.get(XML_ID), T, SIZES[(bsb, canvas)])
                    nz += 1
                    if clamped:
                        nc += 1
                        print(f'  {z.get(XML_ID)}: clamped by {clamped} px')
            if zones or all_sizes:
                new_text, changed = resize_surface(new_text, sid, SIZES[(bsb, canvas)])
                ns += changed
        if new_text != text:
            totals['files'] += 1
            totals['zones'] += nz
            totals['clamped'] += nc
            totals['surfaces'] += ns
            print(f'{rel}: {nz} zones moved ({nc} clamped to the image), {ns} surface sizes set')
            if do_apply:
                path.write_text(new_text, encoding='utf-8')
    unused = sorted(set(TRANS) - used)
    if unused:
        raise SystemExit(f'transformations not used: {unused}')
    print(f"{totals['files']} files, {totals['zones']} zones ({totals['clamped']} clamped), "
          f"{totals['surfaces']} surfaces" + ('' if do_apply else ' (dry run)'))


if __name__ == '__main__':
    main()
