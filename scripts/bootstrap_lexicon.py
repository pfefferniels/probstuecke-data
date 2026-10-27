#!/usr/bin/env python3
"""Bootstrap normalisation/lexicon.tsv from one run of the DTA CAB web service.

The website shows Mattheson's commentary in modernised spelling. Words are
looked up in normalisation/lexicon.tsv; words that are not listed only get the
character rules (ſ → s, aͤ → ä, …). This script started the lexicon: it sends
every Fraktur transcription once to CAB (Deutsches Textarchiv,
https://www.deutschestextarchiv.de/doku/software#cab), collects each original
token (CAB's @t) with the normalisation CAB chose (moot/@word), and keeps the
forms where CAB does more than the character rules.

The lexicon is maintained by hand afterwards. Run the script again only to get
CAB's suggestions for new texts; it refuses to overwrite an existing file, so
write them elsewhere and compare:

    python3 scripts/bootstrap_lexicon.py --out /tmp/suggestions.tsv

The editors' notes (<note type="editorial">) are in modern spelling and are
not looked at. CAB suggestions are dropped (the character rules apply instead)
when:
- the token only occurs in names (<persName>), in <foreign> or under a
  non-German xml:lang;
- the token contains a music sign (♭ ♯ ♮) or no letter at all;
- CAB only adds or removes punctuation, or only drops accents (Traité → Traite).
A capital letter that CAB adds to a lower-case word (a guess at the word
class) is not taken over. CAB marks contractions with _ (ers → er_es); they are
written with a space.

Columns of the lexicon:
    orig    the token as transcribed (with ſ, combining e, …)
    norm    the modern form shown on the website
    status  cab: CAB's suggestion, not yet reviewed; checked: reviewed and kept;
            edited: changed by the editors
    count   occurrences in the transcriptions when the lexicon was created
    note    other normalisations CAB chose in some contexts, or a comment
"""

import argparse
import collections
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
ENCODINGS = ROOT / 'encodings'
CAB_URL = ('https://www.deutschestextarchiv.de/public/cab/query'
           '?a=default&fmt=xml&clean=1&pretty=1&raw=1&qname=qd&file=comments.xml')
TEI = '{http://www.tei-c.org/ns/1.0}'
XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'


def character_rules(token: str) -> str:
    """Rules the website applies to tokens that are not in the lexicon."""
    token = token.replace('ſ', 's')
    for base, umlaut in (('a', 'ä'), ('o', 'ö'), ('u', 'ü'), ('A', 'Ä'), ('O', 'Ö'), ('U', 'Ü')):
        token = token.replace(base + 'ͤ', umlaut)
    # the nasal bar abbreviates a doubled consonant or a following n: kom̃en, genañten, Sachẽ
    token = token.replace('ñ', 'nn').replace('ẽ', 'en')
    for base, expanded in (('m', 'mm'), ('n', 'nn'), ('e', 'en')):
        token = token.replace(base + '\u0303', expanded)
    return token


def fraktur_files():
    for path in sorted(ENCODINGS.rglob('*.xml')):
        text = path.read_text(encoding='utf-8')
        if '<TEI' in text and '<p>Fraktur</p>' in text:
            yield path, text


def normalise_with_cab(raw: str, attempts: int = 3) -> bytes:
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                CAB_URL, data=raw.encode('utf-8'), method='POST',
                # a form content type makes CAB look for a query parameter instead of the body
                headers={'Content-Type': 'text/plain; charset=UTF-8'})
            with urllib.request.urlopen(request, timeout=180) as response:
                body = response.read()
            if b'<TEI' in body:
                return body
            raise ValueError('response is not a TEI document')
        except Exception as error:  # noqa: BLE001 – retry on any failure
            if attempt == attempts - 1:
                raise
            print(f'  retrying after error: {error}', file=sys.stderr)
            time.sleep(5)


def plain_spelling(element) -> bool:
    """True in names and foreign languages, where only the character rules apply."""
    for ancestor in element.iterancestors():
        if ancestor.tag in (TEI + 'foreign', TEI + 'persName'):
            return True
        lang = ancestor.get(XML_LANG)
        if lang is not None:
            return not lang.startswith('de')
        # a footnote in a foreign quotation is in German unless it says otherwise
        if ancestor.tag in (TEI + 'note', TEI + 'fw'):
            return False
    return False


def editorial(element) -> bool:
    return any(a.tag == TEI + 'note' and a.get('type') == 'editorial' for a in element.iterancestors())


def strip_accents(token: str) -> str:
    """Removes the accents of French and Italian letters (é → e), not the German umlauts
    or the nasal stroke (etwañ)."""
    def strip(c):
        if c in 'äöüÄÖÜ':
            return c
        return ''.join(d for d in unicodedata.normalize('NFD', c) if d == '\u0303' or not unicodedata.combining(d))
    return ''.join(c if c == '\u0364' else strip(c) for c in unicodedata.normalize('NFC', token))


def keep_suggestion(orig: str, norm: str, only_plain: bool):
    """The suggestion to store for orig, or None if the character rules apply."""
    if only_plain or any(sign in orig for sign in '♭♯♮') or not any(c.isalpha() for c in orig):
        return None
    if orig[:1].islower() and norm[:1].isupper():
        norm = norm[:1].lower() + norm[1:]
    norm = norm.replace('_', ' ')
    ruled = character_rules(orig)
    # letters and their marks (the nasal stroke of dariñ), without punctuation
    strip = lambda s: ''.join(c for c in s if c.isalnum() or unicodedata.combining(c))  # noqa: E731
    if norm == ruled or strip(norm) == strip(ruled) or norm == strip_accents(ruled):
        return None
    return norm


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--out', default=str(ROOT / 'normalisation' / 'lexicon.tsv'))
    parser.add_argument('--cache', help='directory to keep (and reuse) the CAB responses')
    args = parser.parse_args()
    cache = Path(args.cache) if args.cache else None
    out = Path(args.out)
    if out.exists():
        sys.exit(f'{out} exists; it is maintained by hand. Use --out to write suggestions elsewhere.')

    norms = collections.defaultdict(collections.Counter)
    plain = collections.Counter()
    for path, raw in fraktur_files():
        cached = cache / path.relative_to(ENCODINGS) if cache else None
        if cached and cached.exists():
            body = cached.read_bytes()
        else:
            print(f'CAB: {path.relative_to(ROOT)}', file=sys.stderr)
            body = normalise_with_cab(raw)
            if cached:
                cached.parent.mkdir(parents=True, exist_ok=True)
                cached.write_bytes(body)
        doc = etree.fromstring(body)
        # only the text, not the header
        text = doc.find(f'{TEI}text')
        for w in text.iter(f'{TEI}w'):
            moot = w.find(f'{TEI}moot')
            orig = w.get('t')
            if moot is None or orig is None:
                continue  # continuation of a split token: the first part carries the normalisation
            if editorial(w):
                continue
            norms[orig][moot.get('word', '')] += 1
            if plain_spelling(w):
                plain[orig] += 1

    rows = []
    for orig, counts in norms.items():
        total = sum(counts.values())
        norm = keep_suggestion(orig, counts.most_common(1)[0][0], plain[orig] == total)
        if norm is None:
            continue
        other = ' '.join(f'{n}:{c}' for n, c in counts.most_common()[1:])
        rows.append((orig, norm, 'cab', total, f'CAB also: {other}' if other else ''))

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8') as f:
        f.write('orig\tnorm\tstatus\tcount\tnote\n')
        for row in sorted(rows, key=lambda r: (-r[3], r[0])):
            f.write('\t'.join(map(str, row)) + '\n')
    print(f'{len(rows)} of {len(norms)} forms need an entry; written to {out}', file=sys.stderr)


if __name__ == '__main__':
    main()
