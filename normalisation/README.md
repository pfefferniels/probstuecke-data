# Normalisation

The website shows the 1719 and 1731 commentaries in modernised spelling, with the original spelling on hover. The diplomatic transcriptions in `encodings/` are not changed; the modern forms come from this folder.

## How a word is normalised

1. Text in `<g>` (music symbols), in the TEI header and in the editors' notes (`<note type="editorial">`) is left as it is.
2. Names (`<persName>`) and words inside `<foreign>` or under a non-German `xml:lang` only get the character rules (see 4). A footnote inside a foreign quotation is German unless it says otherwise.
3. A word listed in [`lexicon.tsv`](lexicon.tsv) gets its `norm`.
4. Any other word gets the character rules: `ſ` → `s`; `a`, `o`, `u` with combining e (U+0364) → `ä`, `ö`, `ü`; and the nasal bar is expanded: `m̃` → `mm`, `ñ` → `nn`, `ẽ` → `en` (`kom̃en` → `kommen`).

Words are split at white space and punctuation, as in the transcriptions. A compound with hyphens that is not listed as a whole is looked up part by part (`Tact-Amt` → `Takt-Amt`). A word broken over two lines with a hyphen before `<lb/>` (or `<pb/>`) is looked up joined (`wuͤr-<lb/>den` → `wuͤrden`); the hyphen is kept before a capital (`Prob-<lb/>Stuͤck`). Abbreviations keep their full stop (`pag.`, `Vid.`).

## The lexicon

`lexicon.tsv` is a tab-separated table with one line per original form:

| Column | Content |
| --- | --- |
| `orig` | the form as transcribed, with `ſ`, combining e etc. |
| `norm` | the modern form |
| `status` | `cab`: suggestion from CAB, not yet reviewed; `checked`: reviewed and kept; `edited`: changed by the editors |
| `count` | occurrences when the lexicon was created |
| `note` | other forms CAB chose in some contexts, or the reason for an edit |

Only forms that need more than the character rules are listed.

## Reviewing

Sort by `count` (the file is sorted that way) and work from the top: the first few hundred lines cover most of the text.

- If a modern form is right, set `status` to `checked`.
- If it is wrong, change `norm`, set `status` to `edited` and say why in `note`.

To keep a word exactly as it is, list it with `norm` equal to the character-rule result (e.g. `Clavier`).

## Origin

The lexicon was started from one run of [CAB](https://www.deutschestextarchiv.de/doku/software#cab), the normalisation service of the Deutsches Textarchiv, over all Fraktur transcriptions (`scripts/bootstrap_lexicon.py`). CAB suggestions were not taken over where CAB:
- normalised names or foreign-language words as German;
- dropped music signs (`♭D` → `D`);
- only changed punctuation, or dropped the accents of French and Italian words (`Traité` → `Traite`);
- capitalised a lower-case word.

CAB's contractions are written with a space (`ers` → `er es`). The forms listed as wrong in [probstuecke-digital#124](https://github.com/pfefferniels/probstuecke-digital/issues/124) and other clear errors (names, Latin and French words, diminutives in `-gen`, superlatives in `aller-`) are corrected and marked `edited`.

To see what CAB would suggest for new texts, run the script with `--out` to a different file and compare.
