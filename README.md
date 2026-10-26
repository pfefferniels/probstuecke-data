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
| `encodings/<n>/<name>/` | Lessons and realisations by other musicians, with their own scores and notes |
| `encodings/works.xml` | List of works and their expressions (MEI `workList`); drives the website's overview |
| `encodings/indices/` | Indices of persons, literature and musical works (TEI) |
| `encodings/guidelines/` | Editorial guidelines (TEI) |
| `encodings/about/` | Description of the edition shown on the website's About page (TEI) |
| `encodings/frontpage/` | Transcriptions of the title pages |
| `schema/` | ODD customisations and RELAX NG schemas for TEI and MEI |

`encodings/toc.json` is a table of contents from an earlier version of the website and is no longer used.

## Licence

The encodings, transcriptions, translation, notes and indices are licensed under [CC BY 4.0](LICENSE). The page images used on the website are not part of this repository; they are provided by the Bayerische Staatsbibliothek, Munich, under the rights statement [No Copyright – Non-Commercial Use Only](https://rightsstatements.org/vocab/NoC-NC/1.0/).

## Citation

Citation metadata is in [`CITATION.cff`](CITATION.cff); GitHub shows it under "Cite this repository". Changes between versions are listed in [`CHANGELOG.md`](CHANGELOG.md).

## Releases

Each release is a tag of the form `vX.Y.Z` on `main` with a matching `version` in `CITATION.cff` and an entry in `CHANGELOG.md`. Once the repository is enabled in Zenodo's GitHub integration, Zenodo archives every GitHub release and assigns it a DOI, using the metadata in `.zenodo.json`.
