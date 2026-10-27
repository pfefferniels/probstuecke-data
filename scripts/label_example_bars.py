#!/usr/bin/env python3
"""Label the bars of the music examples with the bar numbers of the piece.

A bar of a music example (encodings/<n>/<name>/music-example*.xml or
example*.xml) that quotes a bar of the piece points to it with @corresp
('#id' of a <measure> in score.xml in the same directory). The script gives
such a bar the number of the quoted bar as @label: the @label of that
measure, or else its @n. The website shows these numbers on the examples; the
examples' own @n are only local counts and are not shown.

Bars without @corresp are left alone. The edits are made in the text of the
start tags, so the files keep their formatting.

With --check, nothing is written: the script lists the bars whose @label is
missing or differs from the quoted bar's number, and the @corresp that do not
name a measure of score.xml, and exits with 1 if there are any (0 otherwise).

Usage:
    python3 scripts/label_example_bars.py [--check] [FILE ...]
"""

import argparse
import re
import sys
from functools import lru_cache
from pathlib import Path

from lxml import etree

MEI = '{http://www.music-encoding.org/ns/mei}'
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'

REPO = Path(__file__).resolve().parent.parent
PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)


def example_files():
    root = REPO / 'encodings'
    return sorted(set(root.glob('*/*/music-example*.xml')) | set(root.glob('*/*/example*.xml')))


@lru_cache(maxsize=None)
def bar_numbers(score_path):
    """xml:id -> number shown for that bar, for every measure of a score"""
    numbers = {}
    if score_path.exists():
        for measure in etree.parse(str(score_path), PARSER).iter(MEI + 'measure'):
            number = measure.get('label') or measure.get('n')
            if measure.get(XML_ID) and number:
                numbers[measure.get(XML_ID)] = number
    return numbers


def set_label(line, label):
    """the line with the <measure> start tag on it, with @label set"""
    match = re.search(r'<measure(?=[\s>/])[^>]*>', line)
    tag = match.group(0)
    if re.search(r'\slabel="[^"]*"', tag):
        new_tag = re.sub(r'(\s)label="[^"]*"', lambda m: '%slabel="%s"' % (m.group(1), label), tag, count=1)
    else:
        # right after @corresp
        new_tag = re.sub(r'(\scorresp="[^"]*")', lambda m: '%s label="%s"' % (m.group(1), label), tag, count=1)
    return line[:match.start()] + new_tag + line[match.end():]


def process(path, check):
    """returns a list of problems (check) or of changes"""
    rel = path.relative_to(REPO)
    numbers = bar_numbers(path.parent / 'score.xml')
    tree = etree.parse(str(path), PARSER)
    raw = path.read_bytes()
    bom = raw.startswith(b'\xef\xbb\xbf')
    lines = raw[3 if bom else 0:].decode('utf-8').splitlines(keepends=True)
    messages = []
    for measure in tree.iter(MEI + 'measure'):
        corresp = measure.get('corresp')
        if not corresp:
            continue
        labels = []
        for token in corresp.split():
            number = numbers.get(token[1:]) if token.startswith('#') else None
            if number is None:
                messages.append('%s:%d: @corresp %s names no measure of %s'
                                % (rel, measure.sourceline, token, rel.parent / 'score.xml'))
            elif number not in labels:
                labels.append(number)
        if not labels:
            continue
        label = labels[0] if len(labels) == 1 else '%s–%s' % (labels[0], labels[-1])
        if measure.get('label') == label:
            continue
        if check:
            messages.append('%s:%d: @label should be "%s", is %s' % (
                rel, measure.sourceline, label,
                '"%s"' % measure.get('label') if measure.get('label') is not None else 'missing'))
        else:
            i = measure.sourceline - 1
            lines[i] = set_label(lines[i], label)
            messages.append('%s:%d: @label="%s"' % (rel, measure.sourceline, label))
    if not check:
        data = ''.join(lines).encode('utf-8')
        if bom:
            data = b'\xef\xbb\xbf' + data
        if data != raw:
            path.write_bytes(data)
    return messages


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--check', action='store_true', help='only report, do not write')
    parser.add_argument('files', nargs='*', type=Path, help='example files (default: all)')
    args = parser.parse_args()
    files = [f.resolve() for f in args.files] or example_files()

    problems = 0
    for path in files:
        for message in process(path, args.check):
            print(message)
            if args.check or '@corresp' in message:
                problems += 1
    if args.check:
        print('%d example files checked: %d problem(s).' % (len(files), problems))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
