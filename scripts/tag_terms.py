#!/usr/bin/env python3
"""Tag the occurrences listed in the index of terms in the transcriptions.

encodings/indices/terms.xml lists for every term the passages that Mattheson's
Register (type="register") or the editors (type="editorial") refer to, e.g.

    <ref type="register" n="312" target="../2/mattheson/comments_de.xml">die pag. 307.
      angefuͤhrte <term>Brechung</term> mit Sexten</ref>

@n is the page of the print, the content a short quotation from the passage in
which <term> marks the word or phrase to tag. For every such ref whose @target
names a file but no element yet, the script looks for the quotation on that
page of the file (pages are counted by <pb n="…"/>), wraps the marked word in

    <term xml:id="t_arpeggio-1" corresp="#t_arpeggio">Brechung</term>

and adds the new xml:id to the ref's @target. If the word is already wrapped in a
<term> for another entry, that element gets a second pointer in @corresp.

Refs whose @target already points to an element, and refs without a quotation
(links to a score, a music example, a paragraph or only a page), are left alone,
so the script can be run again whenever transcriptions are added or replaced:
it only tags what is still missing. A quotation that is not on the given page
(e.g. because the page breaks are wrong or missing) is accepted if it occurs
only once in the file. If the quotation is not found at all (e.g. because a new
transcription reads differently), the marked word alone is tried on that page;
otherwise the ref is reported and left as it is.

The files are edited as text: only the tags are inserted, the rest of the
encoding keeps its formatting.

Usage:
    python3 scripts/tag_terms.py [--dry-run] [--exclude PATH ...] [--root ENCODINGS_DIR]

--exclude skips target files (paths relative to the encodings directory, e.g.
10/mattheson/comments_de.xml), for instance transcriptions that are still being
revised.
"""

import argparse
import re
import sys
from pathlib import Path

from lxml import etree

TEI = '{http://www.tei-c.org/ns/1.0}'
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'
REPO = Path(__file__).resolve().parent.parent

# elements whose text is not part of the running text
SKIP = {'teiHeader', 'facsimile', 'fw', 'reg', 'corr', 'expan'}
UMLAUT = {'a': 'ä', 'o': 'ö', 'u': 'ü'}
ENTITIES = {'&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&apos;': "'"}


def normalise(text):
    """Lower case, round s, umlauts with ¨, single spaces."""
    text = text.replace('ſ', 's')
    text = re.sub('([aouAOU])\u0364', lambda m: UMLAUT[m.group(1).lower()], text)
    return re.sub(r'\s+', ' ', text.lower()).strip()


class Stream:
    """The running text of a TEI file, normalised, with the raw offset and page of every character."""

    def __init__(self, raw):
        self.raw = raw
        self.chars, self.starts, self.ends, self.pages = [], [], [], []
        self.terms = []  # (raw start of <term …>, raw end of </term>) of existing tags
        self._joining = False
        self._page = None
        self._scan()

    def text(self):
        return ''.join(self.chars)

    def _push(self, char, start, end):
        if char == ' ' and (self._joining or (self.chars and self.chars[-1] == ' ')):
            return
        self._joining = False
        self.chars.append(char)
        self.starts.append(start)
        self.ends.append(end)
        self.pages.append(self._page)

    def _line_break(self):
        # a word hyphenated at the end of the line is joined
        k = len(self.chars) - 1
        while k >= 0 and self.chars[k] == ' ':
            k -= 1
        if k > 0 and self.chars[k] in '-=' and self.chars[k - 1].isalpha():
            for column in (self.chars, self.starts, self.ends, self.pages):
                del column[k:]
            self._joining = True
        else:
            self._push(' ', None, None)

    def _scan(self):
        raw = self.raw
        i = raw.find('<text')
        skip = []
        open_terms = []
        first_pb = True
        while 0 <= i < len(raw):
            c = raw[i]
            if c == '<':
                if raw.startswith('<!--', i):
                    i = raw.index('-->', i) + 3
                    continue
                j = raw.index('>', i)
                tag = raw[i + 1:j]
                if tag.startswith('?') or tag.startswith('!'):
                    i = j + 1
                    continue
                name = re.match(r'/?\s*([\w:.-]+)', tag).group(1)
                if tag.startswith('/'):
                    if skip and skip[-1][0] == name:
                        skip[-1][1] -= 1
                        if skip[-1][1] == 0:
                            skip.pop()
                    if name == 'term' and open_terms:
                        self.terms.append((open_terms.pop(), j + 1))
                elif tag.endswith('/'):
                    if not skip:
                        if name == 'pb':
                            n = re.search(r'\bn="(\d+)"', tag)
                            if n:
                                page = int(n.group(1))
                                if first_pb:
                                    # text before the first page break is on the preceding page
                                    self.pages = [page - 1] * len(self.pages)
                                    first_pb = False
                                self._page = page
                        elif name == 'lb':
                            self._line_break()
                else:
                    attrs = dict(re.findall(r'([\w:]+)="([^"]*)"', tag))
                    if skip and skip[-1][0] == name:
                        skip[-1][1] += 1
                    elif not skip and (name in SKIP or (name == 'note' and attrs.get('type') == 'editorial')):
                        skip.append([name, 1])
                    if name == 'term':
                        open_terms.append(i)
                    if not skip and name in ('p', 'head', 'note', 'item', 'div', 'l'):
                        self._push(' ', None, None)
                i = j + 1
                continue
            if skip:
                i += 1
                continue
            if c == '&':
                j = raw.index(';', i)
                self._push(ENTITIES.get(raw[i:j + 1], '?'), i, j + 1)
                i = j + 1
                continue
            if c == '\u0364' and self.chars and self.chars[-1] in 'aou':  # superscript e
                self.chars[-1] = UMLAUT[self.chars[-1]]
                self.ends[-1] = i + 1
                i += 1
                continue
            char = ' ' if c.isspace() else c.replace('ſ', 's').lower()
            self._push(char, i, i + 1)
            i += 1


def open_ends(fragment):
    """Number of elements opened but not closed, and closed but not opened, in a piece of XML."""
    stack, unopened = [], 0
    for m in re.finditer(r'<(/?)([\w:.-]+)[^>]*?(/?)>', fragment):
        closing, name, empty = m.groups()
        if empty:
            continue
        if closing:
            if stack:
                stack.pop()
            else:
                unopened += 1
        else:
            stack.append(name)
    return len(stack), unopened


def balanced(fragment):
    return open_ends(fragment) == (0, 0)


def is_word_boundary(text, a, b):
    return (a == 0 or not text[a - 1].isalnum()) and (b >= len(text) or not text[b].isalnum())


def locate(stream, page, quote, key, offset):
    """Return ((start, end) of the key in the stream, or None) and how it was found."""
    text = stream.text()
    hits = []
    start = text.find(quote)
    while start >= 0:
        hits.append((start + offset, start + offset + len(key)))
        start = text.find(quote, start + 1)
    on_page = [h for h in hits if stream.pages[h[0]] == page]
    if on_page:
        return on_page[0], 'quotation'
    if len(hits) == 1:
        return hits[0], f'quotation, page {stream.pages[hits[0][0]]} by the page breaks'
    if not hits:
        start = text.find(key)
        while start >= 0:
            if stream.pages[start] == page and is_word_boundary(text, start, start + len(key)):
                return (start, start + len(key)), 'word only'
            start = text.find(key, start + 1)
    return None, 'not found' if not hits else 'quotation not unique'


def tag(raw, stream, span, term_id):
    """Insert the tag; return (new raw text, xml:id)."""
    a, b = span
    start, end = stream.starts[a], stream.ends[b - 1]
    if start is None or end is None:
        raise ValueError('span starts or ends at a break')
    # a word that begins or ends inside an element (e.g. <hi>) takes in the whole element
    while True:
        unclosed, unopened = open_ends(raw[start:end])
        closing = re.match(r'\s*</[\w:.-]+>', raw[end:]) if unclosed else None
        opening = re.search(r'<[\w:.-]+(?:\s[^<>]*)?>\s*$', raw[:start]) if unopened else None
        if closing:
            end += closing.end()
        elif opening:
            start = opening.start()
        else:
            break
    fragment = raw[start:end]
    if not balanced(fragment):
        raise ValueError(f'the passage {fragment!r} crosses element boundaries')
    # already tagged: the word is exactly the content of an existing <term>
    before = re.search(r'<term\b([^>]*)>$', raw[:start])
    if before and raw.startswith('</term>', end):
        attrs = before.group(1)
        existing = re.search(r'xml:id="([^"]+)"', attrs)
        corresp = re.search(r'corresp="([^"]*)"', attrs)
        tokens = corresp.group(1).split() if corresp else []
        new_attrs = attrs
        if '#' + term_id not in tokens:
            tokens.append('#' + term_id)
            new_attrs = re.sub(r'corresp="[^"]*"', f'corresp="{" ".join(tokens)}"', attrs) if corresp \
                else attrs + f' corresp="#{term_id}"'
        xml_id = existing.group(1) if existing else new_id(raw, term_id)
        if not existing:
            new_attrs = f' xml:id="{xml_id}"' + new_attrs
        return raw[:before.start()] + f'<term{new_attrs}>' + raw[start:], xml_id
    for t_start, t_end in stream.terms:
        if t_start < end and start < t_end:
            raise ValueError('the passage overlaps another <term>')
    xml_id = new_id(raw, term_id)
    return raw[:start] + f'<term xml:id="{xml_id}" corresp="#{term_id}">' + fragment + '</term>' + raw[end:], xml_id


def new_id(raw, term_id):
    k = 1
    while f'xml:id="{term_id}-{k}"' in raw:
        k += 1
    return f'{term_id}-{k}'


def quotation(ref):
    """(quotation, marked word, offset of the word in the quotation), all normalised, or None."""
    term = ref.find(TEI + 'term')
    if term is None:
        return None
    pre = ref.text or ''
    for child in ref:
        if child is term:
            break
        pre += ''.join(child.itertext()) + (child.tail or '')
    key = ''.join(term.itertext())
    post = term.tail or ''
    for child in term.itersiblings():
        post += ''.join(child.itertext()) + (child.tail or '')
    full, word = normalise(pre + key + post), normalise(key)
    return full, word, full.find(word, max(0, len(normalise(pre)) - 1))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--root', type=Path, default=REPO / 'encodings')
    parser.add_argument('--dry-run', action='store_true', help='report only, change nothing')
    parser.add_argument('--exclude', nargs='*', default=[], help='target files to leave alone')
    args = parser.parse_args(argv)

    root = args.root.resolve()
    index = root / 'indices' / 'terms.xml'
    index_raw = index.read_text(encoding='utf-8')
    tree = etree.fromstring(index_raw.encode('utf-8'))
    excluded = {(root / e).resolve() for e in args.exclude}

    files = {}  # path -> raw text
    index_lines = index_raw.split('\n')
    counts = {'tagged': 0, 'done': 0, 'excluded': 0, 'no quotation': 0, 'failed': 0}
    for item in tree.iter(TEI + 'item'):
        term_id = item.get(XML_ID)
        for ref in item.iter(TEI + 'ref'):
            target = ref.get('target') or ''
            if not target or '#' in target:
                counts['done'] += 1
                continue
            path = (index.parent / target).resolve()
            q = quotation(ref)
            if q is None:
                counts['no quotation'] += 1
                continue
            if path in excluded:
                counts['excluded'] += 1
                continue
            if not path.is_file():
                print(f'line {ref.sourceline}: {target} does not exist')
                counts['failed'] += 1
                continue
            raw = files.get(path) or path.read_text(encoding='utf-8')
            stream = Stream(raw)
            page = int(ref.get('n')) if (ref.get('n') or '').isdigit() else None
            span, how = locate(stream, page, *q)
            label = f'{term_id} p. {page} in {target}: “{q[1]}”'
            if span is None:
                print(f'not tagged: {label} ({how})')
                counts['failed'] += 1
                continue
            try:
                raw, xml_id = tag(raw, stream, span, term_id)
            except ValueError as error:
                print(f'not tagged: {label} ({error})')
                counts['failed'] += 1
                continue
            files[path] = raw
            line = ref.sourceline - 1
            old = f'target="{target}"'
            if index_lines[line].count(old) != 1:
                print(f'line {ref.sourceline}: cannot update the target (put each ref on a line of its own)')
                counts['failed'] += 1
                continue
            index_lines[line] = index_lines[line].replace(old, f'target="{target}#{xml_id}"')
            if how != 'quotation':
                print(f'tagged ({how}): {label}')
            counts['tagged'] += 1

    if not args.dry_run:
        for path, raw in files.items():
            path.write_text(raw, encoding='utf-8')
        if counts['tagged']:
            index.write_text('\n'.join(index_lines), encoding='utf-8')
    print(', '.join(f'{v} {k}' for k, v in counts.items()) + (' (dry run)' if args.dry_run else ''))
    return 1 if counts['failed'] else 0


if __name__ == '__main__':
    sys.exit(main())
