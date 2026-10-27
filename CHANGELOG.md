# Changelog

Notable changes to the encodings. Each version corresponds to a tagged release of this repository.

## 1.0.0 (unreleased)

First versioned release.

### Added

- Every XML file declares a local RELAX NG schema and validates against it; new ODDs for the translations, notes and indices (`probstuecke-tei.odd`) and for `works.xml` (`probstuecke-worklist.odd`); the existing ODDs are adapted to the project's encoding practice
- `scripts/validate.sh` to validate all encodings with Jing, `scripts/build-schemas.sh` to regenerate the schemas from the ODDs
- `encodings/about/about_en.xml`: description of the edition, its sources, selection, editorial approach, credits and licences
- Publisher and CC BY 4.0 licence statements in the index files
- `CITATION.cff` and `.zenodo.json` for citation and archiving

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
- Wrong staff numbers in the score of Probstück 19 and in the fourth music example of Probstück 21, which made Verovio crash and broke all pages of both pieces
