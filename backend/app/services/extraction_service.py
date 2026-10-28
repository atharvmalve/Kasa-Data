import re
from typing import Tuple, Dict, Any, List
from app.core.config import settings
from app.core.logging import logger


class ExtractionError(Exception):
    pass


class UnsupportedFileTypeError(ExtractionError):
    pass


class EmptyDocumentError(ExtractionError):
    pass


class ScannedPdfError(ExtractionError):
    pass


class ExtractionResult:
    def __init__(
        self,
        raw_text: str,
        source_metadata: Dict[str, Any],
        pages: List[Dict[str, Any]] = None,
        headings: List[Dict[str, Any]] = None
    ):
        self.raw_text = raw_text
        self.source_metadata = source_metadata
        self.pages = pages or []
        self.headings = headings or []


class ExtractionService:
    @staticmethod
    def extract(file_bytes: bytes, filename: str, mime_type: str = "") -> ExtractionResult:
        if not file_bytes:
            raise EmptyDocumentError(f"File '{filename}' is empty (0 bytes).")

        if len(file_bytes) > settings.MAX_FILE_SIZE_BYTES:
            max_mb = settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise ExtractionError(f"File exceeds maximum allowed size of {max_mb} MB.")

        ext = filename.lower().split(".")[-1] if "." in filename else ""

        if ext == "txt":
            return ExtractionService.extract_txt(file_bytes, filename)
        elif ext == "md":
            return ExtractionService.extract_markdown(file_bytes, filename)
        elif ext == "pdf":
            return ExtractionService.extract_pdf(file_bytes, filename)
        else:
            raise UnsupportedFileTypeError(
                f"Unsupported file type '.{ext}'. Allowed types are .pdf, .md, .txt."
            )

    @staticmethod
    def extract_txt(file_bytes: bytes, filename: str) -> ExtractionResult:
        # Handle UTF-8 with BOM or plain UTF-8
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                # Try UTF-8 ignoring errors or fallback
                text = file_bytes.decode("utf-8")
            except UnicodeDecodeError as e:
                try:
                    text = file_bytes.decode("latin-1")
                except Exception:
                    raise ExtractionError(f"Failed to decode text file '{filename}' with UTF-8 encoding: {str(e)}")

        # Normalize line endings to \n while preserving empty lines and paragraphs
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        if not text.strip():
            raise EmptyDocumentError(f"Text file '{filename}' contains no readable content.")

        lines = text.split("\n")
        words = len(text.split())

        source_metadata = {
            "format": "txt",
            "line_count": len(lines),
            "character_count": len(text),
            "word_count": words,
        }

        pages = [{
            "page_number": 1,
            "text": text,
            "char_start": 0,
            "char_end": len(text),
        }]

        return ExtractionResult(raw_text=text, source_metadata=source_metadata, pages=pages)

    @staticmethod
    def extract_markdown(file_bytes: bytes, filename: str) -> ExtractionResult:
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("utf-8")
            except UnicodeDecodeError as e:
                raise ExtractionError(f"Markdown file '{filename}' is not valid UTF-8: {str(e)}")

        text = text.replace("\r\n", "\n").replace("\r", "\n")

        if not text.strip():
            raise EmptyDocumentError(f"Markdown file '{filename}' contains no readable content.")

        # Extract heading hierarchy and source offsets
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
        headings = []
        for match in heading_pattern.finditer(text):
            level = len(match.group(1))
            title = match.group(2).strip()
            headings.append({
                "level": level,
                "title": title,
                "start": match.start(),
                "end": match.end(),
            })

        lines = text.split("\n")
        words = len(text.split())

        source_metadata = {
            "format": "markdown",
            "line_count": len(lines),
            "character_count": len(text),
            "word_count": words,
            "heading_count": len(headings),
        }

        pages = [{
            "page_number": 1,
            "text": text,
            "char_start": 0,
            "char_end": len(text),
        }]

        return ExtractionResult(
            raw_text=text,
            source_metadata=source_metadata,
            pages=pages,
            headings=headings
        )

    @staticmethod
    def extract_pdf(file_bytes: bytes, filename: str) -> ExtractionResult:
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ExtractionError("PyMuPDF (fitz) is not installed on this system.")

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise ExtractionError(f"Failed to parse PDF file '{filename}': {str(e)}")

        page_count = len(doc)
        if page_count == 0:
            doc.close()
            raise EmptyDocumentError(f"PDF file '{filename}' has no pages.")

        if page_count > settings.MAX_PDF_PAGES:
            doc.close()
            raise ExtractionError(
                f"PDF exceeds maximum page limit of {settings.MAX_PDF_PAGES} (found {page_count} pages)."
            )

        pages = []
        full_text_parts = []
        total_char_offset = 0
        total_extracted_chars = 0

        for page_idx in range(page_count):
            page_num = page_idx + 1
            try:
                page = doc.load_page(page_idx)
                page_text = page.get_text("text") or ""
                # Normalize line endings
                page_text = page_text.replace("\r\n", "\n").replace("\r", "\n")
            except Exception as e:
                logger.warning(f"Error reading page {page_num} of '{filename}': {e}")
                page_text = ""

            char_start = total_char_offset
            char_end = char_start + len(page_text)
            total_extracted_chars += len(page_text.strip())

            pages.append({
                "page_number": page_num,
                "text": page_text,
                "char_start": char_start,
                "char_end": char_end,
            })

            full_text_parts.append(page_text)
            # Add page break separator
            total_char_offset = char_end + 2  # account for \n\n between pages

        doc.close()

        full_text = "\n\n".join(full_text_parts)

        # Detect image-only or scanned PDFs
        if total_extracted_chars == 0:
            raise ScannedPdfError(
                f"PDF file '{filename}' contains no extractable text. Scanned or image-only PDFs are unsupported for text extraction in Phase 1 without OCR."
            )

        source_metadata = {
            "format": "pdf",
            "page_count": page_count,
            "character_count": len(full_text),
            "word_count": len(full_text.split()),
        }

        return ExtractionResult(raw_text=full_text, source_metadata=source_metadata, pages=pages)

