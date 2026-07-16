"""PDF validation and conversion for Gemini document inputs."""

from dataclasses import dataclass
from pathlib import Path

from google.genai import types


class PdfValidationError(ValueError):
    """Raised when a supplied file is not a usable PDF."""


@dataclass(frozen=True, slots=True)
class PdfDocument:
    """A labelled PDF held in memory for the duration of one request."""

    label: str
    filename: str
    content: bytes

    def __post_init__(self) -> None:
        validate_pdf(self.content, self.filename)

    def as_gemini_parts(self) -> list[types.Part]:
        """Return a stable label followed by the inline native-PDF part."""

        title = f"{self.label}: {Path(self.filename).stem}"
        return [
            types.Part.from_text(text=f"Document label: {title}"),
            build_pdf_document_part(self.content, self.filename),
        ]


@dataclass(frozen=True, slots=True)
class AssessorDocumentBundle:
    """The four assessor input boxes, without persistent storage."""

    gog: PdfDocument
    application_form: PdfDocument
    supporting_documents: tuple[PdfDocument, ...]
    grant_application: PdfDocument


@dataclass(frozen=True, slots=True)
class WriterDocumentBundle:
    """Applicant-facing source documents, with no submitted application."""

    gog: PdfDocument
    application_form: PdfDocument
    supporting_documents: tuple[PdfDocument, ...]


def validate_pdf(pdf_bytes: bytes, filename: str) -> None:
    """Perform the small set of PDF checks needed by the prototype."""

    if not filename.lower().endswith(".pdf"):
        raise PdfValidationError(f"{filename or 'File'} must have a .pdf extension.")
    if not pdf_bytes:
        raise PdfValidationError(f"{filename} is empty.")
    if not pdf_bytes.startswith(b"%PDF-"):
        raise PdfValidationError(f"{filename} does not contain valid PDF data.")


def build_pdf_document_part(
    pdf_bytes: bytes,
    filename: str,
) -> types.Part:
    """Return an inline PDF part accepted by the Gemini Developer API."""

    validate_pdf(pdf_bytes, filename)
    return types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
