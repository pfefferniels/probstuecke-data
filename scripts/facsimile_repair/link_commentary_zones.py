#!/usr/bin/env python3
"""One-off repair: point commentary paragraphs of the 1731 print to their zones.

Five commentaries (comments_1731.xml) have zones that frame a paragraph but are
not named in its @facs, because the paragraph's xml:id and the zone's name
diverged when the text was encoded. Each zone was checked on the page image.

  No. 7   §. 3 begins at the foot of p. 338 (zone "p2-3") and goes on at the
          top of p. 339 (zone "p3-1"); p3-1 named only the second part.
  No. 12, 13, 14
          §. 6 has a single paragraph with the xml:id "p6-2"; the zone
          "p6-1" frames it, but the paragraph had no @facs.
  No. 18  p6-1 continues after the music example at the top of p. 409
          ("Wobey jedoch unausbleiblich ..."), framed by zone "p6-2".
  No. 21  §. 1 (paragraph "p1-1", p. 423) is framed by zone "p1"; the
          paragraph had no @facs.

Zone ids are left as they are. (The zones "p2-1" and "p2-1-2" of No. 8 frame
§. 2, which is not transcribed in comments_1731.xml; they stay unused.)

Usage: python3 scripts/facsimile_repair/link_commentary_zones.py [--apply]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xmledit as X  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent

# file -> paragraph xml:id -> (old @facs or None, new @facs)
LINKS = {
    'encodings/7/mattheson/comments_1731.xml': {'p3-1': ('#facsZone-p3-1', '#facsZone-p2-3 #facsZone-p3-1')},
    'encodings/12/mattheson/comments_1731.xml': {'p6-2': (None, '#facsZone-p6-1')},
    'encodings/13/mattheson/comments_1731.xml': {'p6-2': (None, '#facsZone-p6-1')},
    'encodings/14/mattheson/comments_1731.xml': {'p6-2': (None, '#facsZone-p6-1')},
    'encodings/18/mattheson/comments_1731.xml': {'p6-1': ('#facsZone-p6-1', '#facsZone-p6-1 #facsZone-p6-2')},
    'encodings/21/mattheson/comments_1731.xml': {'p1-1': (None, '#facsZone-p1')},
}


def main():
    do_apply = '--apply' in sys.argv
    for rel, table in LINKS.items():
        path = REPO / rel
        text = path.read_text(encoding='utf-8')
        for pid, (old, new) in table.items():
            for token in new.split():
                X.tag_span(text, 'zone', 'xml:id', token[1:])      # the zone must exist
            span = X.tag_span(text, 'p', 'xml:id', pid)
            tag = text[span[0]:span[1]]
            if X.get_attr(tag, 'facs') == new:
                print(f'{rel}: {pid} already points to {new}')
                continue
            if X.get_attr(tag, 'facs') != old:
                raise SystemExit(f'{rel}: {pid} has @facs {X.get_attr(tag, "facs")!r}, expected {old!r}')
            new_tag = X.add_attr(tag, 'facs', new, after='xml:id') if old is None else X.set_attr(tag, 'facs', new)
            print(f'{rel}:\n  {tag}\n  {new_tag}')
            text = X.replace_span(text, span, new_tag)
        if do_apply:
            path.write_text(text, encoding='utf-8')
    print('applied.' if do_apply else 'dry run.')


if __name__ == '__main__':
    main()
