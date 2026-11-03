# Probstücke Digital: encodings

This repository contains the TEI and MEI encodings of [*Probstücke Digital*](https://probstuecke-digital.de/), a digital edition of the 24 Prob-Stücke from Johann Mattheson's *Exemplarische Organisten-Probe* (Hamburg 1719) and *Grosse General-Baß-Schule* (Hamburg 1731). The website is built from these files by [probstuecke-digital](https://github.com/pfefferniels/probstuecke-digital).

Edited by Niels Pfeffer and Klaus Rettinghaus.

## Contents

| Path | Content |
| --- | --- |
| `encodings/<n>/mattheson/score.xml` | MEI encoding of Probstück *n*, covering both prints (variants in `<app>`/`<rdg>`) |
| `encodings/<n>/mattheson/comments_1719.xml` | Mattheson's commentary in the 1719 print (TEI, DTA Base Format) |
| `encodings/<n>/mattheson/comments_1731.xml` | Mattheson's commentary in the 1731 print (TEI, DTA Base Format) |
| `encodings/<n>/mattheson/comments_1731_en.xml` | English translation of the 1731 commentary (TEI) |
| `encodings/<n>/mattheson/music-example*.xml` | Music examples within the commentary (MEI) |
| `encodings/<n>/<name>/` | Lessons and realisations by other musicians: the transcription of a lesson or notes on a realisation (TEI, named after their language: `comments_de.xml`, `comments_en.xml`, `comments_fr.xml`), its score and music examples (MEI) and audio recordings; Dijoux's French notes on No. 4 are translated into English (`4/jcd/comments_en.xml`) |
| `encodings/works.xml` | List of works and their expressions (MEI `workList`); drives the website's overview |
| `encodings/indices/` | Indices of persons, literature, musical works and terms (TEI); the index of terms (`terms.xml`) is based on Mattheson's Register |
| `encodings/register/register_1731.xml` | Mattheson's Register of the 1731 print (pp. 465–482), transcribed (TEI, DTA Base Format) |
| `encodings/guidelines/` | Editorial guidelines (TEI) |
| `encodings/about/` | Description of the edition shown on the website's About page (TEI) |
| `encodings/frontpage/` | Transcriptions of the title pages |
| `collation/` | Records of the collation of the prints: `reprint_1731_music.tsv`, the differences in the music between the first and the later printing of 1731 |
| `schema/` | ODD customisations and RELAX NG schemas for TEI and MEI (see [`schema/README.md`](schema/README.md)) |
| `scripts/` | `validate.sh` validates the encodings, `build-schemas.sh` regenerates the RELAX NG schemas from the ODDs, `check_references.py` checks internal pointers, `check_accidentals.py` checks the written accidentals against the edition's convention, `label_example_bars.py` labels the bars of the music examples with the bar numbers of the piece they quote, `tag_terms.py` tags the passages listed in the index of terms, `check_facsimile.py` checks the links to the page images (canvases, zones, image sizes); `check_alignment.py` checks the alignment of the translations and of the 1719 print with the 1731 text, sentence by sentence; `facsimile_repair/` holds the one-off scripts and tables with which these links were repaired in 2026, kept as a record, and `image_urls.py`, which turns a `<graphic>` that names a IIIF canvas into the image URL the encodings use (with the canvas in `surface/@corresp`) |

`encodings/toc.json` is a table of contents from an earlier version of the website and is no longer used.

Every TEI file declares its main language twice, as `@xml:lang` on its root and in the header (`<profileDesc><langUsage>`); a lesson that switches between German and English lists both, the main one first. Passages in another language carry `@xml:lang`, too (`<foreign xml:lang="lat">`, `<quote xml:lang="fra">`). All language codes are the three-letter codes of ISO 639-3 (`deu`, `eng`, `fra`, `ita`, `lat`, `grc`, …), as the [DTA Base Format](https://www.deutschestextarchiv.de/doku/basisformat/fremdsprachlMaterial.html) prescribes and as `works.xml` uses them; the website turns them into BCP 47 tags (`de`, `la`, …) for HTML.

## Validation

Every XML file under `encodings/` declares its schema in an `<?xml-model?>` processing instruction. To validate all of them with [Jing](https://github.com/relaxng/jing-trang), run

```sh
JING_JAR=/path/to/jing.jar scripts/validate.sh
```

The script exits with a non-zero status if a file is invalid or has no schema. [`schema/README.md`](schema/README.md) explains which schema applies to which files and how to regenerate the schemas after changing an ODD.

`python3 scripts/check_references.py` checks the internal pointers and `python3 scripts/check_accidentals.py` the written accidentals of all MEI files (printed ones that modern notation does not need in `<orig>`, missing ones in `<supplied>`, cautionary ones with `@func="caution"`, modern key signatures as `<choice>`); the conventions are described in the scripts' docstrings. Both run in the GitHub Actions workflow, too.

## Updating the website

When a push to `main` has passed the checks, the workflow (`.github/workflows/check.yml`) asks [probstuecke-digital](https://github.com/pfefferniels/probstuecke-digital) to update its submodule `probstuecke-data` to the new `main` and to deploy the website again. For this the repository needs the secret `WEBSITE_DISPATCH_TOKEN`, a personal access token that may write to probstuecke-digital:

1. On GitHub, under Settings → Developer settings → Personal access tokens → Fine-grained tokens, generate a new token with *Only select repositories*: `probstuecke-digital`, and the repository permission *Contents: Read and write*.
2. In this repository, under Settings → Secrets and variables → Actions, add it as a new repository secret named `WEBSITE_DISPATCH_TOKEN`.

Without the secret the workflow only warns; with an expired token it fails. Either way the website catches up with its next deploy, or with *Run workflow* under Actions → Deploy to GitHub Pages in probstuecke-digital.

## Alignment of the translation and of the two prints

The English translation and the 1719 print can each be compared with the 1731 text sentence by sentence. All three are divided into sentences (`<s>`). The sentences of the prints carry an ID made of the paragraph's ID and their number in it (`p1-1-s2`: §. 1, first paragraph, second sentence; paragraphs outside the numbered sections are `p0-1`, `p0-2`, …).

The sentences of the translation point with `@corresp` to the sentence they render. A German sentence that the translation splits into two is pointed to twice; an English sentence that renders two German ones points to both:

```xml
<!-- comments_1731.xml -->
<s xml:id="p1-1-s2">Ob nun das Gleichniß hincket, laſſe dahin geſtellt ſeyn; mir iſt es ſehr laͤcherlich vorgekommen.</s>
<!-- comments_1731_en.xml -->
<s corresp="comments_1731.xml#p1-1-s2">Whether or not the simile is lopsided, we will leave to rest.</s>
<s corresp="comments_1731.xml#p1-1-s2">To me it appeared very ridiculous.</s>
```

In the same way, the sentences of the 1719 print point to the sentences that Mattheson made of them in 1731, however much he reworded them:

```xml
<!-- comments_1719.xml -->
<s xml:id="p1-1-s2" corresp="comments_1731.xml#p1-1-s2">Ob nun das <hi rendition="#aq">Simile</hi> hincket, laſſe dahin geſtellet ſeyn; mir iſt es sehr laͤcherlich vorgekommen.</s>
```

A 1719 sentence that Mattheson left out in 1731 points nowhere, and a sentence he added in 1731 is pointed to by none. Notes are left out of the alignment: where a note of 1719 became running text in 1731, or running text a note, the sentences concerned have no counterpart.

A German sentence ends with a full stop, a question mark or an exclamation mark, not with a colon or semicolon, not with the full stop of an abbreviation or an ordinal number ("Vid.", "pag.", "im 23. Tact"), and not with a question or exclamation mark followed by a lowercase word, with which Mattheson continues the sentence ("O! iſt es nichts anders als das? ich dachte …"). Line and page breaks, notes and cited titles (`<bibl>`) stay inside the sentence they fall in. A quotation of several sentences that ends its sentence is divided inside the `<quote>`; the lead-in up to it ("… da er ſich alſo heraus läſſt:") is then a sentence of its own. Where an element such as `<hi>` spans the end of a sentence, it is split into two. Where the translation leaves a German sentence out, the neighbouring English sentence points to it as well, so that it is still shown.

On the website, the sentences of the 1731 text stand small and grey beneath the sentences of the translation. The two prints, which mostly agree word for word, show only where they differ: the website compares the words of each pair of aligned sentences (in modern spelling) and sets the reading of the other print beneath each passage that differs, and marks the sentences that the other print lacks (readers can hide all this). A sentence of the other print without counterpart stands beneath the sentence before it; but a paragraph of the other print none of whose sentences has a counterpart, such as the reference to a piece by another composer (“Vid. Keisers Erlesene Sätze”) with which many commentaries of 1719 begin, is no reading of any sentence: it stands as a paragraph of its own (“only in 1719”), small and grey, where it stands in the other print. `python3 scripts/check_alignment.py` checks that every pointer names a sentence, that the translation renders every sentence of the sections it translates, that the order is kept, that the sentences of the prints have the right IDs and that every word of their paragraphs is in a sentence; `--verbose` lists the sentences of either print that have no counterpart in the other. All 24 translations are aligned (in No. 24 only §. 31 is translated), and so are the two prints of all 24 pieces. The English translation of Dijoux's notes on his realisation of No. 4 (`4/jcd/comments_en.xml`) is aligned with the French in the same way (`<s corresp="comments_fr.xml#p0-1-s1">`).

## Variants of the music

Where the two prints differ in the music, the score or the music example has an `<app>` with the reading of each print: `<lem>` and `<rdg>` name their print with `@source` (`#firstEdition` for 1719, `#secondEdition` for 1731), and the file declares both prints in its `<sourceDesc>`, where each `<source>` points with `@corresp` to the commentary of its print (`#ps1-001`, `#ps1-002`). A reading without `@source` is taken where an `<app>` has no reading of a print: usually the `<lem>`, which is the 1731 reading. An empty reading means that the print has nothing there (e.g. no figure).

On the website, each print's page draws its own readings, and the passages where the other print differs are marked (readers can hide this together with the differences in the text): pointing at one, or tapping it, shows the other print's reading of the bar. Where only the other print has something in a bar (a figure, an ornament, a direction), it stands grey in its place; where only the other print has something in a layer, a small mark stands above the staff.

The copies of one print can differ, too, where type was changed or lost while the sheets were being printed. Four copies of the print of 1731 have been compared in the Ober-Classe (pp. 297–484): those of the Bayerische Staatsbibliothek (Mus.th. 978 a, which the edition follows and whose page images it shows, and 4 Mus.th. 978), the Österreichische Nationalbibliothek (ZMUS MAG 391602-B) and the Biblioteka Narodowa (Mus.I.235). Where they differ in the music, an `<app type="copies">` gives the reading of each copy; its `<lem>` and `<rdg>` name copies (`#copy-D-Mbs-978a`, `#copy-D-Mbs-978`, `#copy-A-Wn`, `#copy-PL-Wn`) and, where it agrees, the print of 1719 (`#firstEdition`) and the later printing of 1731 (`#secondEditionReprint`, see below), all declared in the file's `<sourceDesc>`. The `<lem>` is the reading the edition adopts. Since no reading of such an `<app>` names `#secondEdition`, both prints' pages draw the `<lem>`, and the website marks nothing there. There are three such places: No. 8, bar 3 (b, c′ in two copies), No. 20, bar 31 (a figure 6 that only Mus.th. 978 a and the print of 1719 have) and No. 24, bar 18 (the dot of the last b♭, which the bar needs and only 4 Mus.th. 978 prints).

The print of 1731 was later printed again, without date, from type set anew (VD18 12997536; copy: SUB Hamburg, MS 163/2b): its title page is black only, it has 460 pages instead of 484, the errata of 1731 are applied, and the spelling is modernised. Nothing in it suggests that Mattheson revised the text, so the edition follows the print of 1731, whose errata it gives as `<corr type="corrigenda">`.

Where the later printing differs from the first in the music, its reading stands in an `<app type="reprint">`: the `<lem source="#secondEdition">` holds the first printing's reading, which the edition follows, and the `<rdg source="#secondEditionReprint">` the later printing's (empty where it has nothing). Only the `<lem>` names a print that the website draws (and none names `#firstEdition`), so both prints' pages draw the `<lem>`, and the website marks nothing. The places are mostly figures, added, left out or changed, and some accidentals, rests, dots, slurs and tempo words; a few are misprints of the later printing (No. 15, aria, bar 85; No. 20, example 7). [`collation/reprint_1731_music.tsv`](collation/reprint_1731_music.tsv) lists every difference that the collation of the Ober-Classe found, also those the encodings cannot hold (custodes, the key signatures repeated at the beginnings of lines, beaming and the order of stacked figures), with the reason why each is or is not encoded. Where the collation showed that the encoding did not follow the first printing (No. 12, bars 32 and 33: 6/4/3, the encoding had the 6/4/2 of 1719; No. 22, example 2: four slurs were missing), the encoding has been corrected. The commentary of the later printing has not been collated.

## Index of terms

`encodings/indices/terms.xml` modernises Mattheson's Register (transcribed in `encodings/register/register_1731.xml`) for the Ober-Classe: one entry per term with Mattheson's headword, a modern German form, an English gloss and the passages, each with Mattheson's page and a short quotation in which `<term>` marks the word. `scripts/tag_terms.py` tags these words in the transcriptions (`<term corresp="#t_…">`) and completes the pointers in `terms.xml`. It only adds what is missing, so after a transcription has been added or replaced, run

```sh
python3 scripts/tag_terms.py
```

and check the passages it reports as not found. `--exclude 10/mattheson/comments_1731.xml …` leaves files alone that are still being revised.

## Licence

The encodings, transcriptions, translation, notes and indices are licensed under [CC BY 4.0](LICENSE). The page images used on the website are not part of this repository; they are provided by the Bayerische Staatsbibliothek, Munich, under the rights statement [No Copyright – Non-Commercial Use Only](https://rightsstatements.org/vocab/NoC-NC/1.0/).

## Citation

Citation metadata is in [`CITATION.cff`](CITATION.cff); GitHub shows it under "Cite this repository". Changes between versions are listed in [`CHANGELOG.md`](CHANGELOG.md).

## Releases

Each release is a tag of the form `vX.Y.Z` on `main` with a matching `version` in `CITATION.cff` and an entry in `CHANGELOG.md`. Once the repository is enabled in Zenodo's GitHub integration, Zenodo archives every GitHub release and assigns it a DOI, using the metadata in `.zenodo.json`.
