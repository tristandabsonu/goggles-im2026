from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from backend.assessment import (
    assess_application,
    assess_attachment_section,
    assess_budget_section,
    assess_criterion_section,
    assess_funding_stream_section,
    assess_applicant_budget_field,
    assess_applicant_text_field,
    extract_assessable_sections,
    iter_applicant_assessment_steps,
)
from backend.config import Settings
from backend.documents import (
    AssessorDocumentBundle,
    PdfDocument,
    ApplicantDocumentBundle,
)
from backend.models import (
    AssessmentFinding,
    AttachmentAssessmentResult,
    BudgetAssessmentResult,
    BudgetItemAssessment,
    ClarificationEvidence,
    CriterionAssessmentResult,
    ExtractedSection,
    FundingStreamAssessmentResult,
    SectionExtractionResult,
    SourceReference,
    ThresholdFlag,
    ApplicantDraftField,
    ApplicantFieldAssessmentResult,
)


class FakeMessages:
    def __init__(self, parsed_output: Any) -> None:
        self.request: dict[str, Any] | None = None
        self.parsed_output = parsed_output

    def generate_content(self, **kwargs: Any) -> SimpleNamespace:
        self.request = kwargs
        return SimpleNamespace(
            parsed=self.parsed_output,
            candidates=[SimpleNamespace(finish_reason="STOP")],
            usage_metadata=None,
        )


class InvalidJsonThenValidMessages:
    def __init__(self, parsed_output: ApplicantFieldAssessmentResult) -> None:
        self.parsed_output = parsed_output
        self.requests: list[dict[str, Any]] = []

    def generate_content(self, **kwargs: Any) -> SimpleNamespace:
        self.requests.append(kwargs)
        if len(self.requests) == 1:
            ApplicantFieldAssessmentResult.model_validate_json(
                '{"section_id":"activity_description","findings":[{"comment":"cut'
            )
        return SimpleNamespace(
            parsed=self.parsed_output,
            candidates=[SimpleNamespace(finish_reason="STOP")],
            usage_metadata=None,
        )


def _part_text(part: Any) -> str:
    return getattr(part, "text", None) or ""


def _document_labels(contents: list[Any]) -> list[str]:
    prefix = "Document label: "
    return [
        _part_text(part).removeprefix(prefix)
        for part in contents
        if _part_text(part).startswith(prefix)
    ]


def _source(reference: str = "section 5.4") -> SourceReference:
    return SourceReference(
        document="GOG",
        reference=reference,
        excerpt="Synthetic supporting rule text.",
    )


def test_actionable_results_require_a_usable_source() -> None:
    with pytest.raises(ValidationError):
        SourceReference(document=" ", reference="section 5.4", excerpt="Rule")

    with pytest.raises(ValidationError, match="require a source"):
        BudgetItemAssessment(
            item="Other",
            amount="$1,000",
            classification="vague",
            comment="The purpose is unclear.",
            suggested_action="Itemise the cost.",
            sources=[],
        )

    with pytest.raises(ValidationError):
        ThresholdFlag(
            code="funding_stream_review",
            comment="Review the selected stream.",
            suggested_action="Determine the applicable stream.",
            sources=[],
        )

    with pytest.raises(ValidationError):
        AssessmentFinding(
            comment="More evidence is needed.",
            suggested_action="Clarify the response.",
            sources=[],
        )

    clear_item = BudgetItemAssessment(
        item="Venue hire",
        amount="$1,000",
        classification="in_scope",
        comment="",
        suggested_action="",
        sources=[],
    )
    assert clear_item.sources == []


def test_section_extraction_uses_only_form_and_application_pdfs() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(PdfDocument("Guide", "guide.pdf", b"%PDF-1.7\nguide"),),
        grant_application=PdfDocument(
            "Grant Application",
            "application.pdf",
            b"%PDF-1.7\napplication",
        ),
    )
    extracted = SectionExtractionResult(
        sections=[
            ExtractedSection(
                id="budget",
                header="Budget",
                type="budget",
                text="Cultural facilitators: $3,000",
                order=2,
                source_pages=[18],
            ),
            ExtractedSection(
                id="activity_description",
                header="Activity description",
                type="description",
                text="A free community event.",
                order=1,
                source_pages=[12],
            ),
        ]
    )
    messages = FakeMessages(extracted)
    client = SimpleNamespace(models=messages)

    result = extract_assessable_sections(
        bundle,
        settings,
        client=client,  # type: ignore[arg-type]
    )

    assert [section.id for section in result.sections] == [
        "activity_description",
        "budget",
    ]
    assert messages.request is not None
    content = messages.request["contents"]
    assert _document_labels(content) == [
        "Application Form: form",
        "Grant Application: application",
    ]
    assert all("GOG:" not in _part_text(part) for part in content)


def test_budget_assessment_receives_the_complete_bundle() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(PdfDocument("Guide", "guide.pdf", b"%PDF-1.7\nguide"),),
        grant_application=PdfDocument(
            "Grant Application",
            "application.pdf",
            b"%PDF-1.7\napplication",
        ),
    )
    budget_section = ExtractedSection(
        id="budget",
        header="Budget",
        type="budget",
        text="NAIDOC T-shirts: $1,000",
        order=1,
        source_pages=[18],
    )
    assessed = BudgetAssessmentResult(
        section_id="budget",
        items=[
            BudgetItemAssessment(
                item="NAIDOC T-shirts",
                amount="$1,000",
                classification="out_of_scope",
                comment="Grant funding cannot pay for T-shirts.",
                suggested_action="Review how this cost will be funded.",
                sources=[
                    SourceReference(
                        document="GOG",
                        reference="section 5.4",
                        excerpt="T-shirts are out of scope.",
                    )
                ],
            )
        ],
    )
    messages = FakeMessages(assessed)
    client = SimpleNamespace(models=messages)

    result = assess_budget_section(
        bundle,
        budget_section,
        settings,
        client=client,  # type: ignore[arg-type]
    )

    assert result.items[0].classification == "out_of_scope"
    assert messages.request is not None
    content = messages.request["contents"]
    assert _document_labels(content) == [
        "GOG: gog",
        "Application Form: form",
        "Guide: guide",
        "Grant Application: application",
    ]
    assert "NAIDOC T-shirts: $1,000" in _part_text(content[-1])
    assert "do not use broader appendix material alone" in _part_text(content[-1])


def test_verified_budget_clarification_is_preserved() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(),
        grant_application=PdfDocument(
            "Grant Application",
            "application.pdf",
            b"%PDF-1.7\napplication",
        ),
    )
    budget = ExtractedSection(
        id="budget",
        header="Budget",
        type="budget",
        text="Cultural facilitators: $3,000",
        order=2,
        source_pages=[19],
    )
    activity = ExtractedSection(
        id="activity_description",
        header="Activity description",
        type="description",
        text=(
            "Two facilitators will each lead three sessions at $500 per session, "
            "totalling $3,000."
        ),
        order=1,
        source_pages=[14],
    )
    evidence = ClarificationEvidence(
        source_section_id="activity_description",
        source_section="Unverified model heading",
        source_pages=[999],
        excerpt=activity.text,
        basis="quantity_rate",
        resolved_amount="$3,000",
    )
    messages = FakeMessages(
        BudgetAssessmentResult(
            section_id="budget",
            items=[
                BudgetItemAssessment(
                    item="Cultural facilitators",
                    amount="$3,000",
                    classification="clarified_elsewhere",
                    comment="The amount is explained in the activity description.",
                    suggested_action="Verify the cited calculation.",
                    sources=[_source()],
                    clarification_evidence=evidence,
                )
            ],
        )
    )

    result = assess_budget_section(
        bundle,
        budget,
        settings,
        context_sections=[activity, budget],
        client=SimpleNamespace(models=messages),  # type: ignore[arg-type]
    )

    assert result.items[0].classification == "clarified_elsewhere"
    assert result.items[0].clarification_evidence is not None
    assert result.items[0].clarification_evidence.source_section == activity.header
    assert result.items[0].clarification_evidence.source_pages == activity.source_pages
    assert messages.request is not None
    assert "Section ID: activity_description" in _part_text(
        messages.request["contents"][-1]
    )
    assert activity.text in _part_text(messages.request["contents"][-1])


def test_unreconciled_budget_clarification_is_downgraded_to_vague() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(),
        grant_application=PdfDocument(
            "Grant Application",
            "application.pdf",
            b"%PDF-1.7\napplication",
        ),
    )
    budget = ExtractedSection(
        id="budget",
        header="Budget",
        type="budget",
        text="Event delivery: $5,500",
        order=2,
        source_pages=[19],
    )
    activity = ExtractedSection(
        id="activity_description",
        header="Activity description",
        type="description",
        text="The event will include storytelling, weaving and conversation.",
        order=1,
        source_pages=[14],
    )
    messages = FakeMessages(
        BudgetAssessmentResult(
            section_id="budget",
            items=[
                BudgetItemAssessment(
                    item="Event delivery",
                    amount="$5,500",
                    classification="clarified_elsewhere",
                    comment="The event is described elsewhere.",
                    suggested_action="Verify the description.",
                    sources=[_source()],
                    clarification_evidence=ClarificationEvidence(
                        source_section_id="activity_description",
                        source_section="Activity description",
                        source_pages=[14],
                        excerpt=activity.text,
                        basis="component_breakdown",
                        resolved_amount="$5,500",
                    ),
                )
            ],
        )
    )

    result = assess_budget_section(
        bundle,
        budget,
        settings,
        context_sections=[activity, budget],
        client=SimpleNamespace(models=messages),  # type: ignore[arg-type]
    )

    item = result.items[0]
    assert item.classification == "vague"
    assert "verifiable breakdown" in item.comment
    assert item.clarification_evidence is None


def test_applicant_budget_call_keeps_a_stable_applicant_facing_prefix() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = ApplicantDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(PdfDocument("Guide", "guide.pdf", b"%PDF-1.7\nguide"),),
    )
    field = ApplicantDraftField(
        id="budget",
        header="Budget",
        type="budget",
        text="Other: $1,000",
        order=1,
    )
    messages = FakeMessages(BudgetAssessmentResult(section_id="budget", items=[]))
    client = SimpleNamespace(models=messages)

    assess_applicant_budget_field(
        bundle,
        field,
        settings,
        client=client,  # type: ignore[arg-type]
    )

    content = messages.request["contents"]
    assert _document_labels(content) == [
        "GOG: gog",
        "Application Form: form",
        "Guide: guide",
    ]
    assert messages.request["config"].max_output_tokens == 5_000
    assert "Other: $1,000" in _part_text(content[-1])
    assert "do not use broader appendix material alone" in _part_text(content[-1])


def test_funding_stream_assessment_receives_the_complete_bundle() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(PdfDocument("Guide", "guide.pdf", b"%PDF-1.7\nguide"),),
        grant_application=PdfDocument(
            "Grant Application",
            "application.pdf",
            b"%PDF-1.7\napplication",
        ),
    )
    funding_stream = ExtractedSection(
        id="funding_stream",
        header="Funding stream",
        type="generic",
        text="Stream Two; $6,000 requested",
        order=1,
        source_pages=[12],
    )
    assessed = FundingStreamAssessmentResult(
        section_id="funding_stream",
        selected_stream="Stream Two",
        requested_amount="$6,000",
        threshold_flags=[
            ThresholdFlag(
                code="funding_stream_review",
                comment="The application appears to require Stream One consideration.",
                suggested_action="NIAA should determine the applicable stream.",
                sources=[
                    SourceReference(
                        document="GOG",
                        reference="section 2.1",
                        excerpt="Educational institutions must apply under Stream One.",
                    )
                ],
            )
        ],
    )
    messages = FakeMessages(assessed)
    client = SimpleNamespace(models=messages)

    result = assess_funding_stream_section(
        bundle,
        funding_stream,
        settings,
        client=client,  # type: ignore[arg-type]
    )

    assert result.threshold_flags[0].code == "funding_stream_review"
    assert messages.request is not None
    content = messages.request["contents"]
    assert _document_labels(content) == [
        "GOG: gog",
        "Application Form: form",
        "Guide: guide",
        "Grant Application: application",
    ]
    assert "Stream Two; $6,000 requested" in _part_text(content[-1])


def test_criterion_assessment_receives_the_complete_bundle() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(),
        grant_application=PdfDocument(
            "Grant Application",
            "application.pdf",
            b"%PDF-1.7\napplication",
        ),
    )
    criterion = ExtractedSection(
        id="criterion_1",
        header="Criterion 1",
        type="generic",
        text="We have experience and will manage risks.",
        order=1,
        source_pages=[15],
    )
    assessed = CriterionAssessmentResult(
        section_id="criterion_1",
        findings=[
            AssessmentFinding(
                comment="The assertions lack concrete evidence.",
                suggested_action="Clarify the applicant's supporting evidence.",
                sources=[
                    SourceReference(
                        document="GOG",
                        reference="section 6",
                        excerpt="Applications are assessed against the criterion.",
                    )
                ],
            )
        ],
    )
    messages = FakeMessages(assessed)
    client = SimpleNamespace(models=messages)

    result = assess_criterion_section(
        bundle,
        criterion,
        settings,
        client=client,  # type: ignore[arg-type]
    )

    assert result.findings[0].comment == "The assertions lack concrete evidence."
    assert messages.request is not None
    content = messages.request["contents"]
    assert _document_labels(content) == [
        "GOG: gog",
        "Application Form: form",
        "Grant Application: application",
    ]
    assert "We have experience and will manage risks." in _part_text(content[-1])


def test_attachment_assessment_receives_the_complete_bundle() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(),
        grant_application=PdfDocument(
            "Grant Application",
            "application.pdf",
            b"%PDF-1.7\napplication",
        ),
    )
    attachments = ExtractedSection(
        id="attachments",
        header="Attachments",
        type="generic",
        text="Bank account verification: Not provided",
        order=1,
        source_pages=[24],
    )
    assessed = AttachmentAssessmentResult(
        section_id="attachments",
        findings=[
            AssessmentFinding(
                comment="Mandatory bank evidence is not listed.",
                suggested_action="Confirm the package and determine next steps.",
                sources=[
                    SourceReference(
                        document="GOG",
                        reference="section 7.1",
                        excerpt="Bank verification must accompany all applications.",
                    )
                ],
            )
        ],
    )
    messages = FakeMessages(assessed)
    client = SimpleNamespace(models=messages)

    result = assess_attachment_section(
        bundle,
        attachments,
        settings,
        client=client,  # type: ignore[arg-type]
    )

    assert result.findings[0].comment == "Mandatory bank evidence is not listed."
    assert messages.request is not None
    assert messages.request["config"].max_output_tokens == 5_000
    content = messages.request["contents"]
    assert _document_labels(content) == [
        "GOG: gog",
        "Application Form: form",
        "Grant Application: application",
    ]
    assert "Bank account verification: Not provided" in _part_text(content[-1])


def test_combined_assessment_preserves_order_and_threshold_flags(
    monkeypatch,
) -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(),
        grant_application=PdfDocument(
            "Grant Application",
            "application.pdf",
            b"%PDF-1.7\napplication",
        ),
    )
    funding_stream = ExtractedSection(
        id="funding_stream",
        header="Funding stream",
        type="generic",
        text="Stream Two; $6,000",
        order=2,
        source_pages=[12],
    )
    budget = ExtractedSection(
        id="budget",
        header="Budget",
        type="budget",
        text="Other: $1,000",
        order=6,
        source_pages=[19],
    )
    extraction = SectionExtractionResult(sections=[budget, funding_stream])
    flag = ThresholdFlag(
        code="funding_stream_review",
        comment="Review the selected stream.",
        suggested_action="NIAA should determine the stream.",
        sources=[
            SourceReference(
                document="GOG",
                reference="section 2.1",
                excerpt="Stream rules.",
            )
        ],
    )

    monkeypatch.setattr(
        "backend.assessment.assess_funding_stream_section",
        lambda bundle, section, settings: FundingStreamAssessmentResult(
            section_id="funding_stream",
            selected_stream="Stream Two",
            requested_amount="$6,000",
            threshold_flags=[flag],
        ),
    )
    monkeypatch.setattr(
        "backend.assessment.assess_budget_section",
        lambda bundle, section, settings, **kwargs: BudgetAssessmentResult(
            section_id="budget",
            items=[
                BudgetItemAssessment(
                    item="Other",
                    amount="$1,000",
                    classification="vague",
                    comment="The purpose is unclear.",
                    suggested_action="Clarify and itemise this cost.",
                    sources=[_source("Appendix 4")],
                )
            ],
        ),
    )

    result = assess_application(bundle, extraction, settings)

    assert result.extracted_sections == extraction.sections
    assert [section.id for section in result.sections] == [
        "funding_stream",
        "budget",
    ]
    assert result.threshold_flags == [flag]
    funding_result = next(
        section for section in result.sections if section.id == "funding_stream"
    )
    assert funding_result.has_threshold_flag is True


def test_applicant_budget_call_contains_only_applicant_sources_and_target_field() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = ApplicantDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(PdfDocument("Guide", "guide.pdf", b"%PDF-1.7\nguide"),),
    )
    field = ApplicantDraftField(
        id="budget",
        header="Budget",
        type="budget",
        text="Event delivery: $5,500",
        order=1,
    )
    assessed = BudgetAssessmentResult(
        section_id="budget",
        items=[
            BudgetItemAssessment(
                item="Event delivery",
                amount="$5,500",
                classification="vague",
                comment="The components are unclear.",
                suggested_action="Itemise the separate costs.",
                sources=[_source("Appendix 4")],
            )
        ],
    )
    messages = FakeMessages(assessed)
    client = SimpleNamespace(models=messages)

    result = assess_applicant_budget_field(
        bundle,
        field,
        settings,
        client=client,  # type: ignore[arg-type]
    )

    assert result.items[0].classification == "vague"
    assert messages.request is not None
    content = messages.request["contents"]
    assert _document_labels(content) == [
        "GOG: gog",
        "Application Form: form",
        "Guide: guide",
    ]
    assert "Event delivery: $5,500" in _part_text(content[-1])
    assert all(
        "activity description sentinel" not in _part_text(part).lower()
        for part in content
    )


def test_applicant_budget_clarification_is_downgraded_and_evidence_removed() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = ApplicantDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(),
    )
    field = ApplicantDraftField(
        id="budget",
        header="Budget",
        type="budget",
        text="Event delivery: $5,500",
        order=1,
    )
    assessed = BudgetAssessmentResult(
        section_id="budget",
        items=[
            BudgetItemAssessment(
                item="Event delivery",
                amount="$5,500",
                classification="clarified_elsewhere",
                comment="The amount is explained in the activity description.",
                suggested_action="Verify the description.",
                sources=[_source("Appendix 4")],
                clarification_evidence=ClarificationEvidence(
                    source_section_id="activity_description",
                    source_section="Activity description",
                    source_pages=[14],
                    excerpt="Event delivery totals $5,500.",
                    basis="explicit_total",
                    resolved_amount="$5,500",
                ),
            )
        ],
    )

    result = assess_applicant_budget_field(
        bundle,
        field,
        settings,
        client=SimpleNamespace(models=FakeMessages(assessed)),  # type: ignore[arg-type]
    )

    item = result.items[0]
    assert item.classification == "vague"
    assert "in this field" in item.comment
    assert "budget field" in item.suggested_action
    assert item.clarification_evidence is None


def test_applicant_budget_removes_stray_clarification_evidence() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = ApplicantDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(),
    )
    field = ApplicantDraftField(
        id="budget",
        header="Budget",
        type="budget",
        text="Venue hire: $2,000",
        order=1,
    )
    assessed = BudgetAssessmentResult(
        section_id="budget",
        items=[
            BudgetItemAssessment(
                item="Venue hire",
                amount="$2,000",
                classification="in_scope",
                comment="",
                suggested_action="",
                sources=[],
                clarification_evidence=ClarificationEvidence(
                    source_section_id="activity_description",
                    source_section="Activity description",
                    source_pages=[14],
                    excerpt="Venue hire totals $2,000.",
                    basis="explicit_total",
                    resolved_amount="$2,000",
                ),
            )
        ],
    )

    result = assess_applicant_budget_field(
        bundle,
        field,
        settings,
        client=SimpleNamespace(models=FakeMessages(assessed)),  # type: ignore[arg-type]
    )

    item = result.items[0]
    assert item.classification == "in_scope"
    assert item.clarification_evidence is None


def test_applicant_description_call_is_isolated_and_uses_grounded_feedback() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = ApplicantDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(PdfDocument("Guide", "guide.pdf", b"%PDF-1.7\nguide"),),
    )
    field = ApplicantDraftField(
        id="activity_description",
        header="Activity description and alignment",
        type="description",
        text="We will hold a community event.",
        order=1,
    )
    assessed = ApplicantFieldAssessmentResult(
        section_id="activity_description",
        findings=[
            AssessmentFinding(
                comment="The activity's alignment with the objectives is unclear.",
                suggested_action="Explain how the activity supports a relevant objective.",
                sources=[
                    SourceReference(
                        document="GOG",
                        reference="section 3.1",
                        excerpt="The grant opportunity objectives include cultural expression.",
                    )
                ],
            )
        ],
    )
    messages = FakeMessages(assessed)
    client = SimpleNamespace(models=messages)

    result = assess_applicant_text_field(
        bundle,
        field,
        settings,
        client=client,  # type: ignore[arg-type]
    )

    assert result.findings[0].suggested_action.startswith("Explain how")
    assert messages.request is not None
    assert messages.request["config"].response_schema is ApplicantFieldAssessmentResult
    content = messages.request["contents"]
    assert _document_labels(content) == [
        "GOG: gog",
        "Application Form: form",
        "Guide: guide",
    ]
    assert "We will hold a community event." in _part_text(content[-1])
    assert all(
        "organisation description sentinel" not in _part_text(part).lower()
        for part in content
    )


def test_applicant_attachment_call_checks_only_the_listed_manifest() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = ApplicantDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(PdfDocument("Guide", "guide.pdf", b"%PDF-1.7\nguide"),),
    )
    field = ApplicantDraftField(
        id="attachments",
        header="Attachment checklist",
        type="attachments",
        text="1. support-letter.pdf | Represents: Community letter of support",
        order=3,
    )
    assessed = ApplicantFieldAssessmentResult(
        section_id="attachments",
        findings=[
            AssessmentFinding(
                comment="Bank-account verification is not listed.",
                suggested_action="Confirm that the intended package includes it.",
                sources=[_source("section 7.1")],
            )
        ],
    )
    messages = FakeMessages(assessed)

    result = assess_applicant_text_field(
        bundle,
        field,
        settings,
        client=SimpleNamespace(models=messages),  # type: ignore[arg-type]
    )

    assert result.section_id == "attachments"
    assert messages.request is not None
    assert messages.request["config"].response_schema is ApplicantFieldAssessmentResult
    content = messages.request["contents"]
    assert _document_labels(content) == [
        "GOG: gog",
        "Application Form: form",
        "Guide: guide",
    ]
    prompt = _part_text(content[-1])
    assert "support-letter.pdf" in prompt
    assert "No other applicant answer" in prompt
    assert "attachment file is available" in prompt
    assert "Do not claim to have" in prompt
    assert "opened, authenticated or verified" in prompt


def test_applicant_steps_combine_text_attachment_and_budget_feedback(
    monkeypatch,
) -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = ApplicantDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(),
    )
    fields = [
        ApplicantDraftField(
            id="budget",
            header="Budget",
            type="budget",
            text="Other: $1,000",
            order=2,
        ),
        ApplicantDraftField(
            id="activity_description",
            header="Activity description and alignment",
            type="description",
            text="We will hold a community event.",
            order=1,
        ),
        ApplicantDraftField(
            id="attachments",
            header="Attachment checklist",
            type="attachments",
            text="No attachments listed.",
            order=3,
        ),
    ]
    called = []

    def fake_text(bundle, field, settings):
        called.append(field.id)
        return ApplicantFieldAssessmentResult(
            section_id=field.id,
            findings=[
                AssessmentFinding(
                    comment="Alignment needs more explanation.",
                    suggested_action="Explain the relevant objective.",
                    sources=[_source("section 3")],
                )
            ],
        )

    def fake_budget(bundle, field, settings):
        called.append(field.id)
        return BudgetAssessmentResult(
            section_id=field.id,
            items=[
                BudgetItemAssessment(
                    item="Other",
                    amount="$1,000",
                    classification="vague",
                    comment="The purpose is unclear.",
                    suggested_action="Name and itemise this cost.",
                    sources=[_source("Appendix 4")],
                )
            ],
        )

    monkeypatch.setattr("backend.assessment.assess_applicant_text_field", fake_text)
    monkeypatch.setattr("backend.assessment.assess_applicant_budget_field", fake_budget)

    steps = iter_applicant_assessment_steps(bundle, fields, settings)
    progress = []
    while True:
        try:
            field, current, total = next(steps)
            progress.append((field.id, current, total))
        except StopIteration as completed:
            result = completed.value
            break

    assert called == ["activity_description", "budget", "attachments"]
    assert progress == [
        ("activity_description", 1, 3),
        ("budget", 2, 3),
        ("attachments", 3, 3),
    ]
    assert [section.id for section in result.sections] == [
        "activity_description",
        "budget",
        "attachments",
    ]
    assert result.sections[0].findings
    assert result.sections[1].budget_items[0].classification == "vague"
    assert result.sections[2].type == "attachments"


def test_applicant_text_field_retries_once_after_invalid_structured_json() -> None:
    settings = Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        _env_file=None,
    )
    bundle = ApplicantDocumentBundle(
        gog=PdfDocument("GOG", "gog.pdf", b"%PDF-1.7\ngog"),
        application_form=PdfDocument(
            "Application Form",
            "form.pdf",
            b"%PDF-1.7\nform",
        ),
        supporting_documents=(),
    )
    field = ApplicantDraftField(
        id="activity_description",
        header="Activity description and alignment",
        type="description",
        text="A clear, isolated activity description.",
        order=1,
    )
    messages = InvalidJsonThenValidMessages(
        ApplicantFieldAssessmentResult(
            section_id="activity_description",
            findings=[],
        )
    )
    client = SimpleNamespace(models=messages)

    result = assess_applicant_text_field(
        bundle,
        field,
        settings,
        client=client,  # type: ignore[arg-type]
    )

    assert result.findings == []
    assert len(messages.requests) == 2
    assert messages.requests[0]["config"].max_output_tokens == 5_000
    retry_content = messages.requests[1]["contents"]
    assert "previous response was incomplete" in _part_text(retry_content[-1])
    assert "A clear, isolated activity description." in _part_text(retry_content[-1])
