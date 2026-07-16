"""Opt-in test that spends Gemini Developer API credit."""

import os
from pathlib import Path

import pytest

from backend.assessment import (
    assess_attachment_section,
    assess_budget_section,
    assess_criterion_section,
    assess_funding_stream_section,
    assess_writer_budget_field,
    assess_writer_text_field,
    extract_assessable_sections,
)
from backend.config import load_settings
from backend.documents import (
    AssessorDocumentBundle,
    PdfDocument,
    WriterDocumentBundle,
)
from backend.models import ExtractedSection, WriterDraftField

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NAIDOC_ROOT = PROJECT_ROOT / "demo" / "naidoc"
NAIDOC_DOCUMENTS = NAIDOC_ROOT / "documents"
NAIDOC_TEST_PDFS = NAIDOC_ROOT / "test-cases" / "pdf"
APPLICATION_FORM_PATH = NAIDOC_DOCUMENTS / ("NAIDOC 2026 - Sample Application Form.pdf")
GOG_PATH = NAIDOC_DOCUMENTS / (
    "NAIDOC 2026 Local Grants Opportunity - Grant Opportunity Guidelines.pdf"
)
APPLICANTS_GUIDE_PATH = NAIDOC_DOCUMENTS / (
    "NAIDOC 2026 Local Grants - Applicants Guide.pdf"
)
SYNTHETIC_APPLICATION_01_PATH = NAIDOC_TEST_PDFS / "synthetic-application-01.pdf"
SYNTHETIC_APPLICATION_02_PATH = NAIDOC_TEST_PDFS / "synthetic-application-02.pdf"
SYNTHETIC_APPLICATION_03_PATH = NAIDOC_TEST_PDFS / "synthetic-application-03.pdf"
SYNTHETIC_APPLICATION_04_PATH = NAIDOC_TEST_PDFS / "synthetic-application-04.pdf"
SYNTHETIC_APPLICATION_05_PATH = NAIDOC_TEST_PDFS / "synthetic-application-05.pdf"
SYNTHETIC_APPLICATION_06_PATH = NAIDOC_TEST_PDFS / "synthetic-application-06.pdf"

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        os.getenv("RUN_LIVE_TESTS") != "1",
        reason="Set RUN_LIVE_TESTS=1 to allow a paid Gemini API call.",
    ),
]


def test_gemini_extracts_sections_from_synthetic_application() -> None:
    settings = load_settings()
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", GOG_PATH.name, GOG_PATH.read_bytes()),
        application_form=PdfDocument(
            "Application Form",
            APPLICATION_FORM_PATH.name,
            APPLICATION_FORM_PATH.read_bytes(),
        ),
        supporting_documents=(),
        grant_application=PdfDocument(
            "Grant Application",
            SYNTHETIC_APPLICATION_01_PATH.name,
            SYNTHETIC_APPLICATION_01_PATH.read_bytes(),
        ),
    )

    result = extract_assessable_sections(bundle, settings)

    budget_sections = [
        section for section in result.sections if section.type == "budget"
    ]
    assert len(budget_sections) == 1
    assert "NAIDOC T-shirts" in budget_sections[0].text
    assert any(section.type == "description" for section in result.sections)


@pytest.mark.parametrize(
    ("application_path", "section_id", "expected_text"),
    [
        (SYNTHETIC_APPLICATION_03_PATH, "funding_stream", "Stream Two"),
        (SYNTHETIC_APPLICATION_04_PATH, "criterion_1", "usual processes"),
        (SYNTHETIC_APPLICATION_05_PATH, "attachments", "Not provided"),
    ],
    ids=["application-03", "application-04", "application-05"],
)
def test_gemini_extracts_sections_used_by_combined_assessment(
    application_path: Path,
    section_id: str,
    expected_text: str,
) -> None:
    settings = load_settings()
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", GOG_PATH.name, GOG_PATH.read_bytes()),
        application_form=PdfDocument(
            "Application Form",
            APPLICATION_FORM_PATH.name,
            APPLICATION_FORM_PATH.read_bytes(),
        ),
        supporting_documents=(),
        grant_application=PdfDocument(
            "Grant Application",
            application_path.name,
            application_path.read_bytes(),
        ),
    )

    result = extract_assessable_sections(bundle, settings)

    section = next(item for item in result.sections if item.id == section_id)
    assert expected_text.lower() in section.text.lower()


def test_gemini_finds_only_the_planted_out_of_scope_budget_items() -> None:
    settings = load_settings()
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", GOG_PATH.name, GOG_PATH.read_bytes()),
        application_form=PdfDocument(
            "Application Form",
            APPLICATION_FORM_PATH.name,
            APPLICATION_FORM_PATH.read_bytes(),
        ),
        supporting_documents=(),
        grant_application=PdfDocument(
            "Grant Application",
            SYNTHETIC_APPLICATION_01_PATH.name,
            SYNTHETIC_APPLICATION_01_PATH.read_bytes(),
        ),
    )
    budget = ExtractedSection(
        id="budget",
        header="Budget",
        type="budget",
        text=(
            "Welcome to Country and cultural performances | $3,200.00\n"
            "First Nations artist-led workshops | $2,400.00\n"
            "Venue and event equipment hire | $1,400.00\n"
            "NAIDOC T-shirts for participants | $1,000.00\n"
            "Branded banners and social-media promotion | $800.00"
        ),
        order=6,
        source_pages=[19, 20],
    )
    result = assess_budget_section(bundle, budget, settings)

    assert {item.item: item.classification for item in result.items} == {
        "Welcome to Country and cultural performances": "in_scope",
        "First Nations artist-led workshops": "in_scope",
        "Venue and event equipment hire": "in_scope",
        "NAIDOC T-shirts for participants": "out_of_scope",
        "Branded banners and social-media promotion": "out_of_scope",
    }
    assert all(
        any("5.4" in source.reference for source in item.sources)
        for item in result.items
        if item.classification == "out_of_scope"
    )


def test_gemini_flags_vague_budget_items_without_inventing_scope() -> None:
    settings = load_settings()
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", GOG_PATH.name, GOG_PATH.read_bytes()),
        application_form=PdfDocument(
            "Application Form",
            APPLICATION_FORM_PATH.name,
            APPLICATION_FORM_PATH.read_bytes(),
        ),
        supporting_documents=(),
        grant_application=PdfDocument(
            "Grant Application",
            SYNTHETIC_APPLICATION_02_PATH.name,
            SYNTHETIC_APPLICATION_02_PATH.read_bytes(),
        ),
    )
    budget = ExtractedSection(
        id="budget",
        header="Budget",
        type="budget",
        text=(
            "Event delivery | $5,500.00\n"
            "Materials and supplies | $2,500.00\n"
            "Other | $1,000.00"
        ),
        order=6,
        source_pages=[19, 20],
    )
    activity = ExtractedSection(
        id="activity_description",
        header="Activity description and alignment",
        type="description",
        text=(
            "Harbour Lights Community Association will hold a free afternoon "
            "gathering in Newcastle on 18 July 2026. First Nations cultural "
            "practitioners will share stories with families, lead introductory "
            "weaving activities and facilitate a community conversation about "
            "local histories and cultural continuity. The association's First "
            "Nations-controlled committee shaped the program and volunteers will "
            "welcome participants and assist with accessibility. The activity "
            "supports cultural expression, intergenerational engagement and "
            "broader understanding of First Nations cultures."
        ),
        order=3,
        source_pages=[14],
    )

    result = assess_budget_section(
        bundle,
        budget,
        settings,
        context_sections=[activity, budget],
    )

    classifications = {item.item: item.classification for item in result.items}
    assert classifications["Event delivery"] == "vague"
    assert classifications["Other"] == "vague"
    assert "out_of_scope" not in classifications.values()


def test_gemini_uses_application_context_and_excludes_donations() -> None:
    settings = load_settings()
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", GOG_PATH.name, GOG_PATH.read_bytes()),
        application_form=PdfDocument(
            "Application Form",
            APPLICATION_FORM_PATH.name,
            APPLICATION_FORM_PATH.read_bytes(),
        ),
        supporting_documents=(),
        grant_application=PdfDocument(
            "Grant Application",
            SYNTHETIC_APPLICATION_06_PATH.name,
            SYNTHETIC_APPLICATION_06_PATH.read_bytes(),
        ),
    )
    budget = ExtractedSection(
        id="budget",
        header="Budget",
        type="budget",
        text=(
            "Cultural facilitators | $3,000.00\n"
            "First Nations weaving and visual-art workshop facilitators | "
            "$2,500.00\n"
            "Venue PA and equipment hire | $1,800.00\n"
            "Bush-tucker cooking demonstration ingredients and equipment "
            "hire | $1,400.00\n"
            "Event first-aid services | $700.00"
        ),
        order=6,
        source_pages=[19, 20],
    )
    activity = ExtractedSection(
        id="activity_description",
        header="Activity description and alignment",
        type="description",
        text=(
            "River Plains Community Association will hold a free family cultural "
            "arts and storytelling day in Dubbo on 22 August 2026. Two confirmed "
            "First Nations cultural facilitators will each lead three storytelling "
            "and cultural-learning sessions at $500 per session, totalling $3,000. "
            "Other First Nations artists will deliver weaving and visual-art "
            "workshops, and a cooking demonstrator will share knowledge through a "
            "bush-tucker activity. The First Nations-controlled committee designed "
            "the program to strengthen cultural expression, enable intergenerational "
            "participation and promote respectful community understanding of First "
            "Nations histories, cultures and achievements."
        ),
        order=3,
        source_pages=[14],
    )

    result = assess_budget_section(
        bundle,
        budget,
        settings,
        context_sections=[activity, budget],
    )

    classifications = {item.item: item.classification for item in result.items}
    assert classifications["Cultural facilitators"] == "clarified_elsewhere"
    facilitator = next(
        item for item in result.items if item.item == "Cultural facilitators"
    )
    assert facilitator.clarification_evidence is not None
    assert facilitator.clarification_evidence.resolved_amount in {
        "$3,000",
        "$3,000.00",
    }
    assert len(result.items) == 5
    assert all("t-shirt" not in item.item.lower() for item in result.items)


def test_gemini_flags_the_stream_for_human_review() -> None:
    settings = load_settings()
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", GOG_PATH.name, GOG_PATH.read_bytes()),
        application_form=PdfDocument(
            "Application Form",
            APPLICATION_FORM_PATH.name,
            APPLICATION_FORM_PATH.read_bytes(),
        ),
        supporting_documents=(),
        grant_application=PdfDocument(
            "Grant Application",
            SYNTHETIC_APPLICATION_03_PATH.name,
            SYNTHETIC_APPLICATION_03_PATH.read_bytes(),
        ),
    )
    funding_stream = ExtractedSection(
        id="funding_stream",
        header="Funding stream and amount requested",
        type="generic",
        text=(
            "Selected stream: Stream Two - Small-scale (up to $10,000)\n"
            "Total grant funding requested: $6,000.00"
        ),
        order=2,
        source_pages=[12, 17],
    )

    result = assess_funding_stream_section(bundle, funding_stream, settings)

    assert len(result.threshold_flags) == 1
    flag = result.threshold_flags[0]
    finding_text = f"{flag.comment} {flag.suggested_action}".lower()
    assert "stream one" in finding_text
    assert "$1,500" in finding_text or "1,500" in finding_text
    assert "niaa" in finding_text and "determin" in finding_text
    assert "ineligible" not in finding_text
    assert any("2.1" in source.reference for source in flag.sources)


def test_gemini_flags_unsupported_stream_three_assertions() -> None:
    settings = load_settings()
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", GOG_PATH.name, GOG_PATH.read_bytes()),
        application_form=PdfDocument(
            "Application Form",
            APPLICATION_FORM_PATH.name,
            APPLICATION_FORM_PATH.read_bytes(),
        ),
        supporting_documents=(),
        grant_application=PdfDocument(
            "Grant Application",
            SYNTHETIC_APPLICATION_04_PATH.name,
            SYNTHETIC_APPLICATION_04_PATH.read_bytes(),
        ),
    )
    criterion = ExtractedSection(
        id="criterion_1",
        header="Criterion 1: Demonstrated Experience, Resources and Capability",
        type="generic",
        text=(
            "Our organisation has delivered community events before and has "
            "staff and volunteers available. We believe the event offers value "
            "and will benefit the community. Risks will be managed through our "
            "usual processes."
        ),
        order=4,
        source_pages=[15],
    )

    result = assess_criterion_section(bundle, criterion, settings)

    assert len(result.findings) == 1
    finding = result.findings[0]
    finding_text = f"{finding.comment} {finding.suggested_action}".lower()
    for required_concept in ("experience", "resources", "risk", "value"):
        assert required_concept in finding_text
    assert "capabil" in finding_text
    assert "outcome" in finding_text
    assert "co-contribution" in finding_text
    assert "ineligible" not in finding_text
    assert any("6" in source.reference for source in finding.sources)


def test_gemini_flags_missing_mandatory_bank_evidence() -> None:
    settings = load_settings()
    bundle = AssessorDocumentBundle(
        gog=PdfDocument("GOG", GOG_PATH.name, GOG_PATH.read_bytes()),
        application_form=PdfDocument(
            "Application Form",
            APPLICATION_FORM_PATH.name,
            APPLICATION_FORM_PATH.read_bytes(),
        ),
        supporting_documents=(),
        grant_application=PdfDocument(
            "Grant Application",
            SYNTHETIC_APPLICATION_05_PATH.name,
            SYNTHETIC_APPLICATION_05_PATH.read_bytes(),
        ),
    )
    attachments = ExtractedSection(
        id="attachments",
        header="Attachments",
        type="generic",
        text=(
            "Bank account verification: Not provided\n"
            "Attachment B - Synthetic entity evidence\n"
            "Attachment C - Synthetic recent financial statements"
        ),
        order=7,
        source_pages=[24],
    )

    result = assess_attachment_section(bundle, attachments, settings)

    assert len(result.findings) == 1
    finding = result.findings[0]
    finding_text = f"{finding.comment} {finding.suggested_action}".lower()
    assert "bank" in finding_text and "not" in finding_text
    assert "non-compliant" in finding_text
    assert "may not proceed" in finding_text
    assert "human" in finding_text or "assessor" in finding_text
    assert "automatically rejected" not in finding_text
    assert "ineligible" not in finding_text
    assert any("7.1" in source.reference for source in finding.sources)


def test_gemini_accepts_the_prefilled_isolated_writer_activity() -> None:
    settings = load_settings()
    bundle = WriterDocumentBundle(
        gog=PdfDocument("GOG", GOG_PATH.name, GOG_PATH.read_bytes()),
        application_form=PdfDocument(
            "Application Form",
            APPLICATION_FORM_PATH.name,
            APPLICATION_FORM_PATH.read_bytes(),
        ),
        supporting_documents=(
            PdfDocument(
                "Applicants Guide",
                APPLICANTS_GUIDE_PATH.name,
                APPLICANTS_GUIDE_PATH.read_bytes(),
            ),
        ),
    )
    field = WriterDraftField(
        id="activity_description",
        header="Activity description and alignment",
        type="description",
        text=(
            "River Plains Community Association will hold a free family cultural "
            "arts and storytelling day in Dubbo on 22 August 2026. First Nations "
            "cultural facilitators and artists will lead storytelling, weaving and "
            "visual-art workshops. The community-designed event will strengthen "
            "cultural expression, enable intergenerational participation and promote "
            "respectful understanding of First Nations histories, cultures and "
            "achievements."
        ),
        order=1,
    )

    result = assess_writer_text_field(bundle, field, settings)

    assert result.section_id == "activity_description"
    assert result.findings == []


def test_gemini_classifies_default_writer_budget_mix() -> None:
    settings = load_settings()
    bundle = WriterDocumentBundle(
        gog=PdfDocument("GOG", GOG_PATH.name, GOG_PATH.read_bytes()),
        application_form=PdfDocument(
            "Application Form",
            APPLICATION_FORM_PATH.name,
            APPLICATION_FORM_PATH.read_bytes(),
        ),
        supporting_documents=(
            PdfDocument(
                "Applicants Guide",
                APPLICANTS_GUIDE_PATH.name,
                APPLICANTS_GUIDE_PATH.read_bytes(),
            ),
        ),
    )
    field = WriterDraftField(
        id="budget",
        header="Budget",
        type="budget",
        text=(
            "First Nations storytelling | $600.00\n"
            "Event delivery | $5,500.00\n"
            "Workshop costs | $1,000.00\n"
            "NAIDOC T-shirts for participants | $1,000.00"
        ),
        order=1,
    )

    result = assess_writer_budget_field(bundle, field, settings)

    classifications = {item.item: item.classification for item in result.items}
    assert classifications == {
        "First Nations storytelling": "in_scope",
        "Event delivery": "vague",
        "Workshop costs": "vague",
        "NAIDOC T-shirts for participants": "out_of_scope",
    }
    assert "clarified_elsewhere" not in classifications.values()
    assert all(
        item.suggested_action
        for item in result.items
        if item.classification != "in_scope"
    )
