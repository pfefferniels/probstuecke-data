# Changelog

Notable changes to the encodings. Each version corresponds to a tagged release of this repository.

## 1.0.0 (unreleased)

First versioned release.

### Added

- Every XML file declares a local RELAX NG schema and validates against it; new ODDs for the translations, notes and indices (`probstuecke-tei.odd`) and for `works.xml` (`probstuecke-worklist.odd`); the existing ODDs are adapted to the project's encoding practice
- `scripts/validate.sh` to validate all encodings with Jing, `scripts/build-schemas.sh` to regenerate the schemas from the ODDs
- `scripts/check_references.py` to check internal pointers (`@facs`, `ref/@target`, `ptr/@target`, index links), with an allowlist of known open cases
- `scripts/check_accidentals.py` to check the written accidentals of the MEI encodings against the edition's convention for the diplomatic and the modernised view (`<orig>`, `<supplied>`/`<reg>`, `@func="caution"`), with the rules the full scores follow and an allowlist of knowingly kept cases
- Accidentals of the music examples encoded for the diplomatic and the modernised view as in the scores: superfluous printed ones in `<orig>`, missing and cautionary ones in `<supplied>`, so that the website can show the examples in modern notation, too
- GitHub Actions workflow running both checks on pull requests and on `main`
- `scripts/check_facsimile.py` to check the facsimile links (canvases, image sizes, zones against staves and barlines), and the scripts in `scripts/facsimile_repair/` that repaired them
- `encodings/about/about_en.xml`: description of the edition, its sources, selection, editorial approach, credits and licences
- Publisher and CC BY 4.0 licence statements in the index files
- `CITATION.cff` and `.zenodo.json` for citation and archiving
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
- In the second music example of Probstück 24, the e of bar 2 was encoded as e sharp; Mattheson's text (§ 19) says that it returns to e natural and that the composer left out the sign
- Facsimile links: 183 surfaces pointed to the wrong BSB canvas and 349 declared outdated image sizes; the zones of the 1731 print, drawn on the images of 2019, are rescaled to today's images; damaged zones restored, zones attached to the wrong bars moved, missing bar zones added, and six commentary paragraphs linked to their zones
- Page numbers of 14 page breaks corrected against the prints
- Nos. 14 and 24 keep both notations in `score.xml` (with `mdiv/@label`); the duplicate `score-2.xml` files are removed. The second notation of No. 24 declared the wrong staff, which made Verovio crash
- Two mistyped figures: No. 19, bar 37, and No. 22, first example, bar 7 (raised sixths)
- Double sharps checked against the prints and the figures: in Nos. 21 and 22 (and in No. 21, ex. 4, and No. 22, ex. 3) Mattheson's cross on a note that is already sharp means a double sharp; every note it affects now has `@accid.ges`, crosses the print has were added and two sharps it does not have removed (No. 21, m. 28; No. 21, ex. 4, m. 28); No. 22, m. 42 and m. 45, sound g double sharp, not g sharp. The notes after double sharps in Nos. 14, 18 and 24 have `@accid.ges`, too, and a double sharp in the aria of No. 16 was encoded as a double flat
- The editorial sharps on A in the bass of No. 21 (mm. 17, 20, 24, 32, 34) were shown in the diplomatic view; they are in `<supplied>` now
