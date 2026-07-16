import pytest

from backend.documents import (
    PdfValidationError,
    build_pdf_document_part,
    validate_pdf,
)


def test_pdf_document_part_contains_the_original_bytes() -> None:
    pdf_bytes = b"%PDF-1.7\nsynthetic test content"

    part = build_pdf_document_part(pdf_bytes, "test.pdf")

    assert part.inline_data is not None
    assert part.inline_data.mime_type == "application/pdf"
    assert part.inline_data.data == pdf_bytes


@pytest.mark.parametrize(
    ("pdf_bytes", "filename", "message"),
    [
        (b"", "empty.pdf", "empty"),
        (b"%PDF-1.7", "document.txt", ".pdf extension"),
        (b"not a pdf", "document.pdf", "valid PDF data"),
    ],
)
def test_invalid_pdfs_are_rejected(
    pdf_bytes: bytes,
    filename: str,
    message: str,
) -> None:
    with pytest.raises(PdfValidationError, match=message):
        validate_pdf(pdf_bytes, filename)
