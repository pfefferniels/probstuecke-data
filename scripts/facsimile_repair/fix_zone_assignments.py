#!/usr/bin/env python3
"""One-off repair: attach misassigned zones of the 1731 scores to the right measures.

When the zones were drawn in 2019, some were attached to the wrong <staff>:
the second part of a measure that runs over a line break was given to the
measure before it, a measure that had no zone of its own got the zone of a
neighbouring measure, or a zone was attached twice; in 2020 the re-encoding
of two scores dropped some pointers. Each case below was established on the
page image: the order of the measures on the line, their notes and the
figures above them (see the comments). The zones keep their coordinates; the
script

  - deletes zones that are exact duplicates of another zone,
  - names every zone concerned after the staff it belongs to
    (facsZone-<staff id>, with -2 for the part on the next line), so that the
    ids say again which measure a zone shows; zones are identified by their
    coordinates,
  - sets staff/@facs of every measure concerned (adding it where a measure
    had no zone),
and lists, for every measure whose zones change, the zone boxes before and
after. Operations already carried out are skipped, so the script can be run
again.

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

# file -> {'delete': [(zone, duplicate_of)],          zone must have the coordinates of duplicate_of
#          'ids':    {(ulx, uly, lrx, lry): new id},   the zone with these coordinates
#          'facs':   [(staff, old @facs or None, new @facs)]}
# A staff is given by its xml:id or, if it has none, as 'm<measure n>/s<staff n>'.
FIXES = {
    # No. 1, pp. 304-305: p. 304, line 3 holds m. 26 (figures 6 # 6 4) and
    # m. 27 (figures 6 6 6 6), but both zones of the line were given to
    # m. 26; mm. 35 and 36 named the zone of their second part two and
    # three times.
    'encodings/1/mattheson/score.xml': {
        'ids': {(970, 571, 1986, 901): 'facsZone-m-929'},
        'facs': [
            ('m-899', '#facsZone-m-899 #facsZone-m-899-2', '#facsZone-m-899'),
            ('m-929', None, '#facsZone-m-929'),
            ('m-1230', '#facsZone-m-1230 #facsZone-m-1230-2 #facsZone-m-1230-2',
             '#facsZone-m-1230 #facsZone-m-1230-2'),
            ('m-1268', '#facsZone-m-1268 #facsZone-m-1268-2 #facsZone-m-1268-2 #facsZone-m-1268-2',
             '#facsZone-m-1268 #facsZone-m-1268-2'),
        ],
    },
    # No. 2, pp. 309-310: p. 309, line 2 is m. 11 (four groups of 32nds,
    # figures 7 6 7 6); line 3 begins with m. 12 (figures 7b 6 6 6/4 #),
    # which had no zone; its zone was a second part of m. 11.
    # p. 310: line 3 holds m. 22 and the first half of m. 23, line 4 the
    # second half of m. 23 (32nds on b, a and g with the figures 7b, 7, 7,
    # 7 natural); the zone of line 4 was a second part of m. 22.
    'encodings/2/mattheson/score.xml': {
        'ids': {(35, 845, 1250, 1243): 'facsZone-m-572',
                (98, 1077, 1530, 1447): 'facsZone-m-1058-2'},
        'facs': [
            ('m-515', '#facsZone-m-515 #facsZone-m-515-2', '#facsZone-m-515'),
            ('m-572', None, '#facsZone-m-572'),
            ('m-1025', '#facsZone-m-1025 #facsZone-m-1025-2', '#facsZone-m-1025'),
            ('m-1058', '#facsZone-m-1058', '#facsZone-m-1058 #facsZone-m-1058-2'),
        ],
    },
    # Hill's copy of No. 3 lost the pointer of m. 36 (p. 317, line 3, three
    # quarters on g); the zone is still in the file, as in the Mattheson score.
    'encodings/3/hill/score.xml': {
        'facs': [('m-1322', None, '#facsZone-m-1323')],
    },
    # No. 4, p. 322: m. 25 is complete at the end of line 2 (ending with two
    # quarters); the zone at the end of line 5 that was given to it as a
    # second part is m. 30 (ending with six eighths, figures 7 7 7 7 7 # 7),
    # which had no zone.
    'encodings/4/mattheson/score.xml': {
        'ids': {(919, 1636, 2003, 1948): 'facsZone-m-1375'},
        'facs': [
            ('m-1090', '#facsZone-m-1090 #facsZone-m-1090-2', '#facsZone-m-1090'),
            ('m-1375', None, '#facsZone-m-1375'),
        ],
    },
    # No. 6, p. 330: line 4 holds mm. 7-8, line 6 mm. 12-13. The zone of m. 8
    # (no figures) was given to m. 12 (figure 6), which also named its own
    # zone twice (two identical zones).
    # p. 331: line 2 ends with mm. 24, 25, 26, line 3 begins with mm. 27
    # (no figure), 28 (figure 6), 29 (natural). The zones of mm. 27 and 28
    # were given to mm. 24 and 26 as second parts.
    'encodings/6/mattheson/score.xml': {
        'delete': [('facsZone-m-373-2', 'facsZone-m-373-1')],
        'ids': {(1004, 1400, 1981, 1691): 'facsZone-m-256',
                (123, 2009, 1060, 2309): 'facsZone-m-373',
                (41, 828, 448, 1073): 'facsZone-m-888',
                (417, 828, 670, 1064): 'facsZone-m-907'},
        'facs': [
            ('m-256', None, '#facsZone-m-256'),
            ('m-373', '#facsZone-m-373 #facsZone-m-373-1 #facsZone-m-373-2', '#facsZone-m-373'),
            ('m-788', '#facsZone-m-788 #facsZone-m-788-2', '#facsZone-m-788'),
            ('m-856', '#facsZone-m-856 #facsZone-m-856-2', '#facsZone-m-856'),
            ('m-888', None, '#facsZone-m-888'),
            ('m-907', None, '#facsZone-m-907'),
        ],
    },
    # No. 9, p. 347: m. 26 runs from the end of line 4 (quarter, eighth rest,
    # eighth) to the beginning of line 5 (C clef and eight 16ths, figure 6);
    # m. 27 is the middle of line 5 (16ths with an F clef in between, figures
    # 6 6 b5). The zone of the beginning of line 5 was given to m. 27, twice.
    'encodings/9/mattheson/score.xml': {
        'delete': [('facsZone-m-901-1', 'facsZone-m-901')],
        'ids': {(24, 1302, 567, 1555): 'facsZone-m-881-2',
                (546, 1289, 1480, 1586): 'facsZone-m-901'},
        'facs': [
            ('m-881', '#facsZone-m-881', '#facsZone-m-881 #facsZone-m-881-2'),
            ('m-901', '#facsZone-m-901 #facsZone-m-901-1 #facsZone-m-901-2', '#facsZone-m-901'),
        ],
    },
    # No. 10, p. 352: line 2 holds the end of m. 12, m. 13, m. 14 (figure 6)
    # and the beginning of m. 15 (figure 5b), which ends on line 3. The zone
    # of m. 14 was a first part of m. 15.
    'encodings/10/mattheson/score.xml': {
        'ids': {(1014, 1132, 1489, 1398): 'facsZone-m-321',
                (1439, 1135, 2021, 1426): 'facsZone-m-341',
                (99, 1437, 504, 1706): 'facsZone-m-341-2'},
        'facs': [
            ('m-321', None, '#facsZone-m-321'),
            ('m-341', '#facsZone-m-341 #facsZone-m-341-2 #facsZone-m-341-3', '#facsZone-m-341 #facsZone-m-341-2'),
        ],
    },
    # No. 11, p. 361: the zones of line 3 belong to mm. 23 and 24, whose staffs
    # had the xml:ids staff-0000000633397600 and staff-0000001023194498 until
    # the score was re-encoded in May 2020 (44f83a7), which dropped the ids
    # and the pointers.
    'encodings/11/mattheson/score.xml': {
        'facs': [
            ('m23/s2', None, '#facsZone-staff-0000000633397600'),
            ('m24/s2', None, '#facsZone-staff-0000001023194498'),
        ],
    },
    # No. 15, p. 382: line 4 holds mm. 24-30; its first measure (figures 6 4 3)
    # is m. 24, which had no zone, not a first part of m. 30. Line 6 holds
    # mm. 38-42; its fourth measure is m. 41, which had no zone, not a first
    # part of m. 43 (the first measure of line 7).
    # p. 383: the end of line 5 is m. 82 (natural, C clef, figures 6 7), which
    # had no zone; m. 83 is the beginning of line 6 (figures 7 7 7 7). Both
    # zones were given to m. 83, the first one twice.
    'encodings/15/mattheson/score.xml': {
        'delete': [('facsZone-staff-0000000533730066-1', 'facsZone-staff-0000000533730066')],
        'ids': {(127, 1159, 678, 1517): 'facsZone-staff-0000000387927114',
                (1540, 1113, 2010, 1520): 'facsZone-staff-0000001550170287',
                (1423, 1796, 1685, 2092): 'facsZone-staff-0000000704108684',
                (137, 2062, 606, 2379): 'facsZone-staff-0000000859763273',
                (1221, 1457, 1927, 1809): 'facsZone-staff-0000000970881550',
                (0, 1800, 419, 2058): 'facsZone-staff-0000000533730066'},
        'facs': [
            ('staff-0000000387927114', None, '#facsZone-staff-0000000387927114'),
            ('staff-0000001550170287', '#facsZone-staff-0000001550170287 #facsZone-staff-0000001550170287-2',
             '#facsZone-staff-0000001550170287'),
            ('staff-0000000704108684', None, '#facsZone-staff-0000000704108684'),
            ('staff-0000000859763273', '#facsZone-staff-0000000859763273 #facsZone-staff-0000000859763273-2',
             '#facsZone-staff-0000000859763273'),
            ('staff-0000000970881550', None, '#facsZone-staff-0000000970881550'),
            ('staff-0000000533730066', '#facsZone-staff-0000000533730066 #facsZone-staff-0000000533730066-1 '
             '#facsZone-staff-0000000533730066-2', '#facsZone-staff-0000000533730066'),
        ],
    },
    # No. 16, p. 393: m. 24 begins at the end of line 2 and ends at the
    # beginning of line 3, but its first zone was the one on line 3, so the
    # halves were shown in the wrong order. The two zone ids are swapped;
    # @facs stays as it is.
    'encodings/16/mattheson/score.xml': {
        'ids': {(1417, 564, 1908, 875): 'facsZone-staff-0000001342003217',
                (7, 870, 782, 1222): 'facsZone-staff-0000001342003217-2'},
    },
}


def zone_tags(text):
    """[(span, tag)] of all zone start tags."""
    return [(m.span(), m.group(0)) for m in re.finditer(r'<(?:\w+:)?zone\b[^<>]*>', text)]


def box_of(tag):
    return tuple(int(X.get_attr(tag, k)) if X.get_attr(tag, k) else None for k in ('ulx', 'uly', 'lrx', 'lry'))


def delete_zone(text, zone, duplicate_of):
    if not re.search(r'xml:id="%s"' % re.escape(zone), text):
        return text, False                                    # already deleted
    a_span = X.tag_span(text, 'zone', 'xml:id', zone)
    b_span = X.tag_span(text, 'zone', 'xml:id', duplicate_of)
    if box_of(text[slice(*a_span)]) != box_of(text[slice(*b_span)]):
        raise SystemExit(f'{zone} is not a duplicate of {duplicate_of}')
    a = text.rfind('\n', 0, a_span[0]) + 1
    b = text.index('\n', a_span[1]) + 1
    if text[a:a_span[0]].strip() or text[a_span[1]:b].strip():
        raise SystemExit(f'{zone} does not stand on a line of its own')
    return text[:a] + text[b:], True


def set_zone_id(text, box, new):
    hits = [(span, tag) for span, tag in zone_tags(text) if box_of(tag) == box]
    if len(hits) != 1:
        raise SystemExit(f'expected one zone with the coordinates {box}, found {len(hits)}')
    span, tag = hits[0]
    if X.get_attr(tag, 'xml:id') == new:
        return text, False
    return X.replace_span(text, span, X.set_attr(tag, 'xml:id', new)), True


def staff_span(text, locator):
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


def set_facs(text, locator, old, new):
    span = staff_span(text, locator)
    tag = text[span[0]:span[1]]
    current = X.get_attr(tag, 'facs')
    if current == new:
        return text, False
    if current != old:
        raise SystemExit(f'staff {locator}: @facs is {current!r}, expected {old!r}')
    tag = X.add_attr(tag, 'facs', new, after='n') if old is None else X.set_attr(tag, 'facs', new)
    return X.replace_span(text, span, tag), True


def resolved(text):
    """(mdiv, measure n, staff n) -> zone boxes the staff's @facs points to, in order."""
    root = etree.fromstring(text.encode('utf-8'))
    boxes = {z.get(XML_ID): tuple(int(z.get(k)) if z.get(k) else None for k in ('ulx', 'uly', 'lrx', 'lry'))
             for z in root.iter('{*}zone')}
    out = {}
    for i, mdiv in enumerate(root.iter('{*}mdiv')):
        for measure in mdiv.iter('{*}measure'):
            for staff in measure.iter('{*}staff'):
                key = (i, measure.get('n'), staff.get('n'))
                if key in out and key[1] is not None:
                    raise SystemExit(f'ambiguous measure {key}')
                out[key] = [boxes.get(t[1:], 'UNRESOLVED ' + t) for t in (staff.get('facs') or '').split()]
    return out


def main():
    do_apply = '--apply' in sys.argv
    for rel, fix in FIXES.items():
        path = REPO / rel
        text = path.read_text(encoding='utf-8')
        new_text, done = text, 0
        for zone, duplicate_of in fix.get('delete', []):
            new_text, changed = delete_zone(new_text, zone, duplicate_of)
            done += changed
        for box, new in fix.get('ids', {}).items():
            new_text, changed = set_zone_id(new_text, box, new)
            done += changed
        for locator, old, new in fix.get('facs', []):
            new_text, changed = set_facs(new_text, locator, old, new)
            done += changed
        root = etree.fromstring(new_text.encode('utf-8'))
        ids = [z.get(XML_ID) for z in root.iter('{*}zone')]
        if len(ids) != len(set(ids)):
            raise SystemExit(f'{rel}: duplicate zone ids')
        before, after = resolved(text), resolved(new_text)
        print(f'{rel}: {done} changes' + ('' if done else ' (already done)'))
        for key in sorted(set(before) | set(after), key=lambda k: (k[0], int(re.sub(r'\D', '', k[1] or '0') or 0), k[2] or '')):
            if before.get(key) != after.get(key):
                print(f'  m. {key[1]} staff {key[2]}: {before.get(key)} -> {after.get(key)}')
                if any(isinstance(b, str) for b in after.get(key, [])):
                    raise SystemExit(f'{rel}: unresolved pointer in m. {key[1]}')
        if do_apply and new_text != text:
            path.write_text(new_text, encoding='utf-8')
    print('applied.' if do_apply else 'dry run.')


if __name__ == '__main__':
    main()
