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
- `normalisation/`: the word list behind the modernised spelling on the website, started from one run of the DTA's CAB service and corrected where CAB was wrong (names, Latin, French and Italian words, diminutives, contractions); `scripts/bootstrap_lexicon.py` created it

### Changed

- Music examples: bars that quote the piece point to the quoted bar of the score with `@corresp` in Nos. 9, 20, 21 and 22 as well; the pointers in No. 18 named IDs that no longer exist in the score. Bars 23 and 24 of the score of No. 11 have their IDs back, so that the examples and the commentary can point to them
- Music examples: bars that quote the piece carry the number of the quoted bar as `@label` (in No. 14 instead of the words "Achter Tact", "Neuter Tact."), shown on the website instead of a local numbering (probstuecke-digital#81); `scripts/label_example_bars.py` sets these labels, and CI checks them
- Music examples: every example has a full meter, encoded like the scores' as a `<meterSig>` in each `<staffDef>`, invisible where the print shows none (only one example of No. 24 shows C); the visible meters of the examples in Nos. 9 and 14 were not in the prints. Bars that do not fill the meter (upbeats, cut-off bars) have `@metcon="false"`, also in Robert Hill's examples of No. 4 (#30)
- Music examples: modern clefs for the website's modern view, as in the scores (`<choice>` of `<orig>` and `<reg>`): soprano, alto and tenor clefs become treble clefs (the tenor clef of the low passage in No. 6 a bass clef), the French violin clef a treble clef, the baritone clef a bass clef. Initial clefs, which MEI 4.0.1 allows in no `<choice>` inside `<staffDef>`, are modernised by a `<scoreDef>` in the `<reg>` of a `<choice>` at the start of the section. The same for the arias quoted in Nos. 10, 15 and 16, whose voices are in soprano and alto clefs

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
