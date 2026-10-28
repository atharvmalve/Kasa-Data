import pytest
import uuid
from app.db.models import DataPack, Document, DocumentChunk, ExtractedFact, DocumentSummary, ProcessingEvent
from app.services.datapack_service import DataPackService
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService
from app.schemas.datapack import DataPackCreate, DataPackUpdate
from app.services.chunking_service import ChunkingService


def test_datapack_lifecycle_and_persistence(db_session):
    # 1. Create DataPack
    create_dto = DataPackCreate(name="Test Pack Alpha", description="Integration test pack")
    dp = DataPackService.create(db_session, create_dto)
    assert dp.id is not None
    assert dp.name == "Test Pack Alpha"

    # 2. Retrieve DataPack
    fetched = DataPackService.get(db_session, dp.id)
    assert fetched is not None
    assert fetched.name == "Test Pack Alpha"

    # 3. Update DataPack
    update_dto = DataPackUpdate(name="Updated Pack Alpha")
    updated = DataPackService.update(db_session, dp.id, update_dto)
    assert updated.name == "Updated Pack Alpha"

    # 4. List DataPacks
    all_packs = DataPackService.list_all(db_session)
    assert any(p.id == dp.id for p in all_packs)


def test_document_ingestion_and_deduplication(db_session):
    # Create DataPack
    dp = DataPackService.create(db_session, DataPackCreate(name="Pack Deduplication"))

    doc_content = b"Line 1: System initialization.\n\nLine 2: Configuration parameters verified."
    filename = "system_config.txt"

    # Ingest file first time
    doc1, is_duplicate1 = IngestionService.ingest_file(
        db=db_session,
        datapack_id=dp.id,
        filename=filename,
        file_bytes=doc_content,
        mime_type="text/plain"
    )
    assert is_duplicate1 is False
    assert doc1.processing_status in ["processed", "partially_processed"]
    assert doc1.raw_text is not None

    # Verify chunks created
    chunks = db_session.query(DocumentChunk).filter(
        DocumentChunk.document_id == doc1.id,
        DocumentChunk.processing_version == doc1.processing_version
    ).all()
    assert len(chunks) >= 1
    initial_chunk_count = len(chunks)

    # Ingest IDENTICAL file into same datapack -> must be detected as duplicate!
    doc2, is_duplicate2 = IngestionService.ingest_file(
        db=db_session,
        datapack_id=dp.id,
        filename=filename,
        file_bytes=doc_content,
        mime_type="text/plain"
    )
    assert is_duplicate2 is True
    assert doc2.id == doc1.id

    # Verify no duplicate active chunks were created
    chunks_after = db_session.query(DocumentChunk).filter(
        DocumentChunk.document_id == doc1.id,
        DocumentChunk.processing_version == doc1.processing_version
    ).all()
    assert len(chunks_after) == initial_chunk_count


def test_retry_processing_no_duplicate_chunks(db_session):
    dp = DataPackService.create(db_session, DataPackCreate(name="Pack Retry Test"))
    doc_content = b"First section content.\n\nSecond section content."
    doc, _ = IngestionService.ingest_file(
        db=db_session,
        datapack_id=dp.id,
        filename="retry_test.txt",
        file_bytes=doc_content,
        mime_type="text/plain"
    )

    initial_version = doc.processing_version

    # Retry processing
    updated_doc = IngestionService.retry_processing(db_session, doc.id)
    assert updated_doc.processing_version == initial_version + 1

    # Active chunks for latest version
    latest_chunks = db_session.query(DocumentChunk).filter(
        DocumentChunk.document_id == doc.id,
        DocumentChunk.processing_version == updated_doc.processing_version
    ).all()
    assert len(latest_chunks) >= 1

    # Verify each chunk has a valid content_hash and stable chunk_index
    for idx, c in enumerate(latest_chunks):
        assert c.chunk_index == idx
        assert len(c.content_hash) == 64


def test_pagination_and_invalid_ids(db_session):
    # Non-existent ID returns empty or None
    fake_id = uuid.uuid4()
    assert DocumentService.get(db_session, fake_id) is None
    paginated = DocumentService.get_chunks_paginated(db_session, fake_id, page=1, page_size=10)
    assert paginated.total == 0
    assert len(paginated.items) == 0


def test_document_cascade_deletion(db_session):
    dp = DataPackService.create(db_session, DataPackCreate(name="Pack Cascade Delete"))
    doc, _ = IngestionService.ingest_file(
        db=db_session,
        datapack_id=dp.id,
        filename="cascade.txt",
        file_bytes=b"Delete me soon.",
        mime_type="text/plain"
    )

    doc_id = doc.id
    # Ensure chunks and events exist
    assert db_session.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).count() > 0
    assert db_session.query(ProcessingEvent).filter(ProcessingEvent.document_id == doc_id).count() > 0

    # Delete document
    success = DocumentService.delete(db_session, doc_id)
    assert success is True

    # Check cascading deletes
    assert db_session.query(Document).filter(Document.id == doc_id).first() is None
    assert db_session.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).count() == 0
    assert db_session.query(ProcessingEvent).filter(ProcessingEvent.document_id == doc_id).count() == 0

