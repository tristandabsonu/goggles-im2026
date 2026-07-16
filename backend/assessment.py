"""Gemini calls used by the assessment workflow."""

import logging
import re
import time
from collections.abc import Generator
from decimal import Decimal, InvalidOperation
from typing import Any, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from backend.config import Settings
from backend.documents import (
    AssessorDocumentBundle,
    PdfDocument,
    WriterDocumentBundle,
)
from backend.models import (
    AssessedSection,
    AssessorCheckResult,
    AttachmentAssessmentResult,
    BudgetAssessmentResult,
    CriterionAssessmentResult,
    ExtractedSection,
    FundingStreamAssessmentResult,
    SectionExtractionResult,
    WriterCheckResult,
    WriterDraftField,
    WriterFieldAssessmentResult,
)
from backend.prompts import (
    ATTACHMENT_ASSESSMENT_PROMPT,
    BUDGET_ASSESSMENT_PROMPT,
    CRITERION_ASSESSMENT_PROMPT,
    FUNDING_STREAM_ASSESSMENT_PROMPT,
    SECTION_EXTRACTION_PROMPT,
    WRITER_BUDGET_ASSESSMENT_PROMPT,
    WRITER_CRITERION_ASSESSMENT_PROMPT,
    WRITER_DESCRIPTION_ASSESSMENT_PROMPT,
)

logger = logging.getLogger(__name__)

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)

_NUMBER_PATTERN = re.compile(r"(?<!\w)\$?\s*(\d[\d,]*(?:\.\d{1,2})?)(?!\w)")


def _new_client(settings: Settings) -> genai.Client:
    return genai.Client(
        api_key=settings.gemini_api_key.get_secret_value(),
        http_options=types.HttpOptions(timeout=settings.gemini_request_timeout_ms),
    )


def _document_parts(documents: list[PdfDocument]) -> list[types.Part]:
    """Keep shared documents first and in stable order for implicit caching."""

    parts: list[types.Part] = []
    for document in documents:
        parts.extend(document.as_gemini_parts())
    return parts


def _assessor_document_parts(bundle: AssessorDocumentBundle) -> list[types.Part]:
    """Return the complete Assessor bundle in its stable caching order."""

    return _document_parts(
        [
            bundle.gog,
            bundle.application_form,
            *bundle.supporting_documents,
            bundle.grant_application,
        ]
    )


def _writer_document_parts(bundle: WriterDocumentBundle) -> list[types.Part]:
    """Return applicant-facing documents in their stable caching order."""

    return _document_parts(
        [
            bundle.gog,
            bundle.application_form,
            *bundle.supporting_documents,
        ]
    )


def _finish_reason(response: Any) -> str | None:
    candidates = getattr(response, "candidates", None)
    if not candidates:
        return None
    reason = getattr(candidates[0], "finish_reason", None)
    return getattr(reason, "value", reason)


def _normalise_evidence_text(value: str) -> str:
    """Normalise punctuation and whitespace while preserving word order."""

    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _amounts_in_text(value: str) -> set[Decimal]:
    """Return simple numeric values used to reconcile prototype budget evidence."""

    amounts: set[Decimal] = set()
    for match in _NUMBER_PATTERN.finditer(value):
        try:
            amounts.add(Decimal(match.group(1).replace(",", "")))
        except InvalidOperation:
            continue
    return amounts


def _clarification_is_verifiable(
    item: Any,
    context_sections: list[ExtractedSection],
) -> bool:
    """Apply the conservative local gate for clarified budget classifications."""

    evidence = item.clarification_evidence
    if evidence is None:
        return False

    source = next(
        (
            section
            for section in context_sections
            if section.id == evidence.source_section_id and section.id != "budget"
        ),
        None,
    )
    if source is None or not source.source_pages:
        return False

    excerpt = _normalise_evidence_text(evidence.excerpt)
    source_text = _normalise_evidence_text(source.text)
    if not excerpt or excerpt not in source_text:
        return False

    requested_amounts = _amounts_in_text(item.amount)
    resolved_amounts = _amounts_in_text(evidence.resolved_amount)
    excerpt_amounts = _amounts_in_text(evidence.excerpt)
    if len(requested_amounts) != 1 or len(resolved_amounts) != 1:
        return False

    requested_amount = next(iter(requested_amounts))
    resolved_amount = next(iter(resolved_amounts))
    return requested_amount == resolved_amount and requested_amount in excerpt_amounts


def _enforce_clarification_evidence(
    result: BudgetAssessmentResult,
    context_sections: list[ExtractedSection],
) -> None:
    """Downgrade unsupported clearances instead of trusting an uncertain claim."""

    for item in result.items:
        if item.classification != "clarified_elsewhere":
            item.clarification_evidence = None
            continue
        if _clarification_is_verifiable(item, context_sections):
            source = next(
                section
                for section in context_sections
                if section.id == item.clarification_evidence.source_section_id
            )
            item.clarification_evidence.source_section = source.header
            item.clarification_evidence.source_pages = list(source.source_pages)
            continue

        logger.info(
            "Budget item %r was downgraded because clarification evidence "
            "could not be verified.",
            item.item,
        )
        item.classification = "vague"
        item.comment = (
            "The application mentions the related activity, but does not provide "
            "a verifiable breakdown for this budget amount."
        )
        item.suggested_action = (
            "Confirm the components, quantities or rates that make up this cost."
        )
        item.clarification_evidence = None


def _enforce_writer_budget_isolation(result: BudgetAssessmentResult) -> None:
    """Prevent isolated Writer feedback from relying on another draft field."""

    for item in result.items:
        if item.classification == "clarified_elsewhere":
            logger.info(
                "Writer budget item %r was downgraded because Writer mode "
                "cannot use another draft field.",
                item.item,
            )
            item.classification = "vague"
            item.comment = (
                "This budget item is not explained clearly enough in this field "
                "to verify what the amount covers."
            )
            item.suggested_action = (
                "Describe and itemise the components, quantities or rates that "
                "make up this cost in the budget field."
            )
        item.clarification_evidence = None


def _context_sections_for_prompt(sections: list[ExtractedSection]) -> str:
    """Give Gemini the exact pass-one IDs and text used by the evidence gate."""

    available = [section for section in sections if section.id != "budget"]
    if not available:
        return "None supplied. Do not use clarified_elsewhere."
    return "\n\n".join(
        (
            f"Section ID: {section.id}\n"
            f"Heading: {section.header}\n"
            f"Application pages: {section.source_pages}\n"
            f"Extracted text:\n{section.text}"
        )
        for section in available
    )


def _log_usage(call_name: str, response: Any) -> None:
    """Record billable, thinking and implicit-cache tokens for live checks."""

    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return
    logger.info(
        "%s usage: input=%s output=%s thinking=%s cached=%s total=%s",
        call_name,
        getattr(usage, "prompt_token_count", None),
        getattr(usage, "candidates_token_count", None),
        getattr(usage, "thoughts_token_count", None),
        getattr(usage, "cached_content_token_count", None),
        getattr(usage, "total_token_count", None),
    )


def _generate_structured(
    client: genai.Client,
    settings: Settings,
    document_parts: list[types.Part],
    prompt: str,
    response_model: type[ResponseModel],
    *,
    max_output_tokens: int,
    call_name: str,
) -> tuple[ResponseModel | None, Any]:
    """Make one Gemini structured-output call with inline native PDFs."""

    logger.info(
        "%s started: model=%s thinking=%s timeout_ms=%s",
        call_name,
        settings.gemini_model,
        settings.gemini_thinking_level,
        settings.gemini_request_timeout_ms,
    )
    started_at = time.perf_counter()
    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[
                *document_parts,
                types.Part.from_text(text=prompt),
            ],
            config=types.GenerateContentConfig(
                max_output_tokens=max_output_tokens,
                response_mime_type="application/json",
                response_schema=response_model,
                thinking_config=types.ThinkingConfig(
                    thinking_level=settings.gemini_thinking_level,
                ),
            ),
        )
    except Exception:
        logger.exception(
            "%s failed after %.1fs",
            call_name,
            time.perf_counter() - started_at,
        )
        raise

    logger.info(
        "%s completed in %.1fs",
        call_name,
        time.perf_counter() - started_at,
    )
    _log_usage(call_name, response)

    parsed = getattr(response, "parsed", None)
    if parsed is None:
        return None, response
    if isinstance(parsed, response_model):
        return parsed, response
    if isinstance(parsed, str):
        return response_model.model_validate_json(parsed), response
    return response_model.model_validate(parsed), response


def extract_assessable_sections(
    bundle: AssessorDocumentBundle,
    settings: Settings,
    *,
    client: genai.Client | None = None,
) -> SectionExtractionResult:
    """Extract assessor-relevant applicant answers without assessing them."""

    gemini_client = client or _new_client(settings)
    result, response = _generate_structured(
        gemini_client,
        settings,
        _document_parts([bundle.application_form, bundle.grant_application]),
        SECTION_EXTRACTION_PROMPT,
        SectionExtractionResult,
        max_output_tokens=8_000,
        call_name="section_extraction",
    )

    if result is None:
        raise RuntimeError(
            f"Gemini did not return extracted sections (finish reason: "
            f"{_finish_reason(response)})."
        )

    result.sections.sort(key=lambda section: section.order)
    return result


def assess_budget_section(
    bundle: AssessorDocumentBundle,
    budget_section: ExtractedSection,
    settings: Settings,
    *,
    context_sections: list[ExtractedSection] | None = None,
    client: genai.Client | None = None,
) -> BudgetAssessmentResult:
    """Assess one itemised grant budget using the complete assessor bundle."""

    if budget_section.type != "budget":
        raise ValueError("assess_budget_section requires a budget section")

    gemini_client = client or _new_client(settings)
    document_parts = _assessor_document_parts(bundle)
    prompt = BUDGET_ASSESSMENT_PROMPT.format(
        budget_text=budget_section.text,
        context_sections=_context_sections_for_prompt(context_sections or []),
    )
    result, response = _generate_structured(
        gemini_client,
        settings,
        document_parts,
        prompt,
        BudgetAssessmentResult,
        max_output_tokens=5_000,
        call_name="budget_assessment",
    )

    if result is None:
        raise RuntimeError(
            f"Gemini did not return a budget assessment (finish reason: "
            f"{_finish_reason(response)})."
        )

    _enforce_clarification_evidence(result, context_sections or [])
    return result


def assess_funding_stream_section(
    bundle: AssessorDocumentBundle,
    funding_stream_section: ExtractedSection,
    settings: Settings,
    *,
    client: genai.Client | None = None,
) -> FundingStreamAssessmentResult:
    """Check one selected funding stream using the complete assessor bundle."""

    if funding_stream_section.id != "funding_stream":
        raise ValueError(
            "assess_funding_stream_section requires a funding_stream section"
        )

    gemini_client = client or _new_client(settings)
    document_parts = _assessor_document_parts(bundle)
    prompt = FUNDING_STREAM_ASSESSMENT_PROMPT.format(
        funding_stream_text=funding_stream_section.text
    )
    result, response = _generate_structured(
        gemini_client,
        settings,
        document_parts,
        prompt,
        FundingStreamAssessmentResult,
        max_output_tokens=3_000,
        call_name="funding_stream_assessment",
    )

    if result is None:
        raise RuntimeError(
            f"Gemini did not return a funding-stream assessment (finish reason: "
            f"{_finish_reason(response)})."
        )

    return result


def assess_criterion_section(
    bundle: AssessorDocumentBundle,
    criterion_section: ExtractedSection,
    settings: Settings,
    *,
    client: genai.Client | None = None,
) -> CriterionAssessmentResult:
    """Assess one Stream Three criterion using the complete assessor bundle."""

    if criterion_section.id != "criterion_1":
        raise ValueError("assess_criterion_section requires a criterion_1 section")

    gemini_client = client or _new_client(settings)
    document_parts = _assessor_document_parts(bundle)
    prompt = CRITERION_ASSESSMENT_PROMPT.format(criterion_text=criterion_section.text)
    result, response = _generate_structured(
        gemini_client,
        settings,
        document_parts,
        prompt,
        CriterionAssessmentResult,
        max_output_tokens=3_000,
        call_name="criterion_assessment",
    )

    if result is None:
        raise RuntimeError(
            f"Gemini did not return a criterion assessment (finish reason: "
            f"{_finish_reason(response)})."
        )

    return result


def assess_attachment_section(
    bundle: AssessorDocumentBundle,
    attachment_section: ExtractedSection,
    settings: Settings,
    *,
    client: genai.Client | None = None,
) -> AttachmentAssessmentResult:
    """Check one submitted attachment manifest against mandatory requirements."""

    if attachment_section.id != "attachments":
        raise ValueError("assess_attachment_section requires an attachments section")

    gemini_client = client or _new_client(settings)
    document_parts = _assessor_document_parts(bundle)
    prompt = ATTACHMENT_ASSESSMENT_PROMPT.format(
        attachments_text=attachment_section.text
    )
    result, response = _generate_structured(
        gemini_client,
        settings,
        document_parts,
        prompt,
        AttachmentAssessmentResult,
        max_output_tokens=5_000,
        call_name="attachment_assessment",
    )

    if result is None:
        raise RuntimeError(
            f"Gemini did not return an attachment assessment (finish reason: "
            f"{_finish_reason(response)})."
        )

    return result


SUPPORTED_ASSESSOR_SECTION_IDS = frozenset(
    {"funding_stream", "budget", "criterion_1", "attachments"}
)


def iter_assessment_steps(
    bundle: AssessorDocumentBundle,
    extraction: SectionExtractionResult,
    settings: Settings,
) -> Generator[tuple[ExtractedSection, int, int], None, AssessorCheckResult]:
    """Yield each real review stage before doing its work, then return the result."""

    assessed_sections: list[AssessedSection] = []
    threshold_flags = []
    reviewable_sections = [
        section
        for section in extraction.sections
        if section.id in SUPPORTED_ASSESSOR_SECTION_IDS
    ]

    for current, section in enumerate(reviewable_sections, start=1):
        yield section, current, len(reviewable_sections)

        section_type = {
            "funding_stream": "funding_stream",
            "budget": "budget",
            "criterion_1": "criterion",
            "attachments": "attachments",
        }[section.id]
        assessed = AssessedSection(
            id=section.id,
            header=section.header,
            type=section_type,
            order=section.order,
        )

        try:
            if section.id == "funding_stream":
                result = assess_funding_stream_section(bundle, section, settings)
                threshold_flags.extend(result.threshold_flags)
                assessed.has_threshold_flag = bool(result.threshold_flags)
            elif section.id == "budget":
                result = assess_budget_section(
                    bundle,
                    section,
                    settings,
                    context_sections=extraction.sections,
                )
                assessed.budget_items = result.items
            elif section.id == "criterion_1":
                result = assess_criterion_section(bundle, section, settings)
                assessed.findings = result.findings
            else:
                result = assess_attachment_section(bundle, section, settings)
                assessed.findings = result.findings
        except Exception as exc:  # one failed section should not hide the others
            assessed.error = f"This section could not be assessed: {exc}"

        assessed_sections.append(assessed)

    assessed_sections.sort(key=lambda section: section.order)
    return AssessorCheckResult(
        extracted_sections=extraction.sections,
        sections=assessed_sections,
        threshold_flags=threshold_flags,
    )


def assess_application(
    bundle: AssessorDocumentBundle,
    extraction: SectionExtractionResult,
    settings: Settings,
) -> AssessorCheckResult:
    """Run the implemented assessor checks and combine their section results."""

    steps = iter_assessment_steps(bundle, extraction, settings)
    while True:
        try:
            next(steps)
        except StopIteration as completed:
            return completed.value


def assess_writer_budget_field(
    bundle: WriterDocumentBundle,
    field: WriterDraftField,
    settings: Settings,
    *,
    client: genai.Client | None = None,
) -> BudgetAssessmentResult:
    """Assess one isolated writer budget field without any other draft answers."""

    if field.type != "budget":
        raise ValueError("assess_writer_budget_field requires a budget field")

    gemini_client = client or _new_client(settings)
    document_parts = _writer_document_parts(bundle)
    prompt = WRITER_BUDGET_ASSESSMENT_PROMPT.format(budget_text=field.text)
    result, response = _generate_structured(
        gemini_client,
        settings,
        document_parts,
        prompt,
        BudgetAssessmentResult,
        max_output_tokens=5_000,
        call_name="writer_budget_assessment",
    )

    if result is None:
        raise RuntimeError(
            f"Gemini did not return writer budget feedback (finish reason: "
            f"{_finish_reason(response)})."
        )

    _enforce_writer_budget_isolation(result)
    return result


def assess_writer_text_field(
    bundle: WriterDocumentBundle,
    field: WriterDraftField,
    settings: Settings,
    *,
    client: genai.Client | None = None,
) -> WriterFieldAssessmentResult:
    """Assess one isolated activity description or Stream Three criterion."""

    prompt_templates = {
        "description": WRITER_DESCRIPTION_ASSESSMENT_PROMPT,
        "criterion": WRITER_CRITERION_ASSESSMENT_PROMPT,
    }
    if field.type not in prompt_templates:
        raise ValueError(
            "assess_writer_text_field requires a description or criterion field"
        )

    gemini_client = client or _new_client(settings)
    document_parts = _writer_document_parts(bundle)
    prompt = prompt_templates[field.type].format(field_text=field.text)
    retry_instruction = (
        "\n\nYour previous response was incomplete. Return the complete, concise "
        "structured result now. Do not add prose outside the required result."
    )
    last_finish_reason = None

    for attempt in range(2):
        attempt_prompt = prompt if attempt == 0 else prompt + retry_instruction
        try:
            result, response = _generate_structured(
                gemini_client,
                settings,
                document_parts,
                attempt_prompt,
                WriterFieldAssessmentResult,
                max_output_tokens=5_000,
                call_name=f"writer_{field.type}_assessment",
            )
        except ValidationError as exc:
            if attempt == 0:
                logger.warning(
                    "Writer %s assessment returned invalid structured JSON; retrying once.",
                    field.type,
                )
                continue
            raise RuntimeError(
                "Gemini returned incomplete structured feedback twice. Please try again."
            ) from exc

        last_finish_reason = _finish_reason(response)
        if result is not None:
            return result
        if attempt == 0:
            logger.warning(
                "Writer %s assessment returned no parsed output (finish reason: %s); "
                "retrying once.",
                field.type,
                last_finish_reason,
            )

    raise RuntimeError(
        f"Gemini did not return complete writer {field.type} feedback after a "
        f"retry (last finish reason: {last_finish_reason})."
    )


def iter_writer_assessment_steps(
    bundle: WriterDocumentBundle,
    fields: list[WriterDraftField],
    settings: Settings,
) -> Generator[tuple[WriterDraftField, int, int], None, WriterCheckResult]:
    """Yield each writer field immediately before its isolated assessment."""

    sections: list[AssessedSection] = []
    ordered_fields = sorted(fields, key=lambda item: item.order)
    for current, field in enumerate(ordered_fields, start=1):
        yield field, current, len(ordered_fields)
        assessed = AssessedSection(
            id=field.id,
            header=field.header,
            type=field.type,
            order=field.order,
        )
        if field.type == "generic":
            assessed.error = "This field type is not implemented in the prototype yet."
        elif field.type == "budget":
            try:
                result = assess_writer_budget_field(bundle, field, settings)
                assessed.budget_items = result.items
            except Exception as exc:
                assessed.error = f"This field could not be assessed: {exc}"
        else:
            try:
                result = assess_writer_text_field(bundle, field, settings)
                assessed.findings = result.findings
            except Exception as exc:
                assessed.error = f"This field could not be assessed: {exc}"
        sections.append(assessed)

    return WriterCheckResult(sections=sections)
