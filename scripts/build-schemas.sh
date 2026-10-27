#!/usr/bin/env bash
# Regenerate the RELAX NG schemas in schema/ from their ODD sources.
#
#   scripts/build-schemas.sh                       # every schema/*.odd
#   scripts/build-schemas.sh probstuecke-tei.odd   # selected ODDs
#
# For each ODD the script runs the two steps of the TEI ODD processor:
#   odds/odd2odd.xsl    compile the ODD against its source
#   odds/odd2relax.xsl  turn the compiled ODD into RELAX NG
# The source is MEI if the schemaSpec is in the MEI namespace, otherwise TEI P5.
#
# Pinned versions of Saxon, the TEI Stylesheets, TEI P5 and MEI are
# downloaded once into a cache directory (default
# ~/.cache/probstuecke-schema-tools; set SCHEMA_TOOLS_DIR to change it).
# Requires java, curl and git. See schema/README.md.
set -euo pipefail

SAXON_VERSION=12.5
XMLRESOLVER_VERSION=5.2.2
TEI_STYLESHEETS_VERSION=7.61.0
TEI_VERSION=4.12.0
MEI_VERSION=4.0.1

ROOT=$(cd "$(dirname "$0")/.." && pwd)
SCHEMA_DIR="$ROOT/schema"
TOOLS="${SCHEMA_TOOLS_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/probstuecke-schema-tools}"
MEI_NS=http://www.music-encoding.org/ns/mei

fetch() { # url target
  [ -s "$2" ] && return
  mkdir -p "$(dirname "$2")"
  echo "Downloading $1" >&2
  curl -sSfL -o "$2.part" "$1"
  mv "$2.part" "$2"
}

clone() { # repository tag target
  [ -d "$3" ] && return
  echo "Cloning $1 at $2" >&2
  git -c advice.detachedHead=false clone -q --depth 1 --branch "$2" "$1" "$3"
}

MAVEN=https://repo1.maven.org/maven2
CLASSPATH=
for jar in net/sf/saxon/Saxon-HE/$SAXON_VERSION/Saxon-HE-$SAXON_VERSION.jar \
           org/xmlresolver/xmlresolver/$XMLRESOLVER_VERSION/xmlresolver-$XMLRESOLVER_VERSION.jar \
           org/xmlresolver/xmlresolver/$XMLRESOLVER_VERSION/xmlresolver-$XMLRESOLVER_VERSION-data.jar; do
  fetch "$MAVEN/$jar" "$TOOLS/saxon/${jar##*/}"
  CLASSPATH="$CLASSPATH${CLASSPATH:+:}$TOOLS/saxon/${jar##*/}"
done

STYLESHEETS="$TOOLS/tei-stylesheets-$TEI_STYLESHEETS_VERSION"
clone https://github.com/TEIC/Stylesheets.git "v$TEI_STYLESHEETS_VERSION" "$STYLESHEETS"

TEI_SOURCE="$TOOLS/tei-p5-$TEI_VERSION/p5subset.xml"
fetch "https://www.tei-c.org/Vault/P5/$TEI_VERSION/xml/tei/odd/p5subset.xml" "$TEI_SOURCE"

MEI_SOURCE="$TOOLS/mei-$MEI_VERSION/source/mei-source.xml"
clone https://github.com/music-encoding/music-encoding.git "v$MEI_VERSION" "$TOOLS/mei-$MEI_VERSION"

saxon() { java -cp "$CLASSPATH" net.sf.saxon.Transform "$@"; }

build() { # path to ODD
  local odd=$1 name source tmp
  name=$(basename "$odd" .odd)
  if grep -q "<schemaSpec[^>]*ns=\"$MEI_NS\"" "$odd"; then
    source=$MEI_SOURCE
  else
    source=$TEI_SOURCE
  fi
  tmp=$(mktemp -d)
  echo "Building schema/$name.rng from $(basename "$source")" >&2
  saxon -xi:on -s:"$odd" -xsl:"$STYLESHEETS/odds/odd2odd.xsl" \
    -o:"$tmp/$name.compiled.xml" defaultSource="$source"
  saxon -s:"$tmp/$name.compiled.xml" -xsl:"$STYLESHEETS/odds/odd2relax.xsl" \
    -o:"$SCHEMA_DIR/$name.rng"
  rm -rf "$tmp"
}

if [ $# -eq 0 ]; then
  set -- "$SCHEMA_DIR"/*.odd
fi
for odd in "$@"; do
  case "$odd" in
    */*) ;;
    *) odd="$SCHEMA_DIR/${odd%.odd}.odd" ;;
  esac
  build "$odd"
done
