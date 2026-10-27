# Changelog

Notable changes to the encodings. Each version corresponds to a tagged release of this repository.

## 1.0.0 (unreleased)

First versioned release.

### Added

- Every XML file declares a local RELAX NG schema and validates against it; new ODDs for the translations, notes and indices (`probstuecke-tei.odd`) and for `works.xml` (`probstuecke-worklist.odd`); the existing ODDs are adapted to the project's encoding practice
- `scripts/validate.sh` to validate all encodings with Jing, `scripts/build-schemas.sh` to regenerate the schemas from the ODDs
- `scripts/check_references.py` to check internal pointers (`@facs`, `ref/@target`, `ptr/@target`, index links), with an allowlist of known open cases
- GitHub Actions workflow running both checks on pull requests and on `main`
- `encodings/about/about_en.xml`: description of the edition, its sources, selection, editorial approach, credits and licences
- Publisher and CC BY 4.0 licence statements in the index files
- `CITATION.cff` and `.zenodo.json` for citation and archiving
- `encodings/register/register_1731.xml`: transcription of Mattheson's Register of the 1731 print (pp. 465–482, 527 entries), its entries linked to the indices
- `encodings/indices/terms.xml`: index of terms based on the Register: 151 terms with Mattheson's headword, a modern German form and an English gloss, and 323 references to the Ober-Classe (289 from the Register, 34 added by the editors); the words are tagged with `<term corresp="#t_…">` in the 1731 commentary (Probstücke 8, 10–14, 16, 17 and 22 follow once their transcriptions are revised)
- `scripts/tag_terms.py` to tag the passages of the index of terms; it only adds what is missing and can be run again after transcriptions change
- `term` in the customisation of the DTA Base Format, `TEI/@type="terms"` and `listRef` in `probstuecke-tei.odd`; `check_references.py` also checks the pointers of `<term>`, of the Register and of the index of terms
- `normalisation/`: the word list behind the modernised spelling on the website, started from one run of the DTA's CAB service and corrected where CAB was wrong (names, Latin, French and Italian words, diminutives, contractions); `scripts/bootstrap_lexicon.py` created it

### Fixed

- Encoding errors found by schema validation, among them: the missing treble clefs in an example of Robert Hill's lesson on Probstück 3; the link from St. Lambert's *Traité* in the 1719 text of Probstück 7 to the bibliography; a wrong rendition in the 1719 text of Probstück 22
- Mattheson's surname and forename were swapped in the source descriptions
- The 1719 *Organisten-Probe* was dated 1731 in `<bibl type="M">`
- Typos in the 1719 title ("Matthsons … im Artkel")
- The 1719 text of Probstück 12 carried the source description of the 1731 print
- References to St. Lambert in Probstück 9 pointed to a non-existent index entry
- The *Histoire des ouvrages des savans* cited in Probstück 24 was missing from the bibliography
- The pointer to the Marcello aria in the English text of Probstück 10 was malformed
- Name order of Aristoxenus and Benedetto Marcello in the indices
- 57 broken pointers: `@facs` to undefined zones (1719 texts now point to the page where no zone exists), and `ref/@target` to IDs from older versions of the scores or without `#`
- Wrong staff numbers in the score of Probstück 19 and in the fourth music example of Probstück 21, which made Verovio crash and broke all pages of both pieces
- In the 1719 text of Probstück 12, "ſonſt" was encoded with combining e instead of ſ
- Transcription errors checked against the prints: "Wotte", "kit", "niht", "gafallen", "durgehen", "oͤffentlih", "nocht", "jerderzeit", "weidloch", "mansehnlich", "besanden" (for Worte, mit, nicht, gefallen, durchgehen, oͤffentlich, noch, jederzeit, weidlich, man ſehnlich, beſtanden); f for ſ in "derfelben", "felbiges", "geftimmet", "geftehet", "Organiften-Probe", "ausfchlieſſen"; a missing hyphen in "brilli-ren" (Probstück 2, 1719)
