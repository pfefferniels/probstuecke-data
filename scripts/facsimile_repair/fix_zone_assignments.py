#!/usr/bin/env python3
"""One-off repair: attach misassigned zones of the 1731 scores to the right measures.

When the zones were drawn in 2019, some were attached to the wrong <staff>:
the second part of a measure that runs over a line break was given to the
measure before it, a measure that had no zone of its own got the zone
of the measure with the same rhythm a few bars later, or a zone was attached
twice. Each case below was established on the page image: the order of the
measures on the line, their number of notes and the figures above them (see
the comments). The zones keep their coordinates; the script

  - deletes zones that are exact duplicates of another zone,
  - renames zones after the staff they belong to (facsZone-<staff id>, with
    -2 for the second part on the next line), so that the ids say again which
    measure a zone shows,
  - sets staff/@facs of every measure concerned (adding it where a measure
    had no zone),
and lists, for every measure whose zones change, the zone boxes before and
after.

Usage: python3 scripts/facsimile_repair/fix_zone_assignments.py [--apply]
"""
import re
import sys
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xmledit as X  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'

# file -> list of operations, applied in order:
#   ('delete', zone, duplicate_of)   remove zone, which must have the coordinates of duplicate_of
#   ('rename', old, new)             zone/@xml:id old -> new
#   ('facs', staff, old, new)        staff/@facs of the staff with xml:id staff: old -> new
#                                    (old None: the staff has no @facs yet)
FIXES = {
    # No. 1, pp. 304-305: mm. 35 and 36 named the zone of their second part
    # two and three times.
    'encodings/1/mattheson/score.xml': [
        ('facs', 'm-1230', '#facsZone-m-1230 #facsZone-m-1230-2 #facsZone-m-1230-2',
         '#facsZone-m-1230 #facsZone-m-1230-2'),
        ('facs', 'm-1268', '#facsZone-m-1268 #facsZone-m-1268-2 #facsZone-m-1268-2 #facsZone-m-1268-2',
         '#facsZone-m-1268 #facsZone-m-1268-2'),
    ],
    # No. 2, p. 310: line 3 holds m. 22 and the first half of m. 23, line 4
    # the second half of m. 23 (32nds on b3, a3 and g3 with the figures
    # 7b, 7, 7, 7 natural). The zone of line 4 was given to m. 22.
    'encodings/2/mattheson/score.xml': [
        ('rename', 'facsZone-m-1025-2', 'facsZone-m-1058-2'),
        ('facs', 'm-1025', '#facsZone-m-1025 #facsZone-m-1025-2', '#facsZone-m-1025'),
        ('facs', 'm-1058', '#facsZone-m-1058', '#facsZone-m-1058 #facsZone-m-1058-2'),
    ],
    # No. 4, p. 322: m. 25 is complete at the end of line 2 (ending with two
    # quarters); the zone at the end of line 5 that was given to it as a
    # second part is m. 30 (ending with six eighths, figures 7 7 7 7 7 # 7),
    # which had no zone.
    'encodings/4/mattheson/score.xml': [
        ('rename', 'facsZone-m-1090-2', 'facsZone-m-1375'),
        ('facs', 'm-1090', '#facsZone-m-1090 #facsZone-m-1090-2', '#facsZone-m-1090'),
        ('facs', 'm-1375', None, '#facsZone-m-1375'),
    ],
    # No. 6, p. 330: line 4 holds mm. 7-8, line 6 mm. 12-13. The zone of m. 8
    # (no figures) was given to m. 12 (figure 6), which also named its own
    # zone twice (two identical zones).
    # p. 331: line 2 ends with mm. 24, 25, 26, line 3 begins with mm. 27
    # (no figure), 28 (figure 6), 29 (natural). The zones of mm. 27 and 28
    # were given to mm. 24 and 26 as second parts.
    'encodings/6/mattheson/score.xml': [
        ('delete', 'facsZone-m-373-2', 'facsZone-m-373-1'),
        ('rename', 'facsZone-m-373', 'facsZone-m-256'),
        ('rename', 'facsZone-m-373-1', 'facsZone-m-373'),
        ('facs', 'm-256', None, '#facsZone-m-256'),
        ('facs', 'm-373', '#facsZone-m-373 #facsZone-m-373-1 #facsZone-m-373-2', '#facsZone-m-373'),
        ('rename', 'facsZone-m-788-2', 'facsZone-m-888'),
        ('rename', 'facsZone-m-856-2', 'facsZone-m-907'),
        ('facs', 'm-788', '#facsZone-m-788 #facsZone-m-788-2', '#facsZone-m-788'),
        ('facs', 'm-856', '#facsZone-m-856 #facsZone-m-856-2', '#facsZone-m-856'),
        ('facs', 'm-888', None, '#facsZone-m-888'),
        ('facs', 'm-907', None, '#facsZone-m-907'),
    ],
    # No. 9, p. 347: m. 26 runs from the end of line 4 (quarter, eighth rest,
    # eighth) to the beginning of line 5 (C clef and eight 16ths, figure 6);
    # m. 27 is the middle of line 5 (16ths with an F clef in between, figures
    # 6 6 b5). The zone of the beginning of line 5 was given to m. 27, twice.
    'encodings/9/mattheson/score.xml': [
        ('delete', 'facsZone-m-901-1', 'facsZone-m-901'),
        ('rename', 'facsZone-m-901', 'facsZone-m-881-2'),
        ('rename', 'facsZone-m-901-2', 'facsZone-m-901'),
        ('facs', 'm-881', '#facsZone-m-881', '#facsZone-m-881 #facsZone-m-881-2'),
        ('facs', 'm-901', '#facsZone-m-901 #facsZone-m-901-1 #facsZone-m-901-2', '#facsZone-m-901'),
    ],
    # No. 15, p. 382: line 4 holds mm. 24-30; its first measure (figures 6 4 3)
    # is m. 24, which had no zone, not a first part of m. 30. Line 6 holds
    # mm. 38-42; its fourth measure is m. 41, which had no zone, not a first
    # part of m. 43 (the first measure of line 7).
    # p. 383: the end of line 5 is m. 82 (natural, C clef, figures 6 7), which
    # had no zone; m. 83 is the beginning of line 6 (figures 7 7 7 7). Both
    # zones were given to m. 83, the first one twice.
    'encodings/15/mattheson/score.xml': [
        ('rename', 'facsZone-staff-0000001550170287', 'facsZone-staff-0000000387927114'),
        ('rename', 'facsZone-staff-0000001550170287-2', 'facsZone-staff-0000001550170287'),
        ('facs', 'staff-0000000387927114', None, '#facsZone-staff-0000000387927114'),
        ('facs', 'staff-0000001550170287',
         '#facsZone-staff-0000001550170287 #facsZone-staff-0000001550170287-2',
         '#facsZone-staff-0000001550170287'),
        ('rename', 'facsZone-staff-0000000859763273', 'facsZone-staff-0000000704108684'),
        ('rename', 'facsZone-staff-0000000859763273-2', 'facsZone-staff-0000000859763273'),
        ('facs', 'staff-0000000704108684', None, '#facsZone-staff-0000000704108684'),
        ('facs', 'staff-0000000859763273',
         '#facsZone-staff-0000000859763273 #facsZone-staff-0000000859763273-2',
         '#facsZone-staff-0000000859763273'),
        ('delete', 'facsZone-staff-0000000533730066-1', 'facsZone-staff-0000000533730066'),
        ('rename', 'facsZone-staff-0000000533730066', 'facsZone-staff-0000000970881550'),
        ('rename', 'facsZone-staff-0000000533730066-2', 'facsZone-staff-0000000533730066'),
        ('facs', 'staff-0000000970881550', None, '#facsZone-staff-0000000970881550'),
        ('facs', 'staff-0000000533730066',
         '#facsZone-staff-0000000533730066 #facsZone-staff-0000000533730066-1 #facsZone-staff-0000000533730066-2',
         '#facsZone-staff-0000000533730066'),
    ],
    # No. 16, p. 393: m. 24 begins at the end of line 2 and ends at the
    # beginning of line 3, but its first zone was the one on line 3, so the
    # halves were shown in the wrong order. The two zone ids are swapped;
    # @facs stays as it is.
    'encodings/16/mattheson/score.xml': [
        ('rename', 'facsZone-staff-0000001342003217', 'facsZone-staff-0000001342003217-tmp'),
        ('rename', 'facsZone-staff-0000001342003217-2', 'facsZone-staff-0000001342003217'),
        ('rename', 'facsZone-staff-0000001342003217-tmp', 'facsZone-staff-0000001342003217-2'),
    ],
}


def zone_boxes(text):
    root = etree.fromstring(text.encode('utf-8'))
    return {z.get(XML_ID): tuple(z.get(k) for k in ('ulx', 'uly', 'lrx', 'lry')) for z in root.iter('{*}zone')}


def delete_zone(text, zone, duplicate_of):
    boxes = zone_boxes(text)
    if boxes[zone] != boxes[duplicate_of]:
        raise SystemExit(f'{zone} {boxes[zone]} is not a duplicate of {duplicate_of} {boxes[duplicate_of]}')
    span = X.tag_span(text, 'zone', 'xml:id', zone)
    a = text.rfind('\n', 0, span[0]) + 1
    b = text.index('\n', span[1]) + 1
    if text[a:span[0]].strip() or text[span[1]:b].strip():
        raise SystemExit(f'{zone} does not stand on a line of its own')
    return text[:a] + text[b:]


def rename_zone(text, old, new):
    """zone/@xml:id old -> new; pointers are set by the 'facs' operations."""
    if re.search(r'xml:id="%s"' % re.escape(new), text):
        raise SystemExit(f'cannot rename {old} to {new}: {new} exists')
    span = X.tag_span(text, 'zone', 'xml:id', old)
    return X.replace_span(text, span, X.set_attr(text[span[0]:span[1]], 'xml:id', new))


def set_facs(text, staff, old, new):
    span = X.tag_span(text, 'staff', 'xml:id', staff)
    tag = text[span[0]:span[1]]
    current = X.get_attr(tag, 'facs')
    if current != old:
        raise SystemExit(f'staff {staff}: @facs is {current!r}, expected {old!r}')
    tag = X.add_attr(tag, 'facs', new, after='n') if old is None else X.set_attr(tag, 'facs', new)
    return X.replace_span(text, span, tag)


def resolved(text):
    """(mdiv, measure n, staff n) -> zone boxes the staff's @facs points to, in order."""
    root = etree.fromstring(text.encode('utf-8'))
    boxes = {z.get(XML_ID): tuple(int(z.get(k)) if z.get(k) else None for k in ('ulx', 'uly', 'lrx', 'lry'))
             for z in root.iter('{*}zone')}
    out = {}
    for i, mdiv in enumerate(root.iter('{*}mdiv')):
        for measure in mdiv.iter('{*}measure'):
            for staff in measure.iter('{*}staff'):
                tokens = (staff.get('facs') or '').split()
                key = (i, measure.get('n'), staff.get('n'))
                if key in out:
                    raise SystemExit(f'ambiguous measure {key}')
                out[key] = [boxes.get(t[1:], 'UNRESOLVED ' + t) for t in tokens]
    return out


def main():
    do_apply = '--apply' in sys.argv
    for rel, ops in FIXES.items():
        path = REPO / rel
        text = path.read_text(encoding='utf-8')
        new_text = text
        targeted = set()
        for op in ops:
            kind = op[0]
            if kind == 'delete':
                new_text = delete_zone(new_text, op[1], op[2])
            elif kind == 'rename':
                new_text = rename_zone(new_text, op[1], op[2])
            elif kind == 'facs':
                new_text = set_facs(new_text, op[1], op[2], op[3])
                targeted.add(op[1])
        # what each measure shows, before and after
        before, after = resolved(text), resolved(new_text)
        staff_ids = {}
        root = etree.fromstring(new_text.encode('utf-8'))
        for i, mdiv in enumerate(root.iter('{*}mdiv')):
            for measure in mdiv.iter('{*}measure'):
                for staff in measure.iter('{*}staff'):
                    staff_ids[(i, measure.get('n'), staff.get('n'))] = staff.get(XML_ID)
        print(rel)
        for key in sorted(set(before) | set(after), key=lambda k: (k[0], int(re.sub(r'\D', '', k[1] or '0') or 0), k[2] or '')):
            if before.get(key) != after.get(key):
                note = '' if staff_ids.get(key) in targeted else '  (zone ids swapped)'
                print(f'  m. {key[1]} staff {key[2]}: {before.get(key)} -> {after.get(key)}{note}')
                if any(isinstance(b, str) for b in after.get(key, [])):
                    raise SystemExit(f'{rel}: unresolved pointer in m. {key[1]}')
        if do_apply and new_text != text:
            path.write_text(new_text, encoding='utf-8')
    print('applied.' if do_apply else 'dry run.')


if __name__ == '__main__':
    main()
