#!/usr/bin/env python3
"""One-off repair: restore zone coordinates destroyed by the scripted repairs of 2020.

The zones were drawn in November 2019 with an annotation tool whose IIIF
annotation lists were kept as <n>/mattheson/facsimile_de.json (removed in
5644b39, April 2020). Zones were then copied into the encodings with
@lrx set to the old @lry + 1 and without @lry; commits a761702 and c084965
("add missing lry attributes", "repair nonsense lrx values") rebuilt the
missing values automatically, which went wrong for zones that the
annotation list gave in more than one part: they got the @lrx or @lry of
another part, or none. The annotation lists give each part as
canvas#xywh=x,y,w,h; every zone below keeps its @ulx/@uly, which identify
the part, and gets @lrx = x + w, @lry = y + h of that part.

Robert Hill's score of No. 3 (3/hill/score.xml) is a copy of the Mattheson
score made before those repairs: all 52 zones have @lrx = old @lry (+1) and
no @lry. They get the coordinates of the zone with the same xml:id in
3/mattheson/score.xml (same @ulx/@uly), after the repair of that file.

All coordinates are in the pixel space of the 2019 images, like the other
zones; they are rescaled to the current images in a later step
(rescale_zones.py). Run after that step, the script finds other @ulx/@uly
and stops at the first zone without changing anything.

Usage: python3 scripts/facsimile_repair/restore_zones.py [--apply]
"""
import sys
from pathlib import Path

from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xmledit as X  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'

# file -> zone xml:id -> (ulx, uly, lrx, lry) from the 2019 annotation lists
REPAIRS = {
    'encodings/1/mattheson/score.xml': {
        'facsZone-m-1230': (1158, 1865, 1929, 2197),        # 388#xywh=1158,1865,771,332
    },
    'encodings/2/mattheson/score.xml': {
        'facsZone-m-1025': (105, 725, 1092, 1030),          # 394#xywh=105,725,987,305
        'facsZone-m-1025-2': (111, 1025, 1491, 1381),       # 394#xywh=111,1025,1380,356
    },
    'encodings/3/mattheson/score.xml': {
        'facsZone-m-1115': (1221, 425, 1878, 679),          # 401#xywh=1221,425,657,254
        'facsZone-m-1323': (1563, 929, 1869, 1168),         # 401#xywh=1563,929,306,239 (listed under m-1115)
    },
    'encodings/4/mattheson/score.xml': {
        'facsZone-m-1090': (945, 602, 1929, 895),           # 406#xywh=945,602,984,293
        'facsZone-m-1090-2': (897, 1565, 1950, 1867),       # 406#xywh=897,1565,1053,302
    },
    'encodings/6/mattheson/score.xml': {
        'facsZone-m-373': (978, 1343, 1932, 1627),          # 414#xywh=978,1343,954,284
        'facsZone-m-373-1': (117, 1937, 1032, 2230),        # 414#xywh=117,1937,915,293 (listed twice)
        'facsZone-m-788': (1089, 464, 1344, 754),           # 415#xywh=1089,464,255,290
        'facsZone-m-788-2': (69, 779, 465, 1018),           # 415#xywh=69,779,396,239
        'facsZone-m-856': (1509, 479, 1881, 763),           # 415#xywh=1509,479,372,284
        'facsZone-m-856-2': (435, 779, 681, 1009),          # 415#xywh=435,779,246,230
    },
    'encodings/9/mattheson/score.xml': {
        'facsZone-m-901-1': (60, 1229, 585, 1474),          # 431#xywh=60,1229,525,245 (listed twice)
    },
    'encodings/10/mattheson/score.xml': {
        'facsZone-m-341-2': (1371, 1064, 1926, 1342),       # 436#xywh=1371,1064,555,278
        'facsZone-m-341-3': (93, 1352, 480, 1609),          # 436#xywh=93,1352,387,257
    },
    'encodings/15/mattheson/score.xml': {
        'facsZone-staff-0000001550170287': (141, 1100, 675, 1447),      # 466#xywh=141,1100,534,347
        'facsZone-staff-0000001550170287-2': (1512, 1055, 1977, 1450),  # 466#xywh=1512,1055,465,395
        'facsZone-staff-0000000859763273': (1398, 1718, 1653, 2005),    # 466#xywh=1398,1718,255,287
        'facsZone-staff-0000000859763273-2': (150, 1976, 606, 2284),    # 466#xywh=150,1976,456,308
        'facsZone-staff-0000000533730066-1': (1209, 1382, 1887, 1720),  # 467#xywh=1209,1382,678,338 (listed twice)
    },
    'encodings/16/mattheson/score.xml': {
        'facsZone-staff-0000001342003217': (54, 818, 798, 1156),        # 477#xywh=54,818,744,338
        'facsZone-staff-0000001342003217-2': (1407, 524, 1878, 823),    # 477#xywh=1407,524,471,299
    },
    'encodings/20/mattheson/comments_1731.xml': {
        'facsZone-p2-1': (45, 1895, 1494, 2251),            # 501#xywh=45,1895,1449,356
    },
}

HILL = 'encodings/3/hill/score.xml'
HILL_SOURCE = 'encodings/3/mattheson/score.xml'


def zones_of(text):
    root = etree.fromstring(text.encode('utf-8'))
    return {z.get(XML_ID): {k: z.get(k) for k in ('ulx', 'uly', 'lrx', 'lry')} for z in root.iter('{*}zone')}


def set_zone(text, zone_id, box):
    span = X.tag_span(text, 'zone', 'xml:id', zone_id)
    tag = text[span[0]:span[1]]
    if (X.get_attr(tag, 'ulx'), X.get_attr(tag, 'uly')) != (str(box[0]), str(box[1])):
        raise SystemExit(f'{zone_id}: @ulx/@uly differ from the part {box}: {tag}')
    tag = X.set_attr(tag, 'lrx', str(box[2]))
    if X.get_attr(tag, 'lry') is None:
        tag = X.add_attr(tag, 'lry', str(box[3]), after='lrx')
    else:
        tag = X.set_attr(tag, 'lry', str(box[3]))
    return X.replace_span(text, span, tag)


def main():
    do_apply = '--apply' in sys.argv
    texts = {}
    changes = 0
    for rel, table in REPAIRS.items():
        text = (REPO / rel).read_text(encoding='utf-8')
        before = zones_of(text)
        for zone_id, box in table.items():
            old = before[zone_id]
            new = dict(zip(('ulx', 'uly', 'lrx', 'lry'), map(str, box)))
            if old != new:
                print(f'{rel}: {zone_id} {old} -> {new}')
                text = set_zone(text, zone_id, box)
                changes += 1
        texts[rel] = text
    source = zones_of(texts.get(HILL_SOURCE) or (REPO / HILL_SOURCE).read_text(encoding='utf-8'))
    text = (REPO / HILL).read_text(encoding='utf-8')
    for zone_id, old in zones_of(text).items():
        new = source[zone_id]
        if old != new:
            if (old['ulx'], old['uly']) != (new['ulx'], new['uly']) or old['lry'] is not None \
                    or abs(int(old['lrx']) - int(new['lry'])) > 1:
                raise SystemExit(f'{HILL}: {zone_id} {old} is not a copy of {new}')
            text = set_zone(text, zone_id, tuple(int(new[k]) for k in ('ulx', 'uly', 'lrx', 'lry')))
            changes += 1
    print(f'{HILL}: zones copied from {HILL_SOURCE}')
    texts[HILL] = text
    if do_apply:
        for rel, text in texts.items():
            (REPO / rel).write_text(text, encoding='utf-8')
    print(f'{changes} zones' + (' changed.' if do_apply else ' to change (dry run).'))


if __name__ == '__main__':
    main()
