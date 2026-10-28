#!/usr/bin/env python3
"""Check the alignment of texts with the 1731 print, sentence by sentence.

A text aligned with another is divided into sentences, <s>, whose @corresp
points to the sentence or sentences of the other text that correspond to it.
Two kinds of text are aligned with the 1731 print:

  - the English translation, whose sentences point to the sentences they render:

    comments_1731.xml     <s xml:id="p1-1-s2">Ob nun das Gleichniß hincket, …</s>
    comments_1731_en.xml  <s corresp="comments_1731.xml#p1-1-s2">Whether or not …</s>
                          <s corresp="comments_1731.xml#p1-1-s2">To me it appeared …</s>

  - the 1719 print, whose sentences point to the sentences that Mattheson made
    of them in 1731; a sentence he left out points nowhere, and a sentence he
    added is pointed to by none:

    comments_1719.xml     <s xml:id="p1-1-s2" corresp="comments_1731.xml#p1-1-s2">Ob nun das Simile hincket, …</s>

works.xml tells the two apart: the expression of a translation has
@type="translation", that of a print @type="edition". The website shows the
other text between the lines. For every TEI file with such sentences the script
checks that

  1. each @corresp token of an <s> names an <s> of an existing file;
  2. a translation renders every sentence of the sections (<div>) of the
     original that it translates (a sentence left out would be missing from
     the comparison); sections it leaves out entirely are noted;
  3. the sentences follow the order of the text they point to (a sentence
     that shares a sentence of that text with the one before it may go back
     among that one's);
  4. the sentences of a print (the original and an aligned print) carry the
     ID of their paragraph and their number in it: p1-1-s1, p1-1-s2, …
     (a warning only);
  5. in a print, every word of a paragraph of the running text belongs to a
     sentence (notes, catchwords and the captions of figures aside).

The exit status is 0 if there are no problems, 1 otherwise.

Usage:
    python3 scripts/check_alignment.py [--root ENCODINGS_DIR] [--verbose] [PATH ...]

PATHs (files or directories) limit the check to the aligned texts under them.
--verbose lists the sentences of the prints that have no counterpart in the
other print.
"""

import argparse
import re
import sys
from pathlib import Path

from lxml import etree

TEI = '{http://www.tei-c.org/ns/1.0}'
MEI = '{http://www.music-encoding.org/ns/mei}'
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'

REPO = Path(__file__).resolve().parent.parent
PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)

# text outside the running text of a paragraph
ASIDE = {TEI + 'note', TEI + 'fw', TEI + 'figure', TEI + 'notatedMusic'}


def sentences(root):
    return list(root.iter(TEI + 's'))


def expression_types(root_dir):
    """The type of each expression in works.xml ("edition", "translation", …) by its ID."""
    path = root_dir / 'works.xml'
    if not path.is_file():
        return {}
    types = {}
    for expression in etree.parse(str(path), PARSER).getroot().iter(MEI + 'expression'):
        for token in (expression.get('data') or '').split():
            types[token.lstrip('#')] = expression.get('type')
    return types


def section_of(element):
    """The innermost <div> around an element."""
    for ancestor in element.iterancestors(TEI + 'div'):
        return ancestor
    return None


def section_label(div):
    if div is None:
        return 'the text outside any section'
    head = div.find(TEI + 'head')
    if head is not None and ''.join(head.itertext()).strip():
        return ' '.join(''.join(head.itertext()).split())
    return f'the section at line {div.sourceline}'


def aside(node):
    return any(a.tag in ASIDE for a in node.iterancestors())


def check_print(rel, root):
    """Problems and warnings about the sentences of a print."""
    problems, warnings = [], []
    text = root.find(TEI + 'text')
    for p in (text.iter(TEI + 'p') if text is not None else []):
        if aside(p):
            continue
        pid = p.get(XML_ID)
        for n, s in enumerate(p.iter(TEI + 's'), start=1):
            expected = f'{pid}-s{n}' if pid else None
            if s.get(XML_ID) != expected:
                warnings.append(f'{rel}:{s.sourceline}: sentence {n} of paragraph {pid or "(no xml:id)"} '
                                f'has xml:id {s.get(XML_ID)!r}, expected {expected!r}')
        loose = []
        for text in p.xpath('.//text()'):
            if not re.search(r'\w', text):
                continue
            parent = text.getparent()
            if any(a.tag == TEI + 's' for a in [parent, *parent.iterancestors()]):
                continue
            if parent.tag in ASIDE or aside(parent):
                continue
            loose.append(' '.join(text.split()))
        if loose:
            words = ' … '.join(loose)
            problems.append(f'{rel}:{p.sourceline}: words of paragraph {pid or "(no xml:id)"} outside '
                            f'its sentences: {words[:80]!r}')
    return problems, warnings


def check_aligned(path, rel, root, originals, translation):
    problems, notes = [], []
    # file -> IDs of the sentences pointed to
    used = {}
    last = {}
    # the sentences pointed to by the previous sentence: a sentence that shares one
    # of them may go back among them (the website shows the two together), e.g.
    # where the translator reordered a period
    previous = set()
    for s in sentences(root):
        found = []
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
            found.append((token, name, original, identifier, order))
            used.setdefault(original, set()).add(identifier)

        current = {(original, identifier) for _, _, original, identifier, _ in found}
        for token, name, original, identifier, order in found:
            position = order.index(identifier)
            if position < last.get(original, -1) and not current & previous:
                problems.append(f'{rel}:{s.sourceline}: {token!r} comes after '
                                f'{order[last[original]]!r}, which follows it in {name}')
        for _, _, original, identifier, order in found:
            last[original] = max(order.index(identifier), last.get(original, -1))
        previous = current

    if translation:
        for original, identifiers in used.items():
            all_sections, rendered = [], set()
            for x in sentences(originals[original]):
                section = section_of(x)
                if section not in all_sections:
                    all_sections.append(section)
                if x.get(XML_ID) in identifiers:
                    rendered.add(section)
            for x in sentences(originals[original]):
                if section_of(x) in rendered and x.get(XML_ID) not in identifiers:
                    problems.append(f'{rel}: no sentence renders {original.name}#{x.get(XML_ID)} '
                                    f'(line {x.sourceline})')
            left_out = [section for section in all_sections if section not in rendered]
            if left_out:
                notes.append(f'{rel} translates {len(all_sections) - len(left_out)} of the '
                             f'{len(all_sections)} sections of {original.name} that are divided into sentences')
    return problems, notes, used


def unmatched(rel, root, used, originals):
    """The sentences of two aligned prints that have no counterpart in the other."""
    lines = []
    alone = [s for s in sentences(root) if not s.get('corresp')]
    for s in alone:
        lines.append(f'{rel}:{s.sourceline}: {s.get(XML_ID)} has no counterpart')
    for original, identifiers in used.items():
        for x in sentences(originals[original]):
            if x.get(XML_ID) not in identifiers:
                lines.append(f'{original.name}:{x.sourceline}: {x.get(XML_ID)} has no counterpart in {rel}')
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--root', type=Path, default=REPO / 'encodings',
                        help='encodings directory to check (default: %(default)s)')
    parser.add_argument('--verbose', action='store_true',
                        help='list the sentences of the prints that have no counterpart in the other print')
    parser.add_argument('paths', nargs='*', type=Path,
                        help='check only the aligned texts in these files or directories')
    args = parser.parse_args(argv)

    root_dir = args.root.resolve()
    if not root_dir.is_dir():
        parser.error(f'{args.root} is not a directory')
    base = root_dir.parent
    limits = [p.resolve() for p in args.paths]
    types = expression_types(root_dir)

    originals = {}
    problems, warnings, notes, details = [], [], [], []
    texts, prints = 0, {}
    for path in sorted(root_dir.rglob('*.xml')):
        if limits and not any(path.resolve() == p or p in path.resolve().parents for p in limits):
            continue
        root = etree.parse(str(path), PARSER).getroot()
        if root.tag != TEI + 'TEI' or not any(s.get('corresp') for s in sentences(root)):
            continue
        texts += 1
        rel = path.relative_to(base).as_posix()
        translation = types.get(root.get(XML_ID)) == 'translation'
        found, noted, used = check_aligned(path, rel, root, originals, translation)
        problems += found
        notes += noted
        for original in used:
            prints[original] = originals[original]
        if not translation:
            prints[path.resolve()] = root
            if args.verbose:
                details += unmatched(rel, root, used, originals)
    for path, root in sorted(prints.items()):
        found, warned = check_print(path.relative_to(base).as_posix(), root)
        problems += found
        warnings += warned

    for line in problems:
        print(line)
    for line in warnings:
        print(f'warning: {line}')
    for line in notes + details:
        print(f'note: {line}')
    print(f'{texts} aligned text(s) and {len(prints)} print(s) checked: '
          f'{len(problems)} problem(s), {len(warnings)} warning(s).')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
