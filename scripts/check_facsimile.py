#!/usr/bin/env python3
"""Inventory and check the facsimile links of Probstücke Digital.

The encodings link the transcriptions to page images of the two prints in the
Bayerische Staatsbibliothek (BSB), served by its IIIF APIs:

    1719  Exemplarische Organisten-Probe  Mus.th. 977 a  bsb10527431
    1731  Grosse General-Baß-Schule       Mus.th. 978 a  bsb10598495

A <surface> stands for one page image. Its <graphic> names the IIIF canvas
(@target in MEI, @url in TEI: .../iiif/presentation/v2/<bsb-id>/canvas/<n>);
its <zone>s are pixel rectangles on that image. The website shows the zones
of a staff (staff/@facs in MEI) by requesting

    https://api.digitale-sammlungen.de/iiif/image/v2/<bsb-id>_<n:05d>/<ulx>,<uly>,<w>,<h>/pct:50/0/color.jpg

so canvas <n> must show the right page, and the zone coordinates must be
pixel coordinates of the image as BSB serves it today (its info.json).

The script

  1. lists every surface and zone together with the elements that point to
     them (--inventory FILE writes the list as tab-separated values);
  2. checks offline that
       - every @facs pointer names a <zone> or <surface> of the same file;
       - every graphic names a canvas of one of the two prints, in the
         print the MEI <facsimile decls> gives, and the surface's xml:id
         (facs-p<n>) and, in TEI, its @n (page) agree with it;
       - the canvas is a page of the file's Prob-Stück in that print and not
         a second scan of a page (tables PAGES, DUPLICATES and PIECES below,
         read from the scans), and a pb/@n names the page its @facs shows;
       - every zone has four coordinates and a positive area, lies inside its
         surface and is pointed to; a staff or measure does not name the same
         zone twice;
       - the stored size of a surface (@lrx/@lry) equals that of its graphic;
       - the staff zones of an MEI file follow the order of the measures (left
         to right within a system, top to bottom on a page, page after page),
         a staff has at most one zone per system (zone-split), no two measures
         share a zone (zone-shared), and where the staffs of a file have
         zones every staff with notes or rests has one (a warning,
         staff-no-zone),
         and the zones of a TEI text follow the order of the text (a
         warning only: music examples may stand beside a paragraph);
  3. with --online, fetches info.json for every canvas used (cached in
     --cache) and checks that the stored size of each surface is the size of
     the image BSB serves, so that zones lie inside it;
  4. with --images, also fetches each page image that has MEI staff zones
     (once, --image-width pixels wide) and checks that every staff zone frames
     a five-line staff; with --sheets DIR it writes contact sheets of all MEI
     staff crops, labelled with file, measure, print and canvas, to DIR.

Requests to BSB are cached and at least --delay seconds apart.

Problems listed in scripts/check_facsimile.allow (one per line, "<path>:
<code> <key>", the key as printed in brackets) are reported as allowed; every
entry should be explained by a comment there. Entries that match nothing are
reported as stale.

Usage:
    python3 scripts/check_facsimile.py [--root ENCODINGS_DIR] [--inventory FILE]
        [--online] [--images] [--sheets DIR] [--cache DIR] [--delay SECONDS]

Exit status: 0 if there are no errors (warnings and allowed problems do not
count) and no stale allowlist entries, 1 otherwise, 2 on usage errors.
"""

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

REPO = Path(__file__).resolve().parent.parent
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'
PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True)

PRINTS = {'bsb10527431': '1719', 'bsb10598495': '1731'}
DECLS = {'#firstEdition': '1719', '#secondEdition': '1731'}
CANVAS_URL = re.compile(r'^https://api\.digitale-sammlungen\.de/iiif/presentation/v2/(bsb\d{8})/canvas/(\d+)$')
IMAGE_API = 'https://api.digitale-sammlungen.de/iiif/image/v2'

# Printed pages and canvases, read from the page numbers and headings on the
# scans (October 2026): (first page, last page, first canvas). Pages 101 (1719)
# is the unnumbered half-title "Matthesons Organisten-Probe"; in the 1719
# print pp. 138-139 are misprinted 136-137 (canvases 312-313).
PAGES = {
    '1719': [(96, 100, 270), (101, 101, 275), (102, 149, 276), (150, 163, 360),
             (164, 175, 382), (176, 227, 396), (228, 247, 450)],
    '1731': [(260, 484, 322)],
}
# The 1719 copy was scanned with some pages twice; these second scans
# (canvas: page) are not used.
DUPLICATES = {
    '1719': {**dict(zip(range(324, 336), range(134, 146))),
             **dict(zip(range(336, 354), range(128, 146))),
             **dict(zip(range(354, 360), range(144, 150))),
             **dict(zip(range(374, 382), range(156, 164))),
             394: 174, 395: 175, 448: 226, 449: 227},
    '1731': {},
}
# Canvases of each Prob-Stück (score, commentary, arias): first and last.
PIECES = {
    '1719': {1: (276, 281), 2: (282, 289), 3: (290, 293), 4: (294, 299), 5: (300, 303), 6: (304, 307),
             7: (308, 311), 8: (312, 317), 9: (318, 323), 10: (360, 367), 11: (368, 373), 12: (382, 385),
             13: (386, 391), 14: (392, 397), 15: (398, 405), 16: (406, 413), 17: (414, 418), 18: (419, 423),
             19: (424, 427), 20: (428, 434), 21: (435, 439), 22: (440, 445), 23: (446, 451), 24: (452, 470)},
    '1731': {1: (364, 369), 2: (370, 377), 3: (378, 381), 4: (382, 387), 5: (388, 391), 6: (392, 397),
             7: (398, 401), 8: (402, 407), 9: (408, 413), 10: (414, 421), 11: (422, 427), 12: (428, 433),
             13: (434, 439), 14: (440, 443), 15: (444, 453), 16: (454, 461), 17: (462, 466), 18: (467, 471),
             19: (472, 475), 20: (476, 482), 21: (483, 487), 22: (488, 491), 23: (492, 495), 24: (496, 526)},
}


def page_to_canvas(print_, page):
    for first_page, last_page, first_canvas in PAGES.get(print_, ()):
        if first_page <= page <= last_page:
            return first_canvas + page - first_page
    return None


def canvas_to_page(print_, canvas):
    if canvas in DUPLICATES.get(print_, {}):
        return DUPLICATES[print_][canvas]
    for first_page, last_page, first_canvas in PAGES.get(print_, ()):
        if first_canvas <= canvas <= first_canvas + last_page - first_page:
            return first_page + canvas - first_canvas
    return None


def natural(text):
    return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', str(text))]


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

@dataclass
class Ref:
    """An element whose @facs points to a zone or surface."""
    element: str        # local name: staff, measure, pb, p, notatedMusic, ...
    line: int
    xml_id: str
    context: str        # e.g. 'measure 12 staff 2', 'pb n=302 source=#secondEdition'
    tokens: list


@dataclass
class Surface:
    path: str
    line: int
    xml_id: str
    n: str              # surface/@n
    url: str
    bsb: str            # BSB identifier or ''
    canvas: int         # canvas number or 0
    print: str          # '1719', '1731' or ''
    decls: str          # MEI facsimile/@decls ('' in TEI)
    size: tuple         # (lrx, lry) of the surface
    graphic_size: tuple  # (width, height) of the graphic, without 'px'
    zones: list = field(default_factory=list)
    refs: list = field(default_factory=list)


@dataclass
class Zone:
    path: str
    line: int
    xml_id: str
    coords: dict        # ulx, uly, lrx, lry as ints (missing or malformed ones are absent)
    surface: Surface
    refs: list = field(default_factory=list)

    def box(self):
        c = self.coords
        if all(k in c for k in ('ulx', 'uly', 'lrx', 'lry')):
            return c['ulx'], c['uly'], c['lrx'], c['lry']
        return None


@dataclass
class Document:
    path: str           # relative to the repository, e.g. encodings/1/mattheson/score.xml
    piece: int          # the Prob-Stück (directory number), 0 elsewhere
    kind: str           # 'mei' or 'tei'
    surfaces: list
    zones: dict         # xml:id -> Zone
    refs: list          # all Refs in document order
    pointers: list      # (Ref, token, target or None)
    unlinked: list = field(default_factory=list)   # MEI staffs with notes or rests but no @facs: (line, context, staff n)


def local(el):
    return etree.QName(el).localname


def to_int(value):
    m = re.fullmatch(r'\s*(-?\d+)(?:px)?\s*', value or '')
    return int(m.group(1)) if m else None


def describe(el):
    name = local(el)
    if name in ('staff', 'measure'):
        measure = el if name == 'measure' else next(el.iterancestors('{*}measure'), None)
        text = 'measure ?' if measure is None else f'measure {measure.get("n") or "-"}'
        if measure is not None and measure.get('label') and measure.get('label') != measure.get('n'):
            text += f' (label {measure.get("label")})'
        return text + (f' staff {el.get("n")}' if name == 'staff' else '')
    if name == 'pb':
        return f'pb n={el.get("n")}' + (f' source={el.get("source")}' if el.get('source') else '')
    return f'{name} {el.get(XML_ID) or ""}'.strip()


def read_document(path, base):
    root = etree.parse(str(path), PARSER).getroot()
    rel = path.relative_to(base).as_posix()
    m = re.match(r'encodings/(\d+)/', rel)
    doc = Document(rel, int(m.group(1)) if m else 0,
                   'mei' if root.tag.startswith('{http://www.music-encoding.org/ns/mei}') else 'tei',
                   [], {}, [], [])
    targets = {}
    for facsimile in root.iter('{*}facsimile'):
        for s in facsimile.iter('{*}surface'):
            graphic = next(s.iter('{*}graphic'), None)
            url, gsize = '', (None, None)
            if graphic is not None:
                url = graphic.get('target') or graphic.get('url') or ''
                gsize = (to_int(graphic.get('width')), to_int(graphic.get('height')))
            cm = CANVAS_URL.match(url)
            bsb, canvas = (cm.group(1), int(cm.group(2))) if cm else ('', 0)
            surface = Surface(rel, s.sourceline, s.get(XML_ID) or '', s.get('n') or '', url, bsb, canvas,
                              PRINTS.get(bsb, ''), facsimile.get('decls') or '',
                              (to_int(s.get('lrx')), to_int(s.get('lry'))), gsize)
            doc.surfaces.append(surface)
            if surface.xml_id:
                targets[surface.xml_id] = surface
            for z in s.iter('{*}zone'):
                coords = {k: to_int(z.get(k)) for k in ('ulx', 'uly', 'lrx', 'lry') if to_int(z.get(k)) is not None}
                zone = Zone(rel, z.sourceline, z.get(XML_ID) or '', coords, surface)
                surface.zones.append(zone)
                if zone.xml_id:
                    doc.zones[zone.xml_id] = zone
                    targets[zone.xml_id] = zone
    if doc.kind == 'mei':
        for staff in root.iter('{*}staff'):
            if staff.get('facs') is None and any(local(e) in ('note', 'rest', 'chord', 'mRest')
                                                 for e in staff.iter() if isinstance(e.tag, str)):
                doc.unlinked.append((staff.sourceline, describe(staff), staff.get('n') or '-'))
    for el in root.iter():
        if not isinstance(el.tag, str) or el.get('facs') is None:
            continue
        ref = Ref(local(el), el.sourceline, el.get(XML_ID) or '', describe(el), el.get('facs').split())
        doc.refs.append(ref)
        for token in ref.tokens:
            target = targets.get(token[1:]) if token.startswith('#') else None
            doc.pointers.append((ref, token, target))
            if target is not None:
                target.refs.append(ref)
    return doc


def read_all(root_dir):
    base = root_dir.parent
    documents = []
    for path in sorted(root_dir.rglob('*.xml'), key=lambda p: natural(p.as_posix())):
        text = path.read_text(encoding='utf-8')
        if '<facsimile' in text or ' facs=' in text:
            documents.append(read_document(path, base))
    return documents


def write_inventory(documents, out):
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh, delimiter='\t', lineterminator='\n')
        w.writerow(['file', 'line', 'type', 'print', 'canvas', 'page', 'surface', 'zone',
                    'ulx', 'uly', 'lrx', 'lry', 'stored_width', 'stored_height', 'referenced_by'])
        for doc in documents:
            for s in doc.surfaces:
                page = canvas_to_page(s.print, s.canvas) if s.canvas else ''
                refs = '; '.join(f'{r.context} (line {r.line})' for r in s.refs)
                w.writerow([doc.path, s.line, 'surface', s.print, s.canvas or s.url, page, s.xml_id, '',
                            '', '', '', '', s.size[0], s.size[1], refs])
                for z in s.zones:
                    refs = '; '.join(f'{r.context} (line {r.line})' for r in z.refs)
                    c = z.coords
                    w.writerow([doc.path, z.line, 'zone', s.print, s.canvas or s.url, page, s.xml_id, z.xml_id,
                                c.get('ulx', ''), c.get('uly', ''), c.get('lrx', ''), c.get('lry', ''),
                                '', '', refs])


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

class Report:
    def __init__(self, allow=None):
        self.items = []         # (severity, path, line, code, key, message)
        self.allow = allow or {}
        self.used = set()

    def add(self, severity, path, line, code, key, message):
        if (path, code, key) in self.allow:
            self.used.add((path, code, key))
            severity = 'allowed'
        self.items.append((severity, path, line, code, key, message))

    def error(self, path, line, code, key, message):
        self.add('error', path, line, code, key, message)

    def warn(self, path, line, code, key, message):
        self.add('warning', path, line, code, key, message)

    def count(self, severity):
        return sum(1 for item in self.items if item[0] == severity)

    def stale(self):
        return sorted((n, k) for k, n in self.allow.items() if k not in self.used)

    def print(self, out=sys.stdout, show_allowed=False):
        by_file = defaultdict(list)
        for item in self.items:
            if item[0] != 'allowed' or show_allowed:
                by_file[item[1]].append(item)
        for path in sorted(by_file, key=natural):
            print(path, file=out)
            for severity, _, line, code, key, message in sorted(by_file[path], key=lambda i: (i[2] or 0, i[3])):
                print(f'  line {line or "-":<5} {severity:<7} {code:<14} {message} [{key}]', file=out)
            print(file=out)


def read_allowlist(path):
    entries = {}
    if not path.is_file():
        return entries
    for number, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        file_part, sep, rest = line.partition(': ')
        code, _, key = rest.strip().partition(' ')
        if not sep or not code or not key:
            raise SystemExit(f'{path.name}:{number}: expected "<path>: <code> <key>", got {raw!r}')
        entries[(file_part.strip(), code, key.strip())] = number
    return entries


# ---------------------------------------------------------------------------
# Offline checks
# ---------------------------------------------------------------------------

def check_offline(documents, report):
    for doc in documents:
        check_pointers(doc, report)
        check_surfaces(doc, report)
        check_pages(doc, report)
        if doc.kind == 'mei':
            check_staff_order(doc, report)
            check_staff_zones(doc, report)
        else:
            check_text_order(doc, report)


def check_pointers(doc, report):
    for ref, token, target in doc.pointers:
        if target is None:
            report.error(doc.path, ref.line, 'pointer', token,
                         f'{ref.context}: @facs token {token!r} names no zone or surface in this file')
    for ref in doc.refs:
        for token, n in Counter(ref.tokens).items():
            if n > 1:
                report.warn(doc.path, ref.line, 'pointer-repeat', token, f'{ref.context}: @facs names {token} {n} times')


def check_surfaces(doc, report):
    for s in doc.surfaces:
        name = s.xml_id or f'(line {s.line})'
        if not s.bsb:
            report.error(doc.path, s.line, 'graphic', name, f'surface {name}: graphic {s.url!r} is not a BSB IIIF canvas')
        elif not s.print:
            report.error(doc.path, s.line, 'graphic', name, f'surface {name}: unknown BSB identifier {s.bsb}')
        if s.decls in DECLS and s.print and DECLS[s.decls] != s.print:
            report.error(doc.path, s.line, 'print', name, f'surface {name}: canvas of the {s.print} print in <facsimile decls="{s.decls}">')
        m = re.fullmatch(r'facs-p(\d+)', s.xml_id)
        if m and s.canvas and int(m.group(1)) != s.canvas:
            report.warn(doc.path, s.line, 'surface-id', name, f'surface {name} shows canvas {s.canvas}')
        if doc.kind == 'tei' and s.n.isdigit() and s.canvas and canvas_to_page(s.print, s.canvas) != int(s.n):
            report.error(doc.path, s.line, 'surface-n', name,
                         f'surface {name} n="{s.n}" shows canvas {s.canvas}, p. {canvas_to_page(s.print, s.canvas)}')
        gw, gh = s.graphic_size
        if None in s.size or (gw is not None and (gw, gh) not in (s.size, (s.size[0] + 1, s.size[1] + 1))):
            report.warn(doc.path, s.line, 'surface-size', name, f'surface {name}: lrx/lry {s.size} but graphic {gw}x{gh}')
        for z in s.zones:
            zname = z.xml_id or f'zone (line {z.line})'
            box = z.box()
            if box is None:
                missing = [k for k in ('ulx', 'uly', 'lrx', 'lry') if k not in z.coords]
                report.error(doc.path, z.line, 'zone-coords', zname, f'{zname}: no @{", @".join(missing)}')
                continue
            ulx, uly, lrx, lry = box
            if lrx <= ulx or lry <= uly:
                report.error(doc.path, z.line, 'zone-coords', zname, f'{zname}: empty or inverted rectangle {box}')
            elif None not in s.size and (ulx < 0 or uly < 0 or lrx > s.size[0] + 1 or lry > s.size[1] + 1):
                report.error(doc.path, z.line, 'zone-surface', zname, f'{zname} {box} exceeds its surface (0, 0, {s.size[0]}, {s.size[1]})')
            if not z.refs and z.xml_id:
                report.warn(doc.path, z.line, 'zone-unused', zname, f'{zname} is not pointed to')


def check_pages(doc, report):
    for s in doc.surfaces:
        if not s.print or not s.canvas:
            continue
        name = s.xml_id or f'(line {s.line})'
        if s.canvas in DUPLICATES[s.print]:
            report.error(doc.path, s.line, 'canvas-duplicate', name,
                         f'surface {name}: canvas {s.canvas} is a second scan of p. {DUPLICATES[s.print][s.canvas]}; '
                         f'use canvas {page_to_canvas(s.print, DUPLICATES[s.print][s.canvas])}')
        span = PIECES[s.print].get(doc.piece)
        if span and not span[0] <= s.canvas <= span[1]:
            used = s.zones or s.refs
            (report.error if used else report.warn)(
                doc.path, s.line, 'canvas-piece', name,
                f'surface {name}: canvas {s.canvas} (p. {canvas_to_page(s.print, s.canvas)}) is not a page of '
                f'No. {doc.piece} in the {s.print} print (canvases {span[0]}-{span[1]})'
                + ('' if used else '; the surface is not used'))
    by_id = {s.xml_id: s for s in doc.surfaces if s.xml_id}
    for ref in doc.refs:
        if ref.element != 'pb':
            continue
        m = re.match(r'pb n=(\S+)(?: source=(\S+))?', ref.context)
        n, source = m.group(1), m.group(2)
        for token in ref.tokens:
            s = by_id.get(token[1:])
            if s is None or not s.print:
                continue
            if source in DECLS and DECLS[source] != s.print:
                report.error(doc.path, ref.line, 'pb-source', f'n={n} {token}',
                             f'{ref.context} points to {token}, a page of the {s.print} print')
            if not n.isdigit():
                continue
            if canvas_to_page(s.print, s.canvas) != int(n):
                report.error(doc.path, ref.line, 'pb-canvas', f'n={n} {token}',
                             f'{ref.context} points to {token}, canvas {s.canvas} (p. {canvas_to_page(s.print, s.canvas)})'
                             + (f'; p. {n} is canvas {page_to_canvas(s.print, int(n))}' if page_to_canvas(s.print, int(n)) else ''))


def overlap(a0, a1, b0, b1):
    return max(0, min(a1, b1) - max(a0, b0))


def check_staff_order(doc, report):
    """Staff zones must follow the measures: left to right, top to bottom, page after page."""
    sequences = defaultdict(list)   # (print, staff n) -> [(Ref, Zone)]
    for ref in doc.refs:
        if ref.element not in ('staff', 'measure'):
            continue
        staff_n = re.search(r'staff (\S+)$', ref.context)
        for token in ref.tokens:
            zone = doc.zones.get(token[1:])
            if zone is None or zone.box() is None:
                continue
            seq = sequences[(zone.surface.print, staff_n.group(1) if staff_n else '-')]
            if seq and seq[-1][1] is zone:
                continue
            seq.append((ref, zone))
    surface_order = {id(s): i for i, s in enumerate(doc.surfaces)}
    for seq in sequences.values():
        for (r1, z1), (r2, z2) in zip(seq, seq[1:]):
            s1, s2 = z1.surface, z2.surface
            where = f'{r2.context}: {z2.xml_id} after {z1.xml_id} ({r1.context})'
            if s1 is not s2:
                if surface_order[id(s2)] < surface_order[id(s1)] or (s1.canvas and s2.canvas and s2.canvas != s1.canvas + 1):
                    report.error(doc.path, z2.line, 'zone-order', z2.xml_id, f'{where}: canvas {s1.canvas} -> {s2.canvas}')
                continue
            a, b = z1.box(), z2.box()
            if a[2] <= a[0] or b[2] <= b[0] or a[3] <= a[1] or b[3] <= b[1]:
                continue
            h = min(a[3] - a[1], b[3] - b[1])
            if overlap(a[1], a[3], b[1], b[3]) >= 0.5 * h:      # same system
                if (b[0] + b[2]) / 2 <= (a[0] + a[2]) / 2:
                    report.error(doc.path, z2.line, 'zone-order', z2.xml_id, f'{where}: same system but not further right')
            elif (b[1] + b[3]) / 2 > (a[1] + a[3]) / 2:          # next system
                if b[0] > (a[0] + a[2]) / 2:
                    report.warn(doc.path, z2.line, 'zone-order', z2.xml_id, f'{where}: next system but does not start further left')
            else:
                report.error(doc.path, z2.line, 'zone-order', z2.xml_id, f'{where}: above the previous zone on the same page')


def check_staff_zones(doc, report):
    """A staff may continue on the next system, but not have two zones in one system; two measures
    do not share a zone; and where the staffs of a file have zones, every staff with notes or rests
    should have one."""
    linked_staffs = set()
    users = defaultdict(list)
    for ref in doc.refs:
        if ref.element not in ('staff', 'measure'):
            continue
        staff_n = re.search(r'staff (\S+)$', ref.context)
        zones = [doc.zones.get(t[1:]) for t in dict.fromkeys(ref.tokens)]
        zones = [z for z in zones if z is not None and z.box() is not None]
        if zones:
            linked_staffs.add(staff_n.group(1) if staff_n else '-')
        for z in zones:
            users[z.xml_id].append(ref)
        for i, a in enumerate(zones):
            for b in zones[i + 1:]:
                if a.surface is not b.surface:
                    continue
                ba, bb = a.box(), b.box()
                h = min(ba[3] - ba[1], bb[3] - bb[1])
                if h > 0 and overlap(ba[1], ba[3], bb[1], bb[3]) >= 0.5 * h:
                    report.error(doc.path, ref.line, 'zone-split', b.xml_id,
                                 f'{ref.context}: {a.xml_id} and {b.xml_id} lie in the same system; '
                                 f'one of them shows another measure')
    for zone_id, refs in users.items():
        for ref in refs[1:]:
            if ref.context != refs[0].context:
                report.error(doc.path, ref.line, 'zone-shared', zone_id,
                             f'{ref.context} names {zone_id}, the zone of {refs[0].context}')
    for line, context, staff_n in doc.unlinked:
        if staff_n in linked_staffs:
            report.warn(doc.path, line, 'staff-no-zone', context, f'{context} has notes but no zone')


def check_text_order(doc, report):
    """Zones of a TEI text (paragraphs, music examples) follow the text: page after page, top to bottom."""
    previous = None
    surface_order = {id(s): i for i, s in enumerate(doc.surfaces)}
    for ref in doc.refs:
        if ref.element == 'pb':
            continue
        for token in ref.tokens:
            zone = doc.zones.get(token[1:])
            if zone is None or zone.box() is None:
                continue
            if previous is not None and previous is not zone:
                s1, s2 = previous.surface, zone.surface
                if surface_order[id(s2)] < surface_order[id(s1)]:
                    report.warn(doc.path, ref.line, 'zone-order', zone.xml_id,
                                f'{ref.context}: {zone.xml_id} on canvas {s2.canvas}, before the canvas {s1.canvas} of {previous.xml_id}')
                elif s1 is s2 and zone.box()[1] + 20 < previous.box()[1]:
                    report.warn(doc.path, ref.line, 'zone-order', zone.xml_id,
                                f'{ref.context}: {zone.xml_id} lies above {previous.xml_id} on the same page')
            previous = zone


# ---------------------------------------------------------------------------
# Online checks
# ---------------------------------------------------------------------------

class BSB:
    """Cached, rate-limited access to the BSB IIIF image API."""

    def __init__(self, cache, delay):
        self.cache = Path(cache)
        self.delay = delay
        self.last = 0.0

    def fetch(self, url, dest):
        if dest.exists() and dest.stat().st_size > 0:
            return dest.read_bytes()
        for attempt in range(4):
            wait = self.last + self.delay - time.time()
            if wait > 0:
                time.sleep(wait)
            self.last = time.time()
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    data = response.read()
                break
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt == 3:
                    raise RuntimeError(f'{url}: {exc}') from exc
                time.sleep(2 * (attempt + 1))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return data

    def size(self, bsb, canvas):
        info = json.loads(self.fetch(f'{IMAGE_API}/{bsb}_{canvas:05d}/info.json',
                                     self.cache / 'info' / f'{bsb}_{canvas:05d}.json'))
        return info['width'], info['height']

    def image(self, bsb, canvas, width):
        from PIL import Image
        dest = self.cache / 'images' / f'{bsb}_{canvas:05d}_w{width}.jpg'
        self.fetch(f'{IMAGE_API}/{bsb}_{canvas:05d}/full/{width},/0/default.jpg', dest)
        return Image.open(dest)


def check_online(documents, report, bsb):
    sizes = {}
    for doc in documents:
        for s in doc.surfaces:
            if not s.bsb:
                continue
            key = (s.bsb, s.canvas)
            if key not in sizes:
                sizes[key] = bsb.size(*key)
            width, height = sizes[key]
            name = s.xml_id or f'(line {s.line})'
            if s.graphic_size != (width, height) or s.size not in ((width, height), (width - 1, height - 1)):
                report.error(doc.path, s.line, 'size', name,
                             f'surface {name} (canvas {s.canvas}): stored {s.size[0]}x{s.size[1]}, graphic '
                             f'{s.graphic_size[0]}x{s.graphic_size[1]}; BSB serves {width}x{height}')
            for z in s.zones:
                box = z.box()
                if box and (box[0] < 0 or box[1] < 0 or box[2] > width or box[3] > height):
                    report.error(doc.path, z.line, 'zone-image', z.xml_id,
                                 f'{z.xml_id} {box} exceeds the image of canvas {s.canvas} ({width}x{height})')
    return sizes


# ---------------------------------------------------------------------------
# Image checks
# ---------------------------------------------------------------------------

def otsu(gray):
    import numpy as np
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    total, cum, cum_mean = hist.sum(), np.cumsum(hist), np.cumsum(hist * np.arange(256))
    w0 = cum[:-1]
    w1 = total - w0
    with np.errstate(divide='ignore', invalid='ignore'):
        between = w0 * w1 * (cum_mean[:-1] / w0 - (cum_mean[-1] - cum_mean[:-1]) / w1) ** 2
    return int(np.nanargmax(between))


def line_pixels(dark, max_thick=6, min_len=5):
    """Dark pixels that belong to thin horizontal strokes (staff lines)."""
    import numpy as np
    h, w = dark.shape
    thin = np.zeros_like(dark)
    for x in range(w):
        col = np.concatenate([[False], dark[:, x], [False]]).astype(np.int8)
        d = np.diff(col)
        for a, b in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            if b - a <= max_thick:
                thin[a:b, x] = True
    out = np.zeros_like(dark)
    for y in range(h):
        row = np.concatenate([[False], thin[y], [False]]).astype(np.int8)
        d = np.diff(row)
        for a, b in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            if b - a >= min_len:
                out[y, a:b] = True
    return out


class PageImage:
    """A page reduced to --image-width, with its staff-line pixels."""

    def __init__(self, image, full_size):
        import numpy as np
        gray = np.asarray(image.convert('L'))
        self.image = image
        self.scale = image.width / full_size[0]
        self.lines = line_pixels(gray < otsu(gray))
        profile = self.lines[:, image.width // 5: 4 * image.width // 5].mean(axis=1)
        profile = profile - profile.mean()
        lags = range(4, 40)
        self.spacing = lags[int(np.argmax([np.dot(profile[:-k], profile[k:]) for k in lags]))]

    def staff_in(self, box):
        """Best five-line comb in the zone: (response, centre y as a fraction of the zone height)."""
        import numpy as np
        x0, y0, x1, y1 = (round(v * self.scale) for v in box)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(self.lines.shape[1], x1), min(self.lines.shape[0], y1)
        if x1 - x0 < 10 or y1 - y0 < 5 * self.spacing:
            return 0.0, None
        profile = self.lines[y0:y1, x0:x1].mean(axis=1)
        smooth = np.maximum(profile, np.maximum(np.roll(profile, 1), np.roll(profile, -1)))
        best = (0.0, None)
        for sp in (self.spacing - 1, self.spacing, self.spacing + 1):
            n = len(smooth) - 4 * sp
            if n <= 0:
                continue
            comb = sum(smooth[k * sp: k * sp + n] for k in range(5)) / 5
            y = int(np.argmax(comb))
            if comb[y] > best[0]:
                best = (float(comb[y]), (y + 2 * sp) / len(smooth))
        return best


def staff_zone_crops(documents, bsb, sizes, width):
    """Yield (doc, ref, zone, PageImage) for every MEI staff/measure zone on a BSB canvas."""
    pages = {}
    for doc in documents:
        if doc.kind != 'mei':
            continue
        for ref in doc.refs:
            if ref.element not in ('staff', 'measure'):
                continue
            for token in ref.tokens:
                zone = doc.zones.get(token[1:])
                box = zone.box() if zone is not None else None
                if box is None or box[2] <= box[0] or box[3] <= box[1] or not zone.surface.bsb:
                    continue   # reported as zone-coords
                key = (zone.surface.bsb, zone.surface.canvas)
                if key not in pages:
                    pages[key] = PageImage(bsb.image(*key, width), sizes[key])
                yield doc, ref, zone, pages[key]


def check_images(documents, report, bsb, sizes, width, sheets_dir=None, min_response=0.3):
    sheets = Sheets(sheets_dir) if sheets_dir else None
    checked = 0
    for doc, ref, zone, page in staff_zone_crops(documents, bsb, sizes, width):
        checked += 1
        response, centre = page.staff_in(zone.box())
        ok = response >= min_response and centre is not None and 0.15 <= centre <= 0.85
        if not ok:
            detail = 'no five-line staff' if response < min_response else f'the staff is at {centre:.0%} of its height'
            report.warn(doc.path, zone.line, 'zone-staff', zone.xml_id,
                        f'{ref.context}: {detail} in {zone.xml_id} (canvas {zone.surface.canvas})')
        if sheets is not None:
            f = page.scale
            x0, y0, x1, y1 = zone.box()
            box = (max(0, round(x0 * f)), max(0, round(y0 * f)),
                   min(page.image.width, round(x1 * f)), min(page.image.height, round(y1 * f)))
            crop = page.image.crop(box) if box[2] > box[0] and box[3] > box[1] else None
            label = f'{doc.path.split("/", 1)[1]} | {ref.context} | {zone.surface.print} c{zone.surface.canvas}'
            sheets.add(crop, label + ('' if ok else ' | CHECK'))
    if sheets is not None:
        sheets.close()
    return checked


class Sheets:
    """Contact sheets of labelled crops, 2 columns x 8 rows."""

    def __init__(self, directory, per_sheet=16, cell=(560, 200)):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.per_sheet, self.cell = per_sheet, cell
        self.items, self.count = [], 0

    def add(self, crop, label):
        self.items.append((crop, label))
        if len(self.items) == self.per_sheet:
            self.flush()

    def flush(self):
        from PIL import Image, ImageDraw
        if not self.items:
            return
        cols = 2
        rows = (len(self.items) + cols - 1) // cols
        cw, ch = self.cell
        sheet = Image.new('RGB', (cols * cw, rows * (ch + 18)), 'white')
        draw = ImageDraw.Draw(sheet)
        for i, (crop, label) in enumerate(self.items):
            x, y = (i % cols) * cw, (i // cols) * (ch + 18)
            draw.text((x + 4, y + 3), label[:90], fill='black')
            if crop is not None and crop.width and crop.height:
                c = crop.copy()
                c.thumbnail((cw - 8, ch - 4))
                sheet.paste(c, (x + 4, y + 17))
            draw.rectangle([x, y, x + cw - 1, y + ch + 17], outline='grey')
        self.count += 1
        sheet.save(self.directory / f'sheet_{self.count:03d}.jpg', quality=85)
        self.items = []

    def close(self):
        self.flush()


# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--root', type=Path, default=REPO / 'encodings', help='encodings directory (default: %(default)s)')
    parser.add_argument('--allow', type=Path, default=REPO / 'scripts' / 'check_facsimile.allow',
                        help='allowlist file (default: %(default)s)')
    parser.add_argument('--inventory', type=Path, help='write the inventory of surfaces and zones to this TSV file')
    parser.add_argument('--online', action='store_true', help='compare with the image sizes BSB serves')
    parser.add_argument('--images', action='store_true', help='check that MEI staff zones frame a staff (implies --online)')
    parser.add_argument('--sheets', type=Path, help='write contact sheets of the MEI staff crops to this directory (implies --images)')
    parser.add_argument('--image-width', type=int, default=1000, help='width of the page images fetched for --images (default: %(default)s)')
    parser.add_argument('--cache', type=Path, default=Path('.facsimile-cache'), help='cache for BSB responses (default: %(default)s)')
    parser.add_argument('--delay', type=float, default=0.4, help='seconds between requests to BSB (default: %(default)s)')
    parser.add_argument('--show-allowed', action='store_true', help='also list allowed problems')
    args = parser.parse_args(argv)
    args.images = args.images or bool(args.sheets)
    args.online = args.online or args.images

    root_dir = args.root.resolve()
    if not root_dir.is_dir():
        parser.error(f'{args.root} is not a directory')
    documents = read_all(root_dir)
    if args.inventory:
        write_inventory(documents, args.inventory)

    report = Report(read_allowlist(args.allow))
    check_offline(documents, report)
    checked_images = 0
    if args.online:
        bsb = BSB(args.cache, args.delay)
        sizes = check_online(documents, report, bsb)
        if args.images:
            checked_images = check_images(documents, report, bsb, sizes, args.image_width, args.sheets)

    report.print(show_allowed=args.show_allowed)
    stale = report.stale() if args.online else [s for s in report.stale() if s[1][1] not in ('size', 'zone-image', 'zone-staff')]
    for number, (path, code, key) in stale:
        print(f'{args.allow.name}:{number}: stale entry "{path}: {code} {key}" matches no problem; remove it')
    surfaces = sum(len(d.surfaces) for d in documents)
    zones = sum(len(s.zones) for d in documents for s in d.surfaces)
    staffs = sum(1 for d in documents for r in d.refs if r.element in ('staff', 'measure'))
    print(f'{len(documents)} files with facsimile data: {surfaces} surfaces, {zones} zones, {staffs} MEI staffs/measures '
          f'with @facs' + (f', {checked_images} staff zones checked on the images' if args.images else '')
          + f'; {report.count("error")} error(s), {report.count("warning")} warning(s), {report.count("allowed")} allowed'
          + (f', {len(stale)} stale allowlist entr{"y" if len(stale) == 1 else "ies"}' if stale else '') + '.')
    return 1 if report.count('error') or stale else 0


if __name__ == '__main__':
    sys.exit(main())
