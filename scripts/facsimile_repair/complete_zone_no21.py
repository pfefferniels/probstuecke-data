#!/usr/bin/env python3
"""One-off repair: complete the zone of No. 21, m. 34 (1731, p. 422).

The zone facsZone-staff-0000002060769570 was never in the 2019 annotation
lists; it was added by hand with @ulx, @uly and an @lrx of 2200 (beyond the
right edge of the page) and no @lry, so the website could not show the bar.
Its @ulx and @uly (967, 1900 after rescaling) are right: the zone starts at
the barline before the bar, at the top of the other zones of the system.
@lrx and @lry are taken from the current image of canvas 484 (2031x2529):

  - the final double bar of the piece is at x = 1332-1347; @lrx = 1377 leaves
    the 30 px margin of the other zones of this file behind it;
  - the lowest note of the bar (d, with its rest) reaches y = 2179; @lry =
    2193 is the lower edge of the zone of m. 33 in the same system.

The copy of the score in 21/molinaro has the same zone.

Usage: python3 scripts/facsimile_repair/complete_zone_no21.py [--apply]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xmledit as X  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
FILES = ['encodings/21/mattheson/score.xml', 'encodings/21/molinaro/score.xml']
ZONE = 'facsZone-staff-0000002060769570'
EXPECTED = {'ulx': '967', 'uly': '1900'}
NEW = {'lrx': '1377', 'lry': '2193'}


def main():
    do_apply = '--apply' in sys.argv
    for rel in FILES:
        path = REPO / rel
        text = path.read_text(encoding='utf-8')
        span = X.tag_span(text, 'zone', 'xml:id', ZONE)
        tag = text[span[0]:span[1]]
        for k, v in EXPECTED.items():
            if X.get_attr(tag, k) != v:
                raise SystemExit(f'{rel}: {ZONE} has @{k}={X.get_attr(tag, k)}, expected {v}')
        new = X.set_attr(tag, 'lrx', NEW['lrx'])
        new = X.add_attr(new, 'lry', NEW['lry'], after='lrx') if X.get_attr(new, 'lry') is None \
            else X.set_attr(new, 'lry', NEW['lry'])
        print(f'{rel}:\n  {tag}\n  {new}')
        if do_apply and new != tag:
            path.write_text(X.replace_span(text, span, new), encoding='utf-8')
    print('applied.' if do_apply else 'dry run.')


if __name__ == '__main__':
    main()
