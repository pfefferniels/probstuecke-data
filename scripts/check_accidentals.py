#!/usr/bin/env python3
"""Check the written accidentals of MEI encodings against the edition's convention.

The edition shows every score in two views (see the guidelines and data issue
#3): the diplomatic view shows what the print shows, the modernised view
follows modern accidental rules. Both come from one encoding:

  <accid accid="s"/>                      printed, and needed in modern notation
  <orig><accid accid="s"/></orig>         printed, but superfluous in modern
                                          notation (hidden in the modernised view)
  <supplied resp="#pfeffer"><reg>         not printed, but needed in modern
    <accid accid="s"/>                    notation (hidden in the diplomatic
  </reg></supplied>                       view)
  ... <accid accid="n" func="caution"/>   a cautionary accidental: supplied as
                                          above, or printed (a printed one that
                                          the rules do not ask for may be kept
                                          as a courtesy with @func="caution"
                                          instead of being put into <orig>)
  <choice><orig><accid accid="f"/></orig> a printed sign that modern notation
    <reg resp="#pfeffer"><accid           replaces, e.g. the old flat that
    accid="n"/></reg></choice>            cancels a sharp

The sounding pitch is @accid.ges (on the note or its accid), else the written
accidental, else that of the last note of the same pitch and octave in the bar
that has one of them, else the printed (not the modern) key signature. The
script applies modern rules to it and reports every note whose encoded
accidentals do not fit:

  * the key signature is the one Verovio draws in the modernised view
    (keySig/@sig, @key.sig or @keysig on scoreDef or staffDef, keySig in a
    layer; a <choice> is read as ./reg): where the print has an old one
    (e.g. a "Dorian" minor signature), the modern one is encoded as
      <choice><orig/><reg resp="#pfeffer"><scoreDef><keySig sig="3f"/>
      </scoreDef></reg></choice>
    at the start of the section; @key.pname/@key.mode are ignored;
  * an accidental holds for the same pitch and octave until the barline, on the
    whole staff (all layers, in time order); a barline cancels it;
  * a note tied from the previous note needs no accidental; an alteration tied
    over the barline does not hold for later notes of the bar;
  * cautionary accidentals (as the full scores have them): a note that has its
    key-signature (or current) value gets one
      - if it is the first note of its letter in the bar and the previous bar
        left that letter altered differently, in any octave;
      - if another octave of the same letter was altered differently earlier
        in the bar (on the first note of its pitch and octave after that);
      - if the same pitch was tied over the barline with another alteration.
    A printed accidental that repeats one of another layer of the same staff
    is accepted as a courtesy, too, and so is a supplied cautionary one on a
    note tied over the barline.

Categories of reports:

  error     missing required accidental; a required accidental only in <orig>;
            the modernised view shows a different accidental; an editorial
            accidental (<reg>, <corr>, <add>) outside <supplied>, which the
            diplomatic view would show
  warning   printed accidental that is superfluous but not in <orig> (and not
            kept with @func="caution"); supplied accidental that the rules do
            not ask for; a written accidental that contradicts @accid.ges
  caution   missing cautionary accidental (a suggestion: the full scores have
            about three quarters of the cautionary accidentals these rules ask for)

Where an <app> holds notes, every reading (by @source) is checked. A <choice>
is read as the modernised view reads it (./reg, else the first child).

The rules were derived from the full scores (encodings/*/mattheson/score.xml),
whose accidentals the editors had already corrected; there, the errors the
script reports are encoding mistakes (e.g. a wrong @accid.ges). It does not
check the pitch itself: a note without @accid.ges and without a written
accidental is taken to sound as the modern rules read it.

Allowlist (default: scripts/check_accidentals.allow): one entry per line,

    encodings/<path>.xml: <xml:id of the note>
    encodings/<path>.xml: *

An entry covers every report on that note, or with * on every note of the
file. Lines starting with '#' are
comments; every entry should be explained by one. Entries that no longer match
a report are reported as stale (when their file is checked).

Usage:
    python3 scripts/check_accidentals.py                    # all MEI files under encodings/
    python3 scripts/check_accidentals.py FILE...            # some files
    python3 scripts/check_accidentals.py --summary [FILE...] # counts only
    python3 scripts/check_accidentals.py --level error ...  # errors only

Exit status: 1 if there is a report at or above --fail-level (default:
caution, i.e. any report), a stale allowlist entry or a malformed one; 0
otherwise.
"""

import argparse
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

from lxml import etree

MEI = '{http://www.music-encoding.org/ns/mei}'
XML_ID = '{http://www.w3.org/XML/1998/namespace}id'
PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=True)

ALTER = {'n': 0, 's': 1, 'f': -1, 'x': 2, 'ss': 2, 'ff': -2, 'ns': 1, 'nf': -1, 'xs': 3, 'ts': 3, 'tf': -3}
SIGN = {0: 'n', 1: 's', -1: 'f', 2: 'x', -2: 'ff', 3: 'xs', -3: 'tf'}
DUR = {'maxima': 32, 'long': 16, 'breve': 8, '1': 4, '2': 2, '4': 1, '8': Fraction(1, 2), '16': Fraction(1, 4),
       '32': Fraction(1, 8), '64': Fraction(1, 16), '128': Fraction(1, 32), '256': Fraction(1, 64)}
# containers whose content is read through
TRANSPARENT = {'beam', 'graceGrp', 'bTrem', 'fTrem', 'ligature', 'lem', 'rdg', 'orig', 'reg', 'supplied', 'add',
               'corr', 'sic', 'unclear', 'damage', 'restore', 'del', 'expan', 'abbr', 'subst'}
EDITORIAL = {'reg', 'corr', 'add'}
LEVELS = ('caution', 'warning', 'error')
REPO = Path(__file__).resolve().parent.parent


def localname(el):
    return etree.QName(el).localname if isinstance(el.tag, str) else None


def key_from_sig(sig):
    """'2f' -> {'b': -1, 'e': -1}; '0' or None -> {}."""
    if not sig or not sig[:-1].isdigit():
        return {}
    n, acc = int(sig[:-1]), sig[-1]
    if acc == 's':
        return {p: 1 for p in 'fcgdaeb'[:n]}
    if acc == 'f':
        return {p: -1 for p in 'beadgcf'[:n]}
    return {}


def duration(el, scale):
    if el.get('grace') or el.get('dur') is None:
        return Fraction(0)
    base = Fraction(DUR.get(el.get('dur'), 0))
    dots = int(el.get('dots') or 0) + len(el.findall(MEI + 'dot'))
    total, add = base, base
    for _ in range(dots):
        add /= 2
        total += add
    return total * scale


class Accid:
    """A written accidental of a note: value, @func, and how it is wrapped."""
    __slots__ = ('value', 'func', 'kind', 'el', 'wrappers')

    def __init__(self, value, func, kind, el, wrappers):
        self.value, self.func, self.kind, self.el, self.wrappers = value, func, kind, el, wrappers

    @property
    def alter(self):
        return ALTER.get(self.value)


class Note:
    """A note with its written accidentals.

    The views are those of the website: Verovio takes ./orig (diplomatic) or
    ./reg (modernised) of a <choice>, else its first child; CSS hides accids in
    <supplied> in the diplomatic view and accids in <orig> in the modernised
    view. Accordingly an accid is of the kind 'plain' (shown in both views),
    'orig' (diplomatic view only), 'supplied' (modernised view only) or
    'editorial' (in <reg>, <corr> or <add> but shown in both views).
    """

    def __init__(self, el, reading=None):
        self.el = el
        self.pname, self.oct = el.get('pname'), el.get('oct')
        self.accids = []
        self.ges = el.get('accid.ges')
        if el.get('accid'):
            self.accids.append(Accid(el.get('accid'), None, 'plain', el, ()))
        reading = reading or Reading()
        for a in el.iter(MEI + 'accid'):
            path, p, child = [], a.getparent(), a       # (ancestor, its child towards the accid)
            while p is not el:
                path.append((p, child))
                child, p = p, p.getparent()
            if any(localname(p) == 'app' and reading.app(p) is not c for p, c in path):
                continue        # another reading of an <app> in the note
            wrappers = tuple(localname(p) for p, c in path)
            choices = [(p, c) for p, c in path if localname(p) == 'choice']
            diplomatic = 'supplied' not in wrappers and all(pick(p, 'orig') is c for p, c in choices)
            modern = 'orig' not in wrappers and all(pick(p, 'reg') is c for p, c in choices)
            if diplomatic and modern:
                kind = 'editorial' if EDITORIAL & set(wrappers) else 'plain'
            elif diplomatic:
                kind = 'orig'
            elif modern:
                kind = 'supplied'
            else:
                continue
            if a.get('accid'):
                self.accids.append(Accid(a.get('accid'), a.get('func'), kind, a, wrappers))
            if a.get('accid.ges') and self.ges is None:
                self.ges = a.get('accid.ges')

    @property
    def printed(self):
        return [a for a in self.accids if a.kind in ('plain', 'orig', 'editorial')]

    @property
    def modern(self):
        return [a for a in self.accids if a.kind != 'orig']

    def written_alter(self):
        for kinds in (('plain', 'editorial'), ('supplied',), ('orig',)):
            for a in self.accids:
                if a.kind in kinds and a.alter is not None:
                    return a.alter
        return None


class Result:
    """What the rules ask for one note in one reading."""
    __slots__ = ('note', 'alter', 'need', 'reasons', 'tied', 'measure', 'staff', 'soft')

    def __init__(self, note, alter, need, reasons, tied, measure, staff, soft):
        self.note, self.alter, self.need, self.reasons = note, alter, need, reasons
        self.tied, self.measure, self.staff, self.soft = tied, measure, staff, soft


def pick(choice, name):
    """The child of a <choice> that Verovio renders for choiceXPathQuery ./name."""
    kids = [k for k in choice if isinstance(k.tag, str)]
    for k in kids:
        if localname(k) == name:
            return k
    return kids[0] if kids else None


class Reading:
    """Which child of app/choice to follow (choice: as the modernised view)."""

    def __init__(self, source=None):
        self.source = source

    def app(self, app):
        kids = [k for k in app if localname(k) in ('lem', 'rdg')]
        if self.source:
            for k in kids:
                if self.source in (k.get('source') or '').split():
                    return k
        for k in kids:
            if localname(k) == 'lem':
                return k
        return kids[0] if kids else None

    @staticmethod
    def choice(choice):
        return pick(choice, 'reg')


def layer_events(el, t, scale, out, reading, chord=None):
    """Append (onset, element, chord) for notes and keySigs; return the new time."""
    for ch in el:
        tag = localname(ch)
        if tag is None:
            continue
        if tag == 'note':
            out.append((t, ch, chord))
            if chord is None:
                t += duration(ch, scale)
        elif tag == 'chord':
            layer_events(ch, t, scale, out, reading, chord=ch)
            t += duration(ch, scale)
        elif tag in ('rest', 'space'):
            t += duration(ch, scale)
        elif tag in ('mRest', 'mSpace', 'multiRest', 'mRpt', 'mRpt2', 'beatRpt', 'halfmRpt'):
            t += Fraction(10000)
        elif tag == 'tuplet':
            num, numbase = int(ch.get('num') or 3), int(ch.get('numbase') or 2)
            t = layer_events(ch, t, scale * Fraction(numbase, num), out, reading, chord)
        elif tag == 'app':
            k = reading.app(ch)
            if k is not None:
                t = layer_events(k, t, scale, out, reading, chord)
        elif tag == 'choice':
            k = reading.choice(ch)
            if k is not None:
                t = layer_events(k, t, scale, out, reading, chord)
        elif tag in TRANSPARENT:
            t = layer_events(ch, t, scale, out, reading, chord)
        elif tag == 'keySig':
            out.append((t, ch, None))
    return t


def walk_score(score, reading):
    """Yield (element, view) for scoreDef and measure elements in reading order.

    view is 'both', or 'modern' / 'diplomatic' for a scoreDef in a branch of a
    <choice> that only that view renders (e.g. a modern key signature).
    """
    def walk(el, view):
        for ch in el:
            tag = localname(ch)
            if tag in ('scoreDef', 'measure'):
                if tag == 'scoreDef' or view != 'diplomatic':
                    yield ch, view
            elif tag in ('section', 'ending', 'lem', 'rdg') or tag in TRANSPARENT:
                yield from walk(ch, view)
            elif tag == 'app':
                k = reading.app(ch)
                if k is not None:
                    yield from walk(k, view)
            elif tag == 'choice':
                modern, diplomatic = pick(ch, 'reg'), pick(ch, 'orig')
                if modern is diplomatic:
                    if modern is not None:
                        yield from walk(modern, view)
                    continue
                if modern is not None and view != 'diplomatic':
                    yield from walk(modern, 'modern')
                if diplomatic is not None and view != 'modern':
                    yield from walk(diplomatic, 'diplomatic')
    yield from walk(score, 'both')


def sig_of(el):
    ks = el.find(MEI + 'keySig')
    if ks is not None and ks.get('sig') is not None:
        return ks.get('sig')
    return el.get('key.sig') or el.get('keysig')


class Keys:
    def __init__(self):
        self.default = {}
        self.staff = {}
        self.defined = set()

    def update(self, score_def):
        sig = sig_of(score_def)
        if sig is not None:
            self.default = key_from_sig(sig)
            self.staff = {n: dict(self.default) for n in self.staff}
        defined = set()
        for sd in score_def.iter(MEI + 'staffDef'):
            n = sd.get('n')
            defined.add(n)
            s = sig_of(sd)
            if s is not None:
                self.staff[n] = key_from_sig(s)
            elif n not in self.staff:
                self.staff[n] = dict(self.default)
        if defined:
            self.defined = defined

    def of(self, n):
        if n in self.staff:
            return dict(self.staff[n])
        if len(self.defined) == 1:     # a staff whose @n has no staffDef
            return dict(self.staff[next(iter(self.defined))])
        return dict(self.default)


def analyse_reading(tree, reading, tie_starts, tie_ends):
    results = []
    for score in tree.iter(MEI + 'score'):
        keys = Keys()           # the key signature of the modernised view
        printed_keys = Keys()   # the printed one, for the pitch of notes without @accid.ges
        prev_state = defaultdict(dict)    # staff -> {(p, o): alteration shown in the previous bar}
        tied_alter = defaultdict(dict)    # staff -> {(p, o): alteration of a note with a tie to the next}
        for el, view in walk_score(score, reading):
            if localname(el) == 'scoreDef':
                if view != 'diplomatic':
                    keys.update(el)
                if view != 'modern':
                    printed_keys.update(el)
                continue
            measure = el
            events = defaultdict(list)
            seq = 0
            for staff in measure.findall(MEI + 'staff'):
                for layer in staff.findall(MEI + 'layer'):
                    out = []
                    layer_events(layer, Fraction(0), Fraction(1), out, reading)
                    for t, e, chord in out:
                        seq += 1
                        n = e.get('staff') or (chord.get('staff') if chord is not None else None) or staff.get('n')
                        events[n].append((t, seq, e, layer.get('n')))
            for n, evs in sorted(events.items()):
                evs.sort(key=lambda x: (x[0], x[1]))
                cur_layer = {}     # (p, o) -> layer of the note that showed the accidental
                key = keys.of(n)
                printed_key = printed_keys.of(n)
                known = {}         # (p, o) -> last explicitly encoded alteration in this bar
                last = prev_state[n]
                cur = {}           # (p, o) -> alteration shown by an accidental in this bar
                seen, seen_letter = set(), set()
                tied_in = {}       # (p, o) -> alteration tied over the barline into this bar
                for t, s, e, layer_n in evs:
                    if localname(e) == 'keySig':
                        key = printed_key = key_from_sig(e.get('sig'))
                        continue
                    note = Note(e, reading)
                    if not note.pname or not note.oct:
                        continue
                    p, po = note.pname, (note.pname, note.oct)
                    state = cur.get(po, key.get(p, 0))
                    if note.ges is not None:
                        alter = ALTER.get(note.ges)
                    else:
                        alter = note.written_alter()
                    is_tie_end = e in tie_ends
                    if alter is None:
                        # no @accid.ges and no sign: the pitch of the last note of this pitch
                        # and octave in the bar with an explicit one, else the printed key
                        alter = known.get(po, printed_key.get(p, 0))
                        if is_tie_end:
                            alter = tied_alter[n].get(po, alter)
                    else:
                        known[po] = alter
                    if e in tie_starts:
                        tied_alter[n][po] = alter
                    if is_tie_end:
                        soft = set()
                        if po not in seen:
                            tied_in.setdefault(po, alter)
                            soft.add('tied over the barline')     # a courtesy accidental is accepted
                        results.append(Result(note, alter, None, [], True, measure, n, soft))
                        continue
                    reasons, soft = [], set()
                    if alter != state:
                        need = 'required'
                    else:
                        need = None
                        if po not in cur:
                            if any(pp == p and alt != alter for (pp, oo), alt in cur.items()):
                                reasons.append('another octave altered earlier in the bar')
                            if p not in seen_letter and last.get(po, alter) != alter:
                                reasons.append('altered in the previous bar')
                            elif p not in seen_letter and any(pp == p and alt != alter
                                                              for (pp, oo), alt in last.items()):
                                reasons.append('altered in another octave in the previous bar')
                            if po not in seen and tied_in.get(po, alter) != alter:
                                reasons.append('tied over the barline with another alteration')
                        if reasons:
                            need = 'caution'
                        # weaker contexts, where a printed or supplied courtesy accidental is accepted
                        if any(pp == p and alt != alter for (pp, oo), alt in last.items()):
                            soft.add('previous bar')
                        if po in cur and cur_layer.get(po) != layer_n:
                            soft.add('other layer')
                    if need:
                        cur[po] = alter
                        cur_layer[po] = layer_n
                    seen.add(po)
                    seen_letter.add(p)
                    results.append(Result(note, alter, need, reasons, False, measure, n, soft))
                prev_state[n] = dict(cur)
            for n in list(prev_state):
                if n not in events:     # a bar without notes on this staff
                    prev_state[n] = {}
    return results


def sources_of(tree):
    out = set()
    for el in tree.iter(MEI + 'lem', MEI + 'rdg'):
        if el.find('.//' + MEI + 'note') is not None:
            out.update((el.get('source') or '').split())
    return sorted(out)


def analyse(path):
    """Return the tree and {note element: [Result, ...]} over every reading."""
    tree = etree.parse(str(path), PARSER)
    by_id = {el.get(XML_ID): el for el in tree.iter(MEI + 'note') if el.get(XML_ID)}
    tie_starts, tie_ends = set(), set()
    for tie in tree.iter(MEI + 'tie'):
        s, e = (tie.get('startid') or '').lstrip('#'), (tie.get('endid') or '').lstrip('#')
        if s in by_id:
            tie_starts.add(by_id[s])
        if e in by_id:
            tie_ends.add(by_id[e])
    for el in tree.iter(MEI + 'note'):
        if el.get('tie') in ('i', 'm'):
            tie_starts.add(el)
        if el.get('tie') in ('m', 't'):
            tie_ends.add(el)
    results = defaultdict(list)
    for source in [None] + sources_of(tree):
        for r in analyse_reading(tree, Reading(source), tie_starts, tie_ends):
            results[r.note.el].append(r)
    return tree, results


class Report:
    __slots__ = ('level', 'code', 'message', 'result')

    def __init__(self, level, code, message, result):
        self.level, self.code, self.message, self.result = level, code, message, result


def judge(r):
    """Compare a note's encoded accidentals with what the rules ask for."""
    note, alter, want = r.note, r.alter, SIGN.get(r.alter, '?')
    modern = note.modern
    reports = []

    def rep(level, code, msg):
        reports.append(Report(level, code, msg, r))

    for a in note.accids:
        if a.kind == 'editorial':
            rep('error', 'editorial-visible', f'editorial accidental {a.value} in <{a.wrappers[0]}> outside '
                f'<supplied> is shown in the diplomatic view')
    if note.ges is not None:
        regularised = any(a.alter == alter for a in modern)
        for a in note.printed:
            # an old sign (e.g. a flat that cancels a sharp) is fine once it is in <orig>
            # and the modernised view shows the right one
            if a.alter is not None and a.alter != alter and not (a.kind == 'orig' and regularised):
                rep('warning', 'pitch', f'printed accidental {a.value} contradicts @accid.ges="{note.ges}"')
    if r.need == 'required':
        match = [a for a in modern if a.alter == alter]
        if not match:
            if any(a.kind == 'orig' and a.alter == alter for a in note.accids):
                rep('error', 'needed-in-orig', f'needed accidental {want} is in <orig>')
            elif modern:
                rep('error', 'wrong', f'needs {want}, the modernised view shows '
                    f'{",".join(a.value for a in modern)}')
            else:
                rep('error', 'missing', f'missing accidental {want}')
        elif all(a.func == 'caution' for a in match):
            rep('warning', 'caution-func', f'required accidental {want} has @func="caution"')
        if match:
            for a in modern:
                if a.alter != alter:
                    rep('error', 'wrong', f'modernised view also shows {a.value}')
    elif r.need == 'caution':
        match = [a for a in modern if a.alter == alter]
        if not match:
            if modern:
                rep('error', 'wrong', f'cautionary {want} expected, the modernised view shows '
                    f'{",".join(a.value for a in modern)}')
            else:
                rep('caution', 'caution', f'missing cautionary {want} ({"; ".join(r.reasons)})')
        elif any(a.kind == 'supplied' and a.func != 'caution' for a in match):
            rep('warning', 'caution-func', f'supplied cautionary {want} lacks @func="caution"')
    else:
        what = 'tied note' if r.tied else 'not needed'
        for a in modern:
            if a.kind in ('plain', 'editorial') and a.func != 'caution' and 'other layer' not in r.soft:
                if a.alter is not None and a.alter != alter:
                    rep('error', 'wrong', f'printed {a.value} differs from the pitch ({want}) and is not in <orig>')
                else:
                    rep('warning', 'superfluous', f'printed {a.value} ({what}) is not in <orig>')
            elif a.kind == 'supplied' and a.alter is not None and a.alter != alter:
                rep('error', 'wrong', f'supplied {a.value} differs from the pitch ({want})')
            elif a.kind == 'supplied' and not (a.func == 'caution' and r.soft):
                rep('warning', 'supplied-unneeded', f'supplied {a.value} ({what})')
    return reports


def check(path):
    """Return the reports for one file, one per note and problem."""
    tree, results = analyse(path)
    reports = {}
    for el, rs in results.items():
        for r in rs:
            for rep in judge(r):
                reports.setdefault((el, rep.code, rep.message), rep)
    return sorted(reports.values(), key=lambda rep: rep.result.note.el.sourceline)


def describe(rep):
    r = rep.result
    m = r.measure
    label = m.get('label') or m.get('n') or m.get('corresp') or m.get(XML_ID) or '?'
    el = r.note.el
    ident = f' {el.get(XML_ID)}' if el.get(XML_ID) else ''
    return f'line {el.sourceline}: bar {label}, staff {r.staff}, {r.note.pname}{r.note.oct}{ident}: {rep.message}'


def read_allowlist(path):
    """Return ({(file, xml:id): line number}, [errors])."""
    entries, errors = {}, []
    if not path.is_file():
        return entries, errors
    for number, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        file_part, sep, rest = line.partition(': ')
        fields = rest.split()
        if not sep or not fields or (len(fields) > 1 and not fields[1].startswith('#')):
            errors.append(f'{path.name}:{number}: expected "<path>: <xml:id>", got {raw!r}')
            continue
        entries[(file_part.strip(), fields[0])] = number
    return entries, errors


def mei_files(root):
    """All MEI documents under root."""
    out = []
    for path in sorted(root.rglob('*.xml')):
        try:
            for _, el in etree.iterparse(str(path), events=('start',), no_network=True, resolve_entities=False):
                if el.tag == MEI + 'mei':
                    out.append(path)
                break
        except etree.XMLSyntaxError:
            continue
    return out


def relative(path):
    try:
        return Path(path).resolve().relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('files', nargs='*', type=Path, help='MEI files (default: all under encodings/)')
    ap.add_argument('--level', choices=LEVELS, default='caution', help='lowest level to report')
    ap.add_argument('--fail-level', choices=LEVELS, default='caution')
    ap.add_argument('--summary', action='store_true', help='print counts per file and category only')
    ap.add_argument('--allow', type=Path, default=REPO / 'scripts' / 'check_accidentals.allow',
                    help='allowlist file (default: %(default)s)')
    args = ap.parse_args(argv)
    files = args.files or mei_files(REPO / 'encodings')
    allow, allow_errors = read_allowlist(args.allow)
    lowest = LEVELS.index(args.level)
    failed = bool(allow_errors)
    totals = Counter()
    used = set()
    checked = set()
    for path in files:
        rel = relative(path)
        checked.add(rel)
        reports = []
        for rep in check(path):
            key = (rel, rep.result.note.el.get(XML_ID))
            if (rel, '*') in allow:
                used.add((rel, '*'))
            elif key in allow:
                used.add(key)
            elif LEVELS.index(rep.level) >= lowest:
                reports.append(rep)
        counts = Counter(rep.level for rep in reports)
        totals.update(counts)
        failed |= any(LEVELS.index(rep.level) >= LEVELS.index(args.fail_level) for rep in reports)
        if args.summary:
            if reports:
                print(f'{rel}: ' + ', '.join(f'{counts[lv]} {lv}' for lv in reversed(LEVELS) if counts[lv]))
            continue
        for rep in reports:
            print(f'{rel}: {rep.level}: {describe(rep)}')
    for message in allow_errors:
        print(message)
    stale = sorted((number, key) for key, number in allow.items() if key[0] in checked and key not in used)
    for number, (rel, ident) in stale:
        print(f'{args.allow.name}:{number}: stale entry "{rel}: {ident}" matches no report; remove it')
    failed |= bool(stale)
    print(', '.join(f'{totals[lv]} {lv}' for lv in reversed(LEVELS)) + f' in {len(files)} MEI files, '
          f'{len(used)} allowlist entries used, {len(stale)} stale.', file=sys.stderr)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
