#!/usr/bin/env bash
# Validate every XML file under encodings/ (or under the given files and
# directories) against the RELAX NG schema named in its xml-model
# processing instruction.
#
#   scripts/validate.sh
#   scripts/validate.sh encodings/3 encodings/works.xml
#
# Needs Java, Perl and Jing: set JING_JAR to the path of jing.jar, or put
# a `jing` command on the PATH. Schematron xml-model instructions are
# ignored. A file fails if it has no RELAX NG xml-model, if the schema is
# remote (use a copy in schema/ so that validation works offline) or
# missing, or if Jing reports an error. Exits 0 if every file is valid,
# 1 otherwise, 2 if Jing is not available.
set -uo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
RELAXNG_NS=http://relaxng.org/ns/structure/1.0

if [ -n "${JING_JAR:-}" ]; then
  jing=(java -jar "$JING_JAR")
elif command -v jing >/dev/null 2>&1; then
  jing=(jing)
else
  echo "Jing not found: set JING_JAR=/path/to/jing.jar or put jing on the PATH" >&2
  exit 2
fi

[ $# -gt 0 ] || set -- "$ROOT/encodings"

# Print the RELAX NG schemas that a document names in xml-model
# instructions before its root element, one href per line.
relaxng_hrefs() {
  perl -0777 -ne '
    my ($prolog) = /\A(.*?)<[A-Za-z_]/s or exit;
    while ($prolog =~ /<\?xml-model\s(.*?)\?>/sg) {
      my %att = $1 =~ /([\w-]+)\s*=\s*["\x27]([^"\x27]*)["\x27]/g;
      next unless defined $att{href};
      my $ns = $att{schematypens} // "";
      print "$att{href}\n"
        if $ns eq $ENV{RELAXNG_NS} || ($ns eq "" && $att{href} =~ /\.rng$/);
    }' "$1"
}
export RELAXNG_NS

failed=0
count=0
pairs=$(mktemp)
trap 'rm -f "$pairs"' EXIT

fail() { echo "$1: error: $2"; failed=1; }

while IFS= read -r -d '' file; do
  count=$((count + 1))
  rel=${file#"$ROOT"/}
  hrefs=$(relaxng_hrefs "$file")
  if [ -z "$hrefs" ]; then
    fail "$rel" "no RELAX NG schema declared in an xml-model processing instruction"
    continue
  fi
  while IFS= read -r href; do
    case "$href" in
      *://*) fail "$rel" "remote schema $href; point to a copy in schema/"; continue ;;
      /*) schema=$href ;;
      *) schema="$(dirname "$file")/$href" ;;
    esac
    if [ ! -f "$schema" ]; then
      fail "$rel" "schema $href not found"
      continue
    fi
    schema="$(cd "$(dirname "$schema")" && pwd)/$(basename "$schema")"
    printf '%s\t%s\n' "$schema" "$file" >> "$pairs"
  done <<< "$hrefs"
done < <(find "$@" -type f -name '*.xml' -print0 | sort -z)

# One Jing run per schema
while IFS= read -r schema; do
  files=()
  while IFS=$'\t' read -r s f; do
    [ "$s" = "$schema" ] && files+=("$f")
  done < "$pairs"
  "${jing[@]}" "$schema" "${files[@]}" | sed "s|$ROOT/||g"
  [ "${PIPESTATUS[0]}" -eq 0 ] || failed=1
done < <(cut -f1 "$pairs" | sort -u)

if [ $failed -eq 0 ]; then
  echo "All $count XML files are valid."
else
  echo "Validation failed." >&2
fi
exit $failed
