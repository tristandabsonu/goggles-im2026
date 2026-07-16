#!/usr/bin/env bash
# Rebuild the synthetic test applications: Markdown -> DOCX (pandoc) ->
# styled DOCX -> PDF (LibreOffice). PDFs land in test-cases/pdf.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MARKDOWN_DIR="$ROOT/test-cases/source"
PDF_DIR="$ROOT/test-cases/pdf"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/home" "$WORK/config" "$WORK/runtime"
mkdir -p "$PDF_DIR"

python3 "$ROOT/scripts/generate_test_applications.py"

for md in "$MARKDOWN_DIR"/synthetic-application-*.md; do
    base="$(basename "$md" .md)"
    pandoc "$md" -o "$WORK/$base.docx"
    python3 "$ROOT/scripts/style_test_application_docx.py" "$WORK/$base.docx"
done

HOME="$WORK/home" XDG_CONFIG_HOME="$WORK/config" XDG_RUNTIME_DIR="$WORK/runtime" \
    libreoffice --headless -env:UserInstallation="file://$WORK/lo-profile" \
    --convert-to pdf --outdir "$WORK" "$WORK"/synthetic-application-*.docx

shopt -s nullglob
pdfs=("$WORK"/synthetic-application-*.pdf)
if ((${#pdfs[@]} != 6)); then
    echo "Expected 6 generated PDFs, found ${#pdfs[@]}" >&2
    exit 1
fi

for pdf in "${pdfs[@]}"; do
    cp "$pdf" "$PDF_DIR/$(basename "$pdf")"
done
