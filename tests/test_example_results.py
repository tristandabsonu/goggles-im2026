"""Checks for the captured synthetic outputs rendered by the examples page."""

import json
from pathlib import Path

from backend.models import AssessorCheckResult

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_RESULTS_PATH = (
    PROJECT_ROOT / "frontend" / "src" / "data" / "example-results.json"
)


def captured_result(application_id: str) -> AssessorCheckResult:
    """Load one retained result through the same schema used by the API."""

    payload = json.loads(EXAMPLE_RESULTS_PATH.read_text(encoding="utf-8"))
    example = next(
        item for item in payload["examples"] if item["id"] == application_id
    )
    return AssessorCheckResult.model_validate(example["result"])


def budget_classifications(result: AssessorCheckResult) -> dict[str, str]:
    budget = next(section for section in result.sections if section.id == "budget")
    return {item.item: item.classification for item in budget.budget_items}


def test_example_results_are_complete_validated_assessor_captures() -> None:
    payload = json.loads(EXAMPLE_RESULTS_PATH.read_text(encoding="utf-8"))

    assert payload["schema_version"] == 1
    assert payload["model"] == "gemini-3.5-flash"
    assert payload["model_label"] == "Gemini 3.5 Flash"
    assert [example["id"] for example in payload["examples"]] == [
        f"application_{number:02d}" for number in range(1, 7)
    ]

    for example in payload["examples"]:
        result = AssessorCheckResult.model_validate(example["result"])
        assert result.mode == "assessor"
        assert result.extracted_sections
        assert result.sections
        assert not any(section.error for section in result.sections)
        assert example["model"] == payload["model"]
        assert example["duration_seconds"] > 0
        assert example["proposal_filename"].endswith(".pdf")


def test_application_01_capture_has_only_the_planted_scope_findings() -> None:
    result = captured_result("application_01")
    budget = next(section for section in result.sections if section.type == "budget")
    classifications = {item.item: item.classification for item in budget.budget_items}

    assert classifications == {
        "Welcome to Country and cultural performances": "in_scope",
        "First Nations artist-led workshops": "in_scope",
        "Venue and event equipment hire": "in_scope",
        "NAIDOC T-shirts for participants": "out_of_scope",
        "Branded banners and social-media promotion": "out_of_scope",
    }
    assert all(
        any("5.4" in source.reference for source in item.sources)
        for item in budget.budget_items
        if item.classification == "out_of_scope"
    )


def test_application_02_capture_has_only_vague_budget_findings() -> None:
    result = captured_result("application_02")
    classifications = budget_classifications(result)

    assert classifications["Event delivery"] == "vague"
    assert classifications["Other"] == "vague"
    assert "out_of_scope" not in classifications.values()


def test_application_03_capture_has_the_conditional_stream_flag() -> None:
    result = captured_result("application_03")

    assert len(result.threshold_flags) == 1
    flag = result.threshold_flags[0]
    flag_text = f"{flag.comment} {flag.suggested_action}".lower()
    assert "1,500" in flag_text
    assert "determine" in flag_text
    assert any("2.1" in source.reference for source in flag.sources)


def test_application_04_capture_has_the_criterion_evidence_finding() -> None:
    result = captured_result("application_04")
    criterion = next(section for section in result.sections if section.id == "criterion_1")

    assert len(criterion.findings) == 1
    finding = criterion.findings[0]
    finding_text = f"{finding.comment} {finding.suggested_action}".lower()
    for expected in ("experience", "resources", "risk", "value"):
        assert expected in finding_text
    assert any(
        "criterion 1" in source.reference.lower()
        and "selection criteria" in source.document.lower()
        for source in finding.sources
    )


def test_application_05_capture_has_the_missing_bank_evidence_finding() -> None:
    result = captured_result("application_05")
    attachments = next(section for section in result.sections if section.id == "attachments")

    assert len(attachments.findings) == 1
    finding = attachments.findings[0]
    finding_text = f"{finding.comment} {finding.suggested_action}".lower()
    assert "bank" in finding_text
    assert "may not proceed" in finding_text
    assert any("7.1" in source.reference for source in finding.sources)


def test_application_06_capture_preserves_the_clean_control() -> None:
    result = captured_result("application_06")
    budget = next(section for section in result.sections if section.id == "budget")
    classifications = {item.item: item.classification for item in budget.budget_items}
    facilitators = next(
        item for item in budget.budget_items if item.item == "Cultural facilitators"
    )

    assert classifications["Cultural facilitators"] == "clarified_elsewhere"
    assert facilitators.clarification_evidence is not None
    assert all(
        classification in {"in_scope", "clarified_elsewhere"}
        for classification in classifications.values()
    )
    assert result.threshold_flags == []
    assert all(section.findings == [] for section in result.sections)
