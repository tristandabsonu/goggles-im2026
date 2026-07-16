"""Small response models shared by the backend and Gemini."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class HealthResponse(BaseModel):
    status: str = "ok"


class ExtractedSection(BaseModel):
    """One applicant answer found during assessor pass one."""

    id: str = Field(description="A short, stable snake_case identifier.")
    header: str = Field(
        description="The field or section heading from the application."
    )
    type: Literal["budget", "description", "generic"]
    text: str = Field(description="The applicant's answer exactly as submitted.")
    order: int = Field(ge=1, description="Order in the submitted application.")
    source_pages: list[int] = Field(
        description="One-indexed PDF pages containing the applicant's answer."
    )


class SectionExtractionResult(BaseModel):
    """Structured output from assessor pass one."""

    sections: list[ExtractedSection]


class SourceReference(BaseModel):
    """A human-checkable source supplied with a finding."""

    document: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    excerpt: str = Field(
        description="A short supporting excerpt, or an empty string if unavailable."
    )

    @field_validator("document", "reference")
    @classmethod
    def source_identity_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Source document and reference must not be blank.")
        return value


class ClarificationEvidence(BaseModel):
    """Verifiable application evidence for a clarified budget label."""

    source_section_id: str = Field(
        description="The extracted non-budget section containing the evidence."
    )
    source_section: str = Field(
        description="The human-readable heading of the source section."
    )
    source_pages: list[int] = Field(
        description="One-indexed application pages containing the evidence."
    )
    excerpt: str = Field(
        description="An exact excerpt that explains this specific budget amount."
    )
    basis: Literal[
        "explicit_total",
        "quantity_rate",
        "component_breakdown",
    ]
    resolved_amount: str = Field(
        description="The amount reconciled by the quoted evidence."
    )


class BudgetItemAssessment(BaseModel):
    """Assessment of one requested-grant budget line."""

    item: str
    amount: str
    classification: Literal[
        "in_scope",
        "out_of_scope",
        "vague",
        "clarified_elsewhere",
    ]
    comment: str = Field(
        description="A concise comment, or an empty string when no action is needed."
    )
    suggested_action: str = Field(
        description="Human guidance, or an empty string when no action is needed."
    )
    sources: list[SourceReference]
    clarification_evidence: ClarificationEvidence | None = Field(
        default=None,
        description=("Required only for clarified_elsewhere; otherwise null."),
    )

    @model_validator(mode="after")
    def actionable_item_requires_a_source(self) -> "BudgetItemAssessment":
        """Never expose a budget concern or clarification without a citation."""

        needs_source = (
            self.classification != "in_scope"
            or bool(self.comment.strip())
            or bool(self.suggested_action.strip())
        )
        if needs_source and not self.sources:
            raise ValueError(
                "Actionable budget items and clarifications require a source."
            )
        return self


class BudgetAssessmentResult(BaseModel):
    """Structured pass-two result for the budget section."""

    section_id: str
    items: list[BudgetItemAssessment]


class ThresholdFlag(BaseModel):
    """A possible threshold issue for a human assessor to determine."""

    code: Literal["funding_stream_review"]
    comment: str
    suggested_action: str
    sources: list[SourceReference] = Field(min_length=1)


class FundingStreamAssessmentResult(BaseModel):
    """Structured pass-two result for the selected funding stream."""

    section_id: str
    selected_stream: str
    requested_amount: str
    threshold_flags: list[ThresholdFlag]


class AssessmentFinding(BaseModel):
    """One grounded matter for a human assessor to consider."""

    comment: str
    suggested_action: str
    sources: list[SourceReference] = Field(min_length=1)


class CriterionAssessmentResult(BaseModel):
    """Structured pass-two result for an assessment criterion."""

    section_id: str
    findings: list[AssessmentFinding]


class WriterFieldAssessmentResult(BaseModel):
    """Structured feedback for one isolated non-budget writer field."""

    section_id: str
    findings: list[AssessmentFinding]


class AttachmentAssessmentResult(BaseModel):
    """Structured pass-two result for the submitted attachment manifest."""

    section_id: str
    findings: list[AssessmentFinding]


class AssessedSection(BaseModel):
    """One implemented section check in the combined assessor response."""

    id: str
    header: str
    type: Literal[
        "budget",
        "description",
        "generic",
        "funding_stream",
        "criterion",
        "attachments",
    ]
    order: int
    findings: list[AssessmentFinding] = Field(default_factory=list)
    budget_items: list[BudgetItemAssessment] = Field(default_factory=list)
    has_threshold_flag: bool = False
    error: str | None = None


class AssessorCheckResult(BaseModel):
    """Current combined assessor result for the implemented prototype checks."""

    mode: Literal["assessor"] = "assessor"
    extracted_sections: list[ExtractedSection] = Field(default_factory=list)
    sections: list[AssessedSection]
    threshold_flags: list[ThresholdFlag]


class WriterDraftField(BaseModel):
    """One isolated applicant draft field submitted for writer feedback."""

    id: str
    header: str
    type: Literal["budget", "description", "criterion", "generic"]
    text: str
    order: int = Field(ge=1)


class WriterCheckResult(BaseModel):
    """Writer result with the same top-level shape as the assessor result."""

    mode: Literal["writer"] = "writer"
    sections: list[AssessedSection]
    threshold_flags: list[ThresholdFlag] = Field(default_factory=list)
