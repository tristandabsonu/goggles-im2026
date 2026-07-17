# NAIDOC demo data

This folder contains the only grant-program dataset used by the competition
prototype.

```text
documents/          Public 2026 NAIDOC opportunity PDFs
test-cases/pdf/     Six generated synthetic application PDFs used by the demo
test-cases/source/  Markdown source for those synthetic applications
test-cases/expected-results.md
                    Local human answer key; never send this file to Gemini
test-cases/applicant-smoke-test.md
                    Isolated applicant-view budget check
scripts/            Synthetic-document generation and styling scripts
```

`scripts/generate_example_results.py` runs the six fictional proposal bundles
through Gemini 3.5 Flash and writes validated structured captures to
`frontend/src/data/example-results.json`. It never reads or supplies the private
expected-results answer key.

Only public documents and explicitly synthetic applications are used. The
FastAPI demo-file allow-list exposes the GOG, Application Form, Applicants Guide
and six synthetic PDFs; it does not expose the answer key.

The retained public source documents are the GOG, sample Application Form and
Applicants Guide used by the demo. Other downloaded NAIDOC materials are not
kept because the prototype does not use them.

To regenerate the synthetic PDFs, run `scripts/build_test_documents.sh` from
this directory. The script requires `pdftotext`, Pandoc and LibreOffice.
