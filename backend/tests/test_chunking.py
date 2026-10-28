import pytest
from app.services.chunking_service import ChunkingService


def test_chunking_short_document():
    text = "Short sentence that easily fits in one chunk."
    chunks = ChunkingService.chunk_document(text, file_extension=".txt")
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].content == text
    assert chunks[0].content_hash is not None
    assert chunks[0].character_start == 0
    assert chunks[0].character_end == len(text)


def test_chunking_never_produces_empty_chunks():
    text = "Line 1\n\n\n\n\n\nLine 2\n\n\n\nLine 3"
    chunks = ChunkingService.chunk_document(text, file_extension=".txt")
    for c in chunks:
        assert len(c.content.strip()) > 0


def test_chunking_preserves_markdown_headings_and_code_blocks():
    md = (
        "# Architecture Overview\n\n"
        "This describes the system architecture.\n\n"
        "```python\n"
        "def run_engine():\n"
        "    print('Running engine')\n"
        "```\n\n"
        "## Database Layer\n\n"
        "We use YugabyteDB for persistence.\n"
    )
    chunks = ChunkingService.chunk_document(md, file_extension=".md")
    assert len(chunks) >= 1
    # Check that code block and heading are present in content
    full_combined = " ".join([c.content for c in chunks])
    assert "Architecture Overview" in full_combined
    assert "def run_engine():" in full_combined
    assert "Database Layer" in full_combined


def test_chunking_long_document_splits_with_stable_indices():
    long_para = "This is a detailed sentence about context extraction. " * 80
    text = f"First section.\n\n{long_para}\n\nThird section."
    chunks = ChunkingService.chunk_document(text, file_extension=".txt", target_tokens=100)
    assert len(chunks) > 1
    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx
        assert c.content_hash is not None
        assert c.character_start is not None
        assert c.character_end is not None

