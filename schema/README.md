# Schemas

Every XML file under `encodings/` names its schema in an `<?xml-model?>` processing instruction with a relative path into this directory, for example

```xml
<?xml-model href="../../../schema/probstuecke-tei.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>
```

The RELAX NG schemas (`.rng`) are generated from the ODD files (`.odd`) next to them. Change the ODD, never the RNG, and regenerate the RNG as described below.

| Schema | Source | Customisation of | Used by |
| --- | --- | --- | --- |
| `basisformat_customized.rng` | `basisformat_customized.odd` | DTA Base Format, TEI P5 | Transcriptions of the prints: `*/mattheson/comments_1719.xml`, `*/mattheson/comments_1731.xml`, `frontpage/mattheson/*.xml`, `register/register_1731.xml` |
| `probstuecke-tei.rng` | `probstuecke-tei.odd` | TEI P5 | English translations (`*/mattheson/comments_1731_en.xml`), notes on the realisations (`4/jcd/comment_fr.xml`, `*/pfeffer/comments_de.xml`, `*/molinaro/comments_*.xml`), `about/`, `guidelines/`, `indices/` |
| `lesson_transcription.rng` | `lesson_transcription.odd` | TEI P5 | Transcriptions of lessons: `*/hill/comments_*.xml` |
| `probstuecke-customization.rng` | `probstuecke-customization.odd` | MEI 4.0.1 | All MEI scores and music examples except `4/jcd/score.xml`; `10/mattheson/measure_annotations.xml` |
| `probstuecke-worklist.rng` | `probstuecke-worklist.odd` | MEI 4.0.1 | `works.xml` |
| `mei-basic-5.0.rng` | – | – | `4/jcd/score.xml` |
| `ediarum.REGISTER.rng` | – | – | not used (see below) |

Each ODD documents its deviations from the standard it customises in comments next to the change (and, for the project ODDs, in their prose).

## Regenerating the RELAX NG schemas

Run

```sh
scripts/build-schemas.sh                        # all ODDs in schema/
scripts/build-schemas.sh probstuecke-tei.odd    # one ODD
```

The script needs `java`, `curl` and `git`. On its first run it downloads pinned versions of the tools and sources into `~/.cache/probstuecke-schema-tools` (set `SCHEMA_TOOLS_DIR` to use another directory):

| Tool or source | Version |
| --- | --- |
| Saxon HE (with xmlresolver 5.2.2) | 12.5 |
| TEI Stylesheets | 7.61.0 |
| TEI P5 (`p5subset.xml`) | 4.12.0 |
| MEI source (`mei-source.xml`) | 4.0.1 |

To upgrade, change the version numbers at the top of the script, rebuild and validate.

For each ODD the script runs the two steps of the TEI ODD processor. An ODD whose `schemaSpec` is in the MEI namespace is compiled against the MEI source, every other ODD against TEI P5. Done by hand, building `probstuecke-tei.rng` amounts to:

```sh
java -cp saxon-he-12.5.jar:xmlresolver-5.2.2.jar:xmlresolver-5.2.2-data.jar net.sf.saxon.Transform \
  -xi:on -s:schema/probstuecke-tei.odd -xsl:Stylesheets/odds/odd2odd.xsl \
  -o:/tmp/probstuecke-tei.compiled.xml defaultSource=/path/to/p5subset.xml
java -cp … net.sf.saxon.Transform \
  -s:/tmp/probstuecke-tei.compiled.xml -xsl:Stylesheets/odds/odd2relax.xsl \
  -o:schema/probstuecke-tei.rng
```

For the MEI ODDs, `defaultSource` is `source/mei-source.xml` of the [MEI repository](https://github.com/music-encoding/music-encoding) at tag `v4.0.1`. `probstuecke-customization.odd` also includes SVG 1.1 from `https://www.tei-c.org/release/xml/tei/custom/schema/relaxng/svg11.rng`, which the build fetches.

The same results can be had with the "ODD to RELAX NG" conversion of [TEI Garage](https://teigarage.tei-c.org/) or with the ODD transformation scenarios of oXygen, but their TEI and Stylesheets versions are not pinned.

## Schemas that are not generated here

- `mei-basic-5.0.rng` is an unchanged copy of <https://music-encoding.org/schema/5.0/mei-basic.rng> (MEI 5.0), kept here so that validation works offline. `4/jcd/score.xml` is encoded in MEI 5.0 basic.
- `ediarum.REGISTER.rng` belongs to the [ediarum](https://www.ediarum.org/) framework for oXygen that was used to edit the indices. The indices do not validate against it (they use `TEI/@type`, `publisher`, `availability`, `addName`) and use `probstuecke-tei.rng` instead; `probstuecke-tei.odd` allows the `telota:doctype` attribute by which ediarum recognises them.

## Validating

```sh
JING_JAR=/path/to/jing.jar scripts/validate.sh
```

validates every XML file under `encodings/` with [Jing](https://github.com/relaxng/jing-trang) against the RELAX NG schema in its `xml-model` instruction (Jing from Maven Central, `org.relaxng:jing`, works as is). Instead of setting `JING_JAR`, a `jing` command on the `PATH` will do. Pass files or directories to validate only those. The script exits with a non-zero status if a file has no RELAX NG `xml-model`, names a remote or missing schema, or is invalid. It does not run the Schematron rules embedded in the schemas.
