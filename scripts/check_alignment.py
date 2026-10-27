#!/usr/bin/env python3
"""Check the alignment of the translations with the texts they translate.

A translation is divided into sentences, <s>, whose @corresp points to the
sentence or sentences of the original that it renders:

    comments_de.xml   <s xml:id="p1-1-s2">Ob nun das Gleichniß hincket, …</s>
    comments_en.xml   <s corresp="comments_de.xml#p1-1-s2">Whether or not …</s>
                      <s corresp="comments_de.xml#p1-1-s2">To me it appeared …</s>

The website shows the original between the lines of the translation. For every TEI
file with such sentences the script checks that

  1. each @corresp token of an <s> names an <s> of an existing file;
  2. every <s> of the original is rendered by some sentence of the
     translation (a sentence left out would be missing from the comparison);
  3. the sentences of the translation follow the order of the original;
  4. the sentences of the original carry the ID of their paragraph and their
     number in it: p1-1-s1, p1-1-s2, … (a warning only).

The exit status is 0 if there are no problems, 1 otherwise.

Usage:
    python3 scripts/check_alignment.py [--root ENCODINGS_DIR]
"""

import argparse
import re
import sys
from pathlib import Path

from lxml import etree

TEI = '{http://www.tei-c.org/ns/1.0}'
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'

REPO = Path(__file__).resolve().parent.parent
PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)


def sentences(root):
    return list(root.iter(TEI + 's'))


def check_original(rel, root):
    """Warnings about the IDs of the sentences of an original."""
    warnings = []
    for p in root.iter(TEI + 'p'):
        pid = p.get(XML_ID)
        for n, s in enumerate(p.iter(TEI + 's'), start=1):
            expected = f'{pid}-s{n}' if pid else None
            if s.get(XML_ID) != expected:
                warnings.append(f'{rel}:{s.sourceline}: sentence {n} of paragraph {pid or "(no xml:id)"} '
                                f'has xml:id {s.get(XML_ID)!r}, expected {expected!r}')
    return warnings


def check_translation(path, rel, root, originals):
    problems = []
    # original file -> IDs of its sentences in document order
    used = {}
    last = {}
    for s in sentences(root):
        for token in (s.get('corresp') or '').split():
            if '#' not in token:
                problems.append(f'{rel}:{s.sourceline}: {token!r} names no sentence')
                continue
            name, identifier = token.split('#', 1)
            original = (path.parent / name).resolve() if name else path.resolve()
            if original not in originals:
                if not original.is_file():
                    problems.append(f'{rel}:{s.sourceline}: {token!r}: no file {name!r}')
                    continue
                originals[original] = etree.parse(str(original), PARSER).getroot()
            order = [x.get(XML_ID) for x in sentences(originals[original])]
            if identifier not in order:
                problems.append(f'{rel}:{s.sourceline}: {token!r}: no <s xml:id="{identifier}"> in {name}')
                continue
            position = order.index(identifier)
            if position < last.get(original, -1):
                problems.append(f'{rel}:{s.sourceline}: {token!r} comes after '
                                f'{order[last[original]]!r}, which follows it in {name}')
            last[original] = max(position, last.get(original, -1))
            used.setdefault(original, set()).add(identifier)

    for original, identifiers in used.items():
        for x in sentences(originals[original]):
            if x.get(XML_ID) not in identifiers:
                problems.append(f'{rel}: no sentence renders {original.name}#{x.get(XML_ID)} '
                                f'(line {x.sourceline})')
    return problems, set(used)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--root', type=Path, default=REPO / 'encodings',
                        help='encodings directory to check (default: %(default)s)')
    args = parser.parse_args(argv)

    root_dir = args.root.resolve()
    if not root_dir.is_dir():
        parser.error(f'{args.root} is not a directory')
    base = root_dir.parent

    originals = {}
    problems, warnings = [], []
    translations, aligned = 0, set()
    for path in sorted(root_dir.rglob('*.xml')):
        root = etree.parse(str(path), PARSER).getroot()
        if root.tag != TEI + 'TEI' or not any(s.get('corresp') for s in sentences(root)):
            continue
        translations += 1
        found, used = check_translation(path, path.relative_to(base).as_posix(), root, originals)
        problems += found
        aligned |= used
    for original in sorted(aligned):
        warnings += check_original(original.relative_to(base).as_posix(), originals[original])

    for line in problems:
        print(line)
    for line in warnings:
        print(f'warning: {line}')
    print(f'{translations} aligned translation(s) of {len(aligned)} original(s) checked: '
          f'{len(problems)} problem(s), {len(warnings)} warning(s).')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
