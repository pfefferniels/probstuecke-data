#!/usr/bin/env python3
"""One-off repair: zones for measures of the 1731 scores that had none.

In five scores a measure had no zone because the zone of its neighbour also
covered it (the encoder drew one box over two bars) or because no box was
drawn at all. The missing zones are made from the current page images
(after rescale_zones.py): a two-bar zone is split at the barline between the
bars, and a new zone takes the height of its neighbour. The barline
positions (x, full-resolution pixels of the current image) were measured on
the image as the columns in which the staff is dark from the top to the
bottom line, and checked visually; each zone gets 15 px on either side of
its barlines, like the existing zones.

  No. 2, p. 311, last line: m. 36 | m. 37 (d4 f3 g3 b3, a3 a2, d2) at
      x = 1382-1391; m. 37 ends with the final double bar.
  No. 6, p. 331, last line: m. 39 | m. 40 (d2, two rests) at x = 1535-1543.
  No. 8, p. 340, line 4: m. 15 (whole-bar rest) lies between the barlines
      at x = 1378-1386 and 1512-1519.
  No. 11, p. 360, line 2: m. 4 | m. 5 (six eighths each) at x = 1555-1561.
  No. 15, p. 382, line 3: mm. 14 and 15 (d3 and c3, each with a rest) are
      printed without a barline between them, and the zone given to m. 15
      shows m. 16 (b2 and a rest, x = 697-794). That zone goes to m. 16; the
      zone of m. 14 is split in the gap between the rest of m. 14 and the
      note of m. 15 (x = 594-596).
  No. 17, p. 400, line 5: m. 18 (f3 d4 b2 | e3 c4 a2, figures 6 6) was
      missing from the encoding when the zones were drawn; it was added in
      May 2020 (2b6aa63) as a copy of m. 17, pointer included, so it showed
      m. 17. Its zone lies between the barlines at x = 820-824 and
      1106-1111, with the height of the zone of m. 17. The staff has no
      xml:id; the zone is named after the measure.

Usage: python3 scripts/facsimile_repair/split_zones.py [--apply]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xmledit as X  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
MARGIN = 15

# file -> list of operations, applied in order:
#   ('rename', box, new id)                      give the zone with these coordinates a new xml:id
#   ('split', zone, x, new zone)                 zone keeps the part left of x (+MARGIN), new zone gets
#                                                the part from x (-MARGIN) to the zone's right edge
#   ('new', after zone, (ulx, uly, lrx, lry), new zone)   a new zone, written after the line of 'after zone'
#   ('facs', staff, old @facs or None, new @facs)  staff/@facs; the staff by its xml:id or as 'm<n>/s<n>'
FIXES = {
    'encodings/2/mattheson/score.xml': [
        ('split', 'facsZone-m-1725', 1386, 'facsZone-m-1767'),
        ('facs', 'm-1767', None, '#facsZone-m-1767'),
    ],
    'encodings/6/mattheson/score.xml': [
        ('split', 'facsZone-m-1217', 1539, 'facsZone-m-1250'),
        ('facs', 'm-1250', None, '#facsZone-m-1250'),
    ],
    'encodings/8/mattheson/score.xml': [
        ('new', 'facsZone-m-289', (1382 - MARGIN, 1574, 1515 + MARGIN, 1810), 'facsZone-m-298'),
        ('facs', 'm-298', None, '#facsZone-m-298'),
    ],
    'encodings/11/mattheson/score.xml': [
        ('split', 'facsZone-staff-0000000691022510', 1558, 'facsZone-staff-0000000435614713'),
        ('facs', 'staff-0000000435614713', None, '#facsZone-staff-0000000435614713'),
    ],
    'encodings/15/mattheson/score.xml': [
        ('rename', (671, 915, 811, 1192), 'facsZone-staff-0000001897837758'),
        ('split', 'facsZone-staff-0000001233821212', 595, 'facsZone-staff-0000001976983187'),
        ('facs', 'staff-0000001897837758', None, '#facsZone-staff-0000001897837758'),
    ],
    'encodings/17/mattheson/score.xml': [
        ('new', 'facsZone-staff-0000001440923572', (822 - MARGIN, 1603, 1108 + MARGIN, 1967), 'facsZone-m18-staff2'),
        ('facs', 'm18/s2', '#facsZone-staff-0000001440923572', '#facsZone-m18-staff2'),
    ],
}


def box_of(tag):
    return tuple(int(X.get_attr(tag, k)) for k in ('ulx', 'uly', 'lrx', 'lry'))


def has_id(text, zid):
    return re.search(r'<(?:\w+:)?zone\b[^<>]*\sxml:id="%s"' % re.escape(zid), text) is not None


def zone_line(text, span):
    a = text.rfind('\n', 0, span[0]) + 1
    b = text.index('\n', span[1]) + 1
    if text[a:span[0]].strip() or text[span[1]:b].strip():
        raise SystemExit(f'zone at {span} does not stand on a line of its own')
    return a, b


def with_box(tag, box, zid=None):
    for k, v in zip(('ulx', 'uly', 'lrx', 'lry'), box):
        tag = X.set_attr(tag, k, str(v))
    return X.set_attr(tag, 'xml:id', zid) if zid else tag


def insert_after(text, anchor_id, box, zid):
    span = X.tag_span(text, 'zone', 'xml:id', anchor_id)
    a, b = zone_line(text, span)
    line = text[a:b]
    tag = text[span[0]:span[1]]
    new_line = line.replace(tag, with_box(tag, box, zid))
    return text[:b] + new_line + text[b:]


def staff_span(text, locator):
    """Start tag of a staff, given by its xml:id or as 'm<measure n>/s<staff n>'."""
    m = re.fullmatch(r'm(\w+)/s(\d+)', locator)
    if not m:
        return X.tag_span(text, 'staff', 'xml:id', locator)
    measures = [h for h in re.finditer(r'<(?:\w+:)?measure\b[^<>]*>', text) if X.get_attr(h.group(0), 'n') == m.group(1)]
    if len(measures) != 1:
        raise SystemExit(f'expected one measure n="{m.group(1)}", found {len(measures)}')
    end = text.index('</measure>', measures[0].end())
    staffs = [h for h in re.finditer(r'<(?:\w+:)?staff\b[^<>]*>', text[:end]) if h.start() > measures[0].end()
              and X.get_attr(h.group(0), 'n') == m.group(2)]
    if len(staffs) != 1:
        raise SystemExit(f'measure {m.group(1)}: expected one staff n="{m.group(2)}", found {len(staffs)}')
    return staffs[0].span()


def main():
    do_apply = '--apply' in sys.argv
    for rel, ops in FIXES.items():
        path = REPO / rel
        text = path.read_text(encoding='utf-8')
        new = text
        log = []
        for op in ops:
            if op[0] == 'rename':
                _, box, zid = op
                hits = [m for m in re.finditer(r'<(?:\w+:)?zone\b[^<>]*>', new) if box_of(m.group(0)) == box]
                if len(hits) != 1:
                    raise SystemExit(f'{rel}: expected one zone {box}, found {len(hits)}')
                tag = hits[0].group(0)
                if X.get_attr(tag, 'xml:id') != zid:
                    if has_id(new, zid):
                        raise SystemExit(f'{rel}: {zid} exists')
                    log.append(f'zone {box}: {X.get_attr(tag, "xml:id")} -> {zid}')
                    new = X.replace_span(new, hits[0].span(), X.set_attr(tag, 'xml:id', zid))
            elif op[0] == 'split':
                _, zid, x, new_id = op
                span = X.tag_span(new, 'zone', 'xml:id', zid)
                tag = new[span[0]:span[1]]
                ulx, uly, lrx, lry = box_of(tag)
                left = (ulx, uly, x + MARGIN, lry)
                right = (x - MARGIN, uly, lrx, lry)
                if has_id(new, new_id):
                    done = box_of(new[slice(*X.tag_span(new, 'zone', 'xml:id', new_id))])
                    if (ulx, uly, lrx, lry)[2] != x + MARGIN or done[0] != x - MARGIN:
                        raise SystemExit(f'{rel}: {new_id} exists, but {zid} is not split at {x}')
                    continue
                if not ulx < x < lrx:
                    raise SystemExit(f'{rel}: {x} is not inside {zid} {box_of(tag)}')
                log.append(f'{zid} {box_of(tag)} -> {left}; new {new_id} {right}')
                new = X.replace_span(new, span, with_box(tag, left))
                new = insert_after(new, zid, right, new_id)
            elif op[0] == 'new':
                _, anchor, box, new_id = op
                if has_id(new, new_id):
                    if box_of(new[slice(*X.tag_span(new, 'zone', 'xml:id', new_id))]) != box:
                        raise SystemExit(f'{rel}: {new_id} exists with other coordinates')
                    continue
                log.append(f'new {new_id} {box}')
                new = insert_after(new, anchor, box, new_id)
            elif op[0] == 'facs':
                _, staff, old_value, value = op
                span = staff_span(new, staff)
                tag = new[span[0]:span[1]]
                current = X.get_attr(tag, 'facs')
                if current == value:
                    continue
                if current != old_value:
                    raise SystemExit(f'{rel}: staff {staff} has @facs {current!r}, expected {old_value!r}')
                log.append(f'staff {staff}: @facs {current} -> {value}')
                tag = X.add_attr(tag, 'facs', value, after='n') if current is None else X.set_attr(tag, 'facs', value)
                new = X.replace_span(new, span, tag)
        print(f'{rel}: ' + ('; '.join(log) if log else 'already done'))
        if do_apply and new != text:
            path.write_text(new, encoding='utf-8')
    print('applied.' if do_apply else 'dry run.')


if __name__ == '__main__':
    main()
