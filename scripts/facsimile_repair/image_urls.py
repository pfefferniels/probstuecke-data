#!/usr/bin/env python3
"""Let every <graphic> point to the page image, and its <surface> to the IIIF canvas.

The graphics of the facsimile sections named the IIIF canvas of the page
(.../iiif/presentation/v2/<bsb-id>/canvas/<n>). A canvas is not an image
(probstuecke-data#31), so the graphic now gives the full image of the page
from the IIIF Image API, and the surface keeps the canvas in @corresp:

    <surface xml:id="facs-p411" corresp=".../iiif/presentation/v2/bsb10598495/canvas/411" …>
      <graphic url=".../iiif/image/v2/bsb10598495_00411/full/full/0/default.jpg" …/>

The edits are made on the text, so the files keep their formatting. Running the
script again changes nothing; run it after adding surfaces in the old form.

Usage: python3 scripts/facsimile_repair/image_urls.py [--check]
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANVAS = re.compile(r'https://api\.digitale-sammlungen\.de/iiif/presentation/v2/(bsb\d{8})/canvas/(\d+)')
SURFACE = re.compile(r'<(?:\w+:)?surface\b[^<>]*>')
GRAPHIC = re.compile(r'<(?:\w+:)?graphic\b[^<>]*>')


def image_url(bsb, canvas):
    return f'https://api.digitale-sammlungen.de/iiif/image/v2/{bsb}_{int(canvas):05d}/full/full/0/default.jpg'


def convert(text):
    out, pos, changes = [], 0, 0
    for surface in SURFACE.finditer(text):
        graphic = GRAPHIC.search(text, surface.end())
        if not graphic:
            continue
        canvas = CANVAS.search(graphic.group())
        if not canvas:
            continue
        surface_tag = surface.group()
        if 'corresp=' not in surface_tag:
            end = -2 if surface_tag.endswith('/>') else -1
            surface_tag = f'{surface_tag[:end].rstrip()} corresp="{canvas.group()}"{surface_tag[end:]}'
        graphic_tag = graphic.group().replace(canvas.group(), image_url(*canvas.groups()))
        out += [text[pos:surface.start()], surface_tag, text[surface.end():graphic.start()], graphic_tag]
        pos = graphic.end()
        changes += 1
    out.append(text[pos:])
    return ''.join(out), changes


def main():
    check = '--check' in sys.argv
    total = 0
    for path in sorted((ROOT / 'encodings').rglob('*.xml')):
        text = path.read_text(encoding='utf-8')
        new, changes = convert(text)
        if changes:
            total += changes
            print(f'{path.relative_to(ROOT)}: {changes} surface(s)')
            if not check:
                path.write_text(new, encoding='utf-8')
    print(f'{total} surface(s) {"to convert" if check else "converted"}')
    sys.exit(1 if check and total else 0)


if __name__ == '__main__':
    main()
