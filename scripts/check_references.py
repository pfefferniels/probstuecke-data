#!/usr/bin/env python3
"""Check the internal pointers of the TEI encodings of Probstücke Digital.

For every TEI file under encodings/ the script checks that

  1. @facs        '#id' tokens name an xml:id in the same file
                  (a <zone> or <surface> of its <facsimile>);
  2. ref/@target  '#id' tokens name an xml:id in the same file or in an MEI
                  file the TEI file embeds via notatedMusic//ptr/@target
                  (these are the elements the website highlights); other
                  relative tokens must name existing files;
  3. ptr/@target  file references name existing files;
  4. @corresp     '#ed_...' tokens name an xml:id in encodings/indices/*.xml.

Problems are printed grouped by file. The exit status is 0 if there are none
(apart from allowlisted ones), 1 if there are problems or stale allowlist
entries, and 2 on usage errors.

Allowlist (default: scripts/check_references.allow): one entry per line,

    encodings/<path>.xml: <pointer>

where <pointer> is the token exactly as it appears in the attribute (e.g.
'#m-512'). An entry covers every occurrence of that token in that file. Lines
starting with '#' are comments; every entry should be explained by one. An
entry that no longer matches a problem is reported as stale, so that the list
shrinks as cases get fixed.

Usage:
    python3 scripts/check_references.py [--root ENCODINGS_DIR] [--allow FILE]
"""

import argparse
import difflib
import re
import sys
from collections import defaultdict
from pathlib import Path

from lxml import etree

TEI = '{http://www.tei-c.org/ns/1.0}'
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'
URI_SCHEME = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*:')

REPO = Path(__file__).resolve().parent.parent
PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True)


class Problem:
    __slots__ = ('path', 'line', 'kind', 'token', 'message')

    def __init__(self, path, line, kind, token, message):
        self.path, self.line, self.kind, self.token, self.message = path, line, kind, token, message


class Documents:
    """Parses each XML file at most once and caches its xml:ids."""

    def __init__(self):
        self._trees = {}
        self._ids = {}

    def tree(self, path):
        path = path.resolve()
        if path not in self._trees:
            try:
                self._trees[path] = etree.parse(str(path), PARSER)
            except (etree.XMLSyntaxError, OSError) as exc:
                self._trees[path] = exc
        return self._trees[path]

    def ids(self, path):
        path = path.resolve()
        if path not in self._ids:
            tree = self.tree(path)
            if isinstance(tree, Exception):
                self._ids[path] = set()
            else:
                self._ids[path] = {el.get(XML_ID) for el in tree.iter()
                                   if isinstance(el.tag, str) and el.get(XML_ID)}
        return self._ids[path]


def classify(token):
    """Return 'local', 'external', 'site' or 'file' for a pointer token."""
    if token.startswith('#'):
        return 'local'
    if URI_SCHEME.match(token):
        return 'external'
    if token.startswith('/'):
        return 'site'  # a route of the website, e.g. /guidelines/
    return 'file'


def split_file_token(token):
    path, _, fragment = token.partition('#')
    return path, fragment


def tei_elements(root, local_name=None):
    for el in root.iter(TEI + local_name if local_name else etree.Element):
        if isinstance(el.tag, str) and el.tag.startswith(TEI):
            yield el


def check_file_token(docs, base_dir, token):
    """Check a relative 'file' or 'file#id' token. Return an error message or None."""
    file_part, fragment = split_file_token(token)
    target = base_dir / file_part
    if not target.is_file():
        return f'file {file_part!r} does not exist'
    if fragment and target.suffix == '.xml' and fragment not in docs.ids(target):
        return f'no xml:id {fragment!r} in {file_part}'
    return None


def check_tei(docs, path, rel, root, index_ids):
    problems = []
    base_dir = path.parent
    local_ids = docs.ids(path)

    def report(el, kind, token, message):
        problems.append(Problem(rel, el.sourceline, kind, token, message))

    # MEI files embedded via notatedMusic//ptr (as the website loads them)
    embedded = []
    for music in tei_elements(root, 'notatedMusic'):
        for ptr in music.iter(TEI + 'ptr'):
            for token in (ptr.get('target') or '').split():
                if classify(token) == 'file':
                    file_part, _ = split_file_token(token)
                    target = (base_dir / file_part).resolve()
                    if target.is_file() and target.suffix == '.xml' and target not in embedded:
                        embedded.append(target)
    embedded_ids = set()
    for target in embedded:
        embedded_ids |= docs.ids(target)
    in_scope = local_ids | embedded_ids

    def other_holders(identifier):
        """Sibling XML files that hold the ID but are not embedded."""
        holders = []
        for candidate in sorted(base_dir.glob('*.xml')):
            if candidate.resolve() in (path.resolve(), *embedded):
                continue
            if identifier in docs.ids(candidate):
                holders.append(candidate.name)
        return holders

    for el in tei_elements(root):
        # 1. @facs
        for token in (el.get('facs') or '').split():
            kind = classify(token)
            if kind == 'local':
                if token[1:] not in local_ids:
                    message = f'no <zone>/<surface> with xml:id {token[1:]!r} in this file'
                    close = difflib.get_close_matches(token[1:], [i for i in local_ids if i.startswith('facs')], n=1, cutoff=0.9)
                    if close:
                        message += f' (did you mean #{close[0]}?)'
                    report(el, '@facs', token, message)
            elif kind == 'file':
                if token in local_ids:
                    report(el, '@facs', token, f"missing '#': {token!r} is an xml:id in this file, write '#{token}'")
                else:
                    error = check_file_token(docs, base_dir, token)
                    if error:
                        report(el, '@facs', token, f"neither a '#id' nor an existing file: {error}")

        # 4. @corresp="#ed_..."
        for token in (el.get('corresp') or '').split():
            if token.startswith('#ed_') and token[1:] not in index_ids:
                report(el, '@corresp', token, f'no entry {token[1:]!r} in encodings/indices/*.xml')

    # 2. ref/@target
    for ref in tei_elements(root, 'ref'):
        for token in (ref.get('target') or '').split():
            kind = classify(token)
            if kind == 'local':
                if token[1:] not in in_scope:
                    message = f'no xml:id {token[1:]!r} in this file or its embedded MEI'
                    if embedded:
                        message += ' (' + ', '.join(t.name for t in embedded) + ')'
                    holders = other_holders(token[1:])
                    if holders:
                        message += f"; it exists in {', '.join(holders)}, which this file does not embed via notatedMusic"
                    report(ref, 'ref/@target', token, message)
            elif kind == 'file':
                if token in in_scope:
                    report(ref, 'ref/@target', token, f"missing '#': {token!r} is an xml:id in scope, write '#{token}'")
                else:
                    error = check_file_token(docs, base_dir, token)
                    if error:
                        report(ref, 'ref/@target', token, error)

    # 3. ptr/@target
    for ptr in tei_elements(root, 'ptr'):
        for token in (ptr.get('target') or '').split():
            kind = classify(token)
            if kind == 'file':
                error = check_file_token(docs, base_dir, token)
                if error:
                    report(ptr, 'ptr/@target', token, error)
            elif kind == 'local' and token[1:] not in local_ids:
                report(ptr, 'ptr/@target', token, f'no xml:id {token[1:]!r} in this file')

    return problems


def read_allowlist(path):
    entries = {}
    errors = []
    if not path.is_file():
        return entries, errors
    for number, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        file_part, sep, rest = line.partition(': ')
        fields = rest.split()
        if not sep or not fields or (len(fields) > 1 and not fields[1].startswith('#')):
            errors.append(f'{path.name}:{number}: expected "<path>: <pointer>", got {raw!r}')
            continue
        entries[(file_part.strip(), fields[0])] = number
    return entries, errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--root', type=Path, default=REPO / 'encodings',
                        help='encodings directory to check (default: %(default)s)')
    parser.add_argument('--allow', type=Path, default=REPO / 'scripts' / 'check_references.allow',
                        help='allowlist file (default: %(default)s)')
    args = parser.parse_args(argv)

    root_dir = args.root.resolve()
    if not root_dir.is_dir():
        parser.error(f'{args.root} is not a directory')
    base = root_dir.parent  # paths are reported relative to this, e.g. encodings/1/...

    docs = Documents()
    index_ids = set()
    for index in sorted((root_dir / 'indices').glob('*.xml')):
        index_ids |= docs.ids(index)

    problems = []
    tei_files = 0
    for path in sorted(root_dir.rglob('*.xml')):
        rel = path.relative_to(base).as_posix()
        tree = docs.tree(path)
        if isinstance(tree, Exception):
            problems.append(Problem(rel, 0, 'parse', '-', f'not well-formed: {tree}'))
            continue
        root = tree.getroot()
        if root.tag != TEI + 'TEI':
            continue
        tei_files += 1
        problems.extend(check_tei(docs, path, rel, root, index_ids))

    allow, allow_errors = read_allowlist(args.allow)
    used = set()
    open_problems = []
    allowed = 0
    for problem in problems:
        key = (problem.path, problem.token)
        if key in allow:
            used.add(key)
            allowed += 1
        else:
            open_problems.append(problem)
    stale = sorted((number, key) for key, number in allow.items() if key not in used)

    by_file = defaultdict(list)
    for problem in open_problems:
        by_file[problem.path].append(problem)
    for rel in sorted(by_file):
        print(rel)
        for p in sorted(by_file[rel], key=lambda p: (p.line or 0, p.kind, p.token)):
            print(f'  line {p.line:<5} {p.kind:<12} {p.token}  {p.message}')
        print()

    for message in allow_errors:
        print(message)
    for number, (rel, token) in stale:
        print(f'{args.allow.name}:{number}: stale entry "{rel}: {token}" matches no problem; remove it')

    files_with_problems = len(by_file)
    print(f'{tei_files} TEI files checked: {len(open_problems)} problem(s) in {files_with_problems} file(s), '
          f'{allowed} allowlisted, {len(stale)} stale allowlist entr{"y" if len(stale) == 1 else "ies"}.')
    return 1 if open_problems or stale or allow_errors else 0


if __name__ == '__main__':
    sys.exit(main())
