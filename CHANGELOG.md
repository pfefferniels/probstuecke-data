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
- Modern key signatures for the modernised view where the prints use old ones (minor keys with one flat or sharp fewer, B-flat major with one flat, d minor without signature, abbreviated signatures in examples): Nos. 2, 9, 10, 14, 15, 21, 22 and 24, examples of Nos. 1, 2, 9, 10, 12, 13, 14, 20, 21, 22 (including the two of the 1719 Anmerckungen, with an abbreviated signature of three sharps), the arias in Nos. 10, 15, 16, the lessons by Pfeffer (Nos. 10, 14), Molinaro (No. 21) and Hill (No. 4). They are encoded like the modern clefs, as `<choice><orig/><reg><scoreDef><keySig/></scoreDef></reg></choice>` at the start of the section (in the same `<scoreDef>` as the modern clefs where both apply), so that the diplomatic view is unchanged
- The accidentals of the modernised view follow the modern key signatures (in the files above, 505 printed accidentals the modern signature makes superfluous moved into `<orig>`, 223 needed ones supplied, 19 supplied ones removed), and all scores, examples and lessons have the cautionary accidentals the rules of the full scores ask for (52 more); `scripts/check_accidentals.py` reports nothing on any file
- GitHub Actions workflow running the schema validation, `check_references.py`, `check_accidentals.py`, `label_example_bars.py --check` and `check_facsimile.py` on pull requests and on `main`
- `scripts/check_facsimile.py` to check the facsimile links (canvases, image sizes, zones against staves and barlines), and the scripts in `scripts/facsimile_repair/` that repaired them
- `encodings/about/about_en.xml`: description of the edition, its sources, selection, editorial approach, credits and licences
- Publisher and CC BY 4.0 licence statements in the index files
- `CITATION.cff` and `.zenodo.json` for citation and archiving
- `encodings/register/register_1731.xml`: transcription of Mattheson's Register of the 1731 print (pp. 465–482, 527 entries), its entries linked to the indices
- `encodings/indices/terms.xml`: index of terms based on the Register: 151 terms with Mattheson's headword, a modern German form and an English gloss, and 323 references to the Ober-Classe (289 from the Register, 34 added by the editors); the words are tagged with `<term corresp="#t_…">` in the 1731 commentary (Probstücke 8, 10–14, 16, 17 and 22 follow once their transcriptions are revised)
- `scripts/tag_terms.py` to tag the passages of the index of terms; it only adds what is missing and can be run again after transcriptions change
- `term` in the customisation of the DTA Base Format, `TEI/@type="terms"` and `listRef` in `probstuecke-tei.odd`; `check_references.py` also checks the pointers of `<term>`, of the Register and of the index of terms
- `normalisation/`: the word list behind the modernised spelling on the website, started from one run of the DTA's CAB service and corrected where CAB was wrong (names, Latin, French and Italian words, diminutives, contractions); `scripts/bootstrap_lexicon.py` created it
- The realisations of Nos. 10 and 14 by Niels Pfeffer and of Nos. 20 and 21 by Larry Molinaro, and Robert Hill's lesson on No. 16, are expressions of their works in `works.xml` (`ps10-004`, `ps14-004`, `ps16-004`, `ps20-004`, `ps21-004`), so that the website shows them with their scores and recordings

### Changed

- Music examples: bars that quote the piece point to the quoted bar of the score with `@corresp` in Nos. 9, 20, 21 and 22 as well; the pointers in No. 18 named IDs that no longer exist in the score. Bars 23 and 24 of the score of No. 11 have their IDs back, so that the examples and the commentary can point to them
- Music examples: bars that quote the piece carry the number of the quoted bar as `@label` (in No. 14 instead of the words "Achter Tact", "Neuter Tact."), shown on the website instead of a local numbering (probstuecke-digital#81); `scripts/label_example_bars.py` sets these labels, and CI checks them
- Music examples: every example has a full meter, encoded like the scores' as a `<meterSig>` in each `<staffDef>`, invisible where the print shows none (only one example of No. 24 shows C); the visible meters of the examples in Nos. 9 and 14 were not in the prints. Bars that do not fill the meter (upbeats, cut-off bars) have `@metcon="false"`, also in Robert Hill's examples of No. 4 (#30)
- Music examples: modern clefs for the website's modern view, as in the scores (`<choice>` of `<orig>` and `<reg>`): soprano, alto and tenor clefs become treble clefs (the tenor clef of the low passage in No. 6 a bass clef), the French violin clef a treble clef, the baritone clef a bass clef. Initial clefs, which MEI 4.0.1 allows in no `<choice>` inside `<staffDef>`, are modernised by a `<scoreDef>` in the `<reg>` of a `<choice>` at the start of the section. The same for the arias quoted in Nos. 10, 15 and 16, whose voices are in soprano and alto clefs
- Lessons and realisations follow the conventions of the other texts: the score in a `<div type="score">` with `<figure type="notatedMusic">` (Robert Hill's lessons on Nos. 3 and 4 refer to it, but did not embed it; the notes on the realisations of Nos. 10, 14, 20 and 21 had no link to theirs), the text in a division of its own; a `<head>` in the figure says what a score that is not Mattheson's shows. `lesson_transcription.odd` allows `figure` and documents `ptr[@type="audio"]`
- Robert Hill's lessons: the participants with their IDs and roles in `particDesc/listPerson` instead of a `listPerson` in the body; all playing as `<kinesic type="playing">` (some was `<incident>`); language codes in BCP 47 (`de`, `en` instead of `ger`, `eng`); dates in the headings written out (No. 16 had 03/06/2019 for 3 June, Nos. 3 and 4 the American order); the empty `<notatedMusic>` after Robert Hill's playing in No. 16, which is not transcribed, is a comment
- Titles of the notes on the realisations name piece and musician instead of "Description of Realization" and "JCD, PS 4"

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
- Wrong sounding pitches: in Mattheson's annotations to No. 11 (mm. 4-6, 21-22) the flats were on g and d instead of a, b and e; in No. 10, m. 16, the b with a printed natural sounded b flat; 100 notes altered by the key signature or by an accidental earlier in the bar had no `@accid.ges` (so that the MIDI played them unaltered)
- Accidentals in the wrong place for the modernised view: a natural in No. 1, m. 36, and a sharp in No. 2, m. 8, were hidden although needed; a natural in No. 10, m. 16, is not in the print and is supplied now
- `<graphic>` gives the page image (IIIF Image API) instead of the IIIF canvas, which moves to `surface/@corresp` (#31); the unused facsimile section of the English text of No. 5, on local images not in the repository, is removed
- Transcriptions checked against the prints: the 1719 text of No. 6, normalised (round s, no line breaks) and with 21 wrong words ("sagten" for ſagen, "Gesellschaft", "getroffen habe"), is transcribed diplomatically anew; the 1731 text of No. 8 gets §. 2, and its §. 1 and its note on St. Lambert are corrected ("gemeinglich", "ſchieht", "unterſscheiden", round s), the note with its page (p. 343); the 1731 text of No. 22 is corrected (no text was missing: Mattheson dropped §§. 1 and 4 of 1719), and the 1719 text is transcribed diplomatically anew ("#c" for cis, "hölzern schicken" for höltzern klingen, "neuenzehnten", "extemporifiren"; a duplicate page break) and gets the "Anmerckungen" printed under the score (p. 221), with their two bass examples encoded (`anm-music-example1.xml`, `anm-music-example2.xml`). In all three texts of No. 22, "si suona" in §. 3 points to bar 29 instead of bar 11, and "Tutti" to all four tutti
- In Robert Hill's lesson on No. 4, "Mit Zäsur würde das gehen" points again to the student's playing (example 7), whose ID was lost when the examples became `ptr[@type="transcription"]`; the transcription of the bass variation is no longer inside the `<ref>` to the bars it varies; one description of the student's playing named him again ("Student spielt …") after `@who`
