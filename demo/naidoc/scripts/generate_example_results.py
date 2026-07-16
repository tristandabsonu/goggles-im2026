#!/usr/bin/env python3
"""Capture real Gemini assessor outputs for the static example-results page."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.assessment import (  # noqa: E402
    assess_application,
    extract_assessable_sections,
)
from backend.config import load_settings  # noqa: E402
from backend.documents import AssessorDocumentBundle, PdfDocument  # noqa: E402
from backend.models import AssessorCheckResult  # noqa: E402

NAIDOC_ROOT = PROJECT_ROOT / "demo" / "naidoc"
DOCUMENTS_ROOT = NAIDOC_ROOT / "documents"
PROPOSALS_ROOT = NAIDOC_ROOT / "test-cases" / "pdf"
DEFAULT_OUTPUT = PROJECT_ROOT / "frontend" / "src" / "data" / "example-results.json"
MODEL_ID = "gemini-3.5-flash"

GOG_PATH = DOCUMENTS_ROOT / (
    "NAIDOC 2026 Local Grants Opportunity - Grant Opportunity Guidelines.pdf"
)
APPLICATION_FORM_PATH = DOCUMENTS_ROOT / "NAIDOC 2026 - Sample Application Form.pdf"
APPLICANTS_GUIDE_PATH = DOCUMENTS_ROOT / (
    "NAIDOC 2026 Local Grants - Applicants Guide.pdf"
)

EXAMPLE_TAB_LABELS = {
    1: "01 · Out-of-scope costs",
    2: "02 · Vague budget lines",
    3: "03 · Funding stream",
    4: "04 · Criterion evidence",
    5: "05 · Missing bank evidence",
    6: "06 · Clean control",
}


def pdf_document(label: str, path: Path) -> PdfDocument:
    """Load one public or synthetic input PDF with its normal UI label."""

    return PdfDocument(label=label, filename=path.name, content=path.read_bytes())


def build_bundle(number: int) -> AssessorDocumentBundle:
    """Build the same four-box bundle used by the Assessor homepage demo."""

    proposal_path = PROPOSALS_ROOT / f"synthetic-application-{number:02d}.pdf"
    return AssessorDocumentBundle(
        gog=pdf_document("Selection Criteria (GOG)", GOG_PATH),
        application_form=pdf_document("Application Form", APPLICATION_FORM_PATH),
        supporting_documents=(
            pdf_document("Supporting Document", APPLICANTS_GUIDE_PATH),
        ),
        grant_application=pdf_document("Grant Application", proposal_path),
    )


def load_existing_examples(output_path: Path) -> dict[str, dict]:
    """Retain successful earlier captures when a later run is resumed."""

    if not output_path.exists():
        return {}
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    examples = {}
    for example in payload.get("examples", []):
        AssessorCheckResult.model_validate(example["result"])
        examples[example["id"]] = example
    return examples


def write_capture(output_path: Path, examples: dict[str, dict]) -> None:
    """Persist only validated structured results and benign provenance."""

    payload = {
        "schema_version": 1,
        "model": MODEL_ID,
        "model_label": "Gemini 3.5 Flash",
        "examples": sorted(examples.values(), key=lambda item: item["id"]),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def capture_example(number: int, settings) -> dict:
    """Run and validate one complete assessor workflow."""

    example_id = f"application_{number:02d}"
    proposal_filename = f"synthetic-application-{number:02d}.pdf"
    started_at = time.perf_counter()
    logging.info("%s capture started with %s", example_id, MODEL_ID)

    bundle = build_bundle(number)
    extraction = extract_assessable_sections(bundle, settings)
    result = AssessorCheckResult.model_validate(
        assess_application(bundle, extraction, settings)
    )
    duration_seconds = round(time.perf_counter() - started_at, 1)

    section_errors = [
        section.error for section in result.sections if section.error is not None
    ]
    if section_errors:
        raise RuntimeError(
            f"{example_id} returned section errors: {'; '.join(section_errors)}"
        )

    logging.info("%s capture completed in %.1fs", example_id, duration_seconds)
    return {
        "id": example_id,
        "tab_label": EXAMPLE_TAB_LABELS[number],
        "proposal_filename": proposal_filename,
        "model": MODEL_ID,
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "duration_seconds": duration_seconds,
        "result": result.model_dump(mode="json"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "applications",
        metavar="N",
        type=int,
        nargs="*",
        default=list(EXAMPLE_TAB_LABELS),
        choices=sorted(EXAMPLE_TAB_LABELS),
        help="Synthetic application numbers to capture (default: all six).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Capture destination (default: {DEFAULT_OUTPUT}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )

    settings = load_settings().model_copy(update={"gemini_model": MODEL_ID})
    examples = load_existing_examples(args.output)
    for number in args.applications:
        example = capture_example(number, settings)
        examples[example["id"]] = example
        write_capture(args.output, examples)


if __name__ == "__main__":
    main()
