import pytest
import io
import fitz  # PyMuPDF
from app.services.extraction_service import (
    ExtractionService, UnsupportedFileTypeError, EmptyDocumentError, ScannedPdfError
)


def create_dummy_pdf(text: str = "Hello from PDF page 1") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_empty_pdf() -> bytes:
    doc = fitz.open()
    doc.new_page()  # page with no text
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_txt_extraction_utf8():
    content = "Hello world\nThis is a test paragraph.\n\nAnother paragraph.".encode("utf-8")
    res = ExtractionService.extract(content, "sample.txt")
    assert "Hello world" in res.raw_text
    assert res.source_metadata["format"] == "txt"
    assert res.source_metadata["word_count"] > 0
    assert len(res.pages) == 1
    assert res.pages[0]["page_number"] == 1


def test_txt_extraction_utf8_bom():
    content = "\ufeffBOM text content".encode("utf-8")
    res = ExtractionService.extract(content, "sample_bom.txt")
    assert res.raw_text == "BOM text content"


def test_markdown_extraction_headings_and_hierarchy():
    md = (
        "# Main Title\n\n"
        "Introduction paragraph.\n\n"
        "## Subtitle\n\n"
        "Section text with `code`.\n\n"
        "```python\n"
        "def foo():\n"
        "    return 42\n"
        "```\n"
    ).encode("utf-8")

    res = ExtractionService.extract(md, "test.md")
    assert "# Main Title" in res.raw_text
    assert res.source_metadata["format"] == "markdown"
    assert len(res.headings) == 2
    assert res.headings[0]["title"] == "Main Title"
    assert res.headings[0]["level"] == 1
    assert res.headings[1]["title"] == "Subtitle"
    assert res.headings[1]["level"] == 2


def test_pdf_extraction_page_provenance():
    pdf_bytes = create_dummy_pdf("This is a verifiable PDF content statement.")
    res = ExtractionService.extract(pdf_bytes, "test.pdf")
    assert "verifiable PDF content" in res.raw_text
    assert res.source_metadata["format"] == "pdf"
    assert res.source_metadata["page_count"] == 1
    assert len(res.pages) == 1
    assert res.pages[0]["page_number"] == 1
    assert res.pages[0]["char_start"] == 0


def test_unsupported_file_extension():
    with pytest.raises(UnsupportedFileTypeError):
        ExtractionService.extract(b"Some data", "file.docx")


def test_empty_file_error():
    with pytest.raises(EmptyDocumentError):
        ExtractionService.extract(b"", "empty.txt")


def test_scanned_or_no_text_pdf_error():
    empty_pdf = create_empty_pdf()
    with pytest.raises(ScannedPdfError):
        ExtractionService.extract(empty_pdf, "scanned.pdf")

