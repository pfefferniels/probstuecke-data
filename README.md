# Probstücke Digital: encodings

This repository contains the TEI and MEI encodings of [*Probstücke Digital*](https://probstuecke-digital.de/), a digital edition of the 24 Prob-Stücke from Johann Mattheson's *Exemplarische Organisten-Probe* (Hamburg 1719) and *Grosse General-Baß-Schule* (Hamburg 1731). The website is built from these files by [probstuecke-digital](https://github.com/pfefferniels/probstuecke-digital).

Edited by Niels Pfeffer and Klaus Rettinghaus.

## Contents

| Path | Content |
| --- | --- |
| `encodings/<n>/mattheson/score.xml` | MEI encoding of Probstück *n*, covering both prints (variants in `<app>`/`<rdg>`) |
| `encodings/<n>/mattheson/comments_1st.xml` | Mattheson's commentary in the 1719 print (TEI, DTA Base Format) |
| `encodings/<n>/mattheson/comments_de.xml` | Mattheson's commentary in the 1731 print (TEI, DTA Base Format) |
| `encodings/<n>/mattheson/comments_en.xml` | English translation of the 1731 commentary (TEI) |
| `encodings/<n>/mattheson/music-example*.xml` | Music examples within the commentary (MEI) |
| `encodings/<n>/<name>/` | Lessons and realisations by other musicians: the transcription of a lesson or notes on a realisation (TEI), its score and music examples (MEI) and audio recordings |
| `encodings/works.xml` | List of works and their expressions (MEI `workList`); drives the website's overview |
| `encodings/indices/` | Indices of persons, literature, musical works and terms (TEI); the index of terms (`terms.xml`) is based on Mattheson's Register |
| `encodings/register/register_1731.xml` | Mattheson's Register of the 1731 print (pp. 465–482), transcribed (TEI, DTA Base Format) |
| `encodings/guidelines/` | Editorial guidelines (TEI) |
| `encodings/about/` | Description of the edition shown on the website's About page (TEI) |
| `encodings/frontpage/` | Transcriptions of the title pages |
| `schema/` | ODD customisations and RELAX NG schemas for TEI and MEI (see [`schema/README.md`](schema/README.md)) |
| `scripts/` | `validate.sh` validates the encodings, `build-schemas.sh` regenerates the RELAX NG schemas from the ODDs, `check_references.py` checks internal pointers, `check_accidentals.py` checks the written accidentals against the edition's convention, `label_example_bars.py` labels the bars of the music examples with the bar numbers of the piece they quote, `tag_terms.py` tags the passages listed in the index of terms, `check_facsimile.py` checks the links to the page images (canvases, zones, image sizes); `facsimile_repair/` holds the one-off scripts and tables with which these links were repaired in 2026, kept as a record, and `image_urls.py`, which turns a `<graphic>` that names a IIIF canvas into the image URL the encodings use (with the canvas in `surface/@corresp`) |

`encodings/toc.json` is a table of contents from an earlier version of the website and is no longer used.

## Validation

Every XML file under `encodings/` declares its schema in an `<?xml-model?>` processing instruction. To validate all of them with [Jing](https://github.com/relaxng/jing-trang), run

```sh
JING_JAR=/path/to/jing.jar scripts/validate.sh
```

The script exits with a non-zero status if a file is invalid or has no schema. [`schema/README.md`](schema/README.md) explains which schema applies to which files and how to regenerate the schemas after changing an ODD.

`python3 scripts/check_references.py` checks the internal pointers and `python3 scripts/check_accidentals.py` the written accidentals of all MEI files (printed ones that modern notation does not need in `<orig>`, missing ones in `<supplied>`, cautionary ones with `@func="caution"`, modern key signatures as `<choice>`); the conventions are described in the scripts' docstrings. Both run in the GitHub Actions workflow, too.

## Index of terms

`encodings/indices/terms.xml` modernises Mattheson's Register (transcribed in `encodings/register/register_1731.xml`) for the Ober-Classe: one entry per term with Mattheson's headword, a modern German form, an English gloss and the passages, each with Mattheson's page and a short quotation in which `<term>` marks the word. `scripts/tag_terms.py` tags these words in the transcriptions (`<term corresp="#t_…">`) and completes the pointers in `terms.xml`. It only adds what is missing, so after a transcription has been added or replaced, run

```sh
python3 scripts/tag_terms.py
```

and check the passages it reports as not found. `--exclude 10/mattheson/comments_de.xml …` leaves files alone that are still being revised.

## Licence

The encodings, transcriptions, translation, notes and indices are licensed under [CC BY 4.0](LICENSE). The page images used on the website are not part of this repository; they are provided by the Bayerische Staatsbibliothek, Munich, under the rights statement [No Copyright – Non-Commercial Use Only](https://rightsstatements.org/vocab/NoC-NC/1.0/).

## Citation

Citation metadata is in [`CITATION.cff`](CITATION.cff); GitHub shows it under "Cite this repository". Changes between versions are listed in [`CHANGELOG.md`](CHANGELOG.md).

## Releases

Each release is a tag of the form `vX.Y.Z` on `main` with a matching `version` in `CITATION.cff` and an entry in `CHANGELOG.md`. Once the repository is enabled in Zenodo's GitHub integration, Zenodo archives every GitHub release and assigns it a DOI, using the metadata in `.zenodo.json`.
