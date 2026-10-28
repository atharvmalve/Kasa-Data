from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.db.session import get_db
from app.schemas.document import DocumentResponse, DocumentContentResponse
from app.schemas.chunk import ChunkResponse, ChunkVectorResponse
from app.schemas.fact import FactResponse
from app.schemas.summary import SummaryResponse
from app.schemas.event import EventResponse
from app.schemas.pagination import PaginatedResponse
from app.schemas.audit import (
    TransformationLedgerResponse,
    ChunkingComparisonResponse,
    EvaluationResponse,
    StorageFootprintResponse
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: UUID, db: Session = Depends(get_db)):
    """Get metadata for a specific document."""
    doc = DocumentService.get_with_chunk_count(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )
    return doc


@router.get("/{document_id}/content", response_model=DocumentContentResponse)
def get_document_content(document_id: UUID, db: Session = Depends(get_db)):
    """Retrieve original extracted text of a document."""
    doc = DocumentService.get(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )
    return DocumentContentResponse(
        id=doc.id,
        filename=doc.filename,
        raw_text=doc.raw_text
    )


@router.get("/{document_id}/chunks", response_model=PaginatedResponse[ChunkResponse])
def get_document_chunks(
    document_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Retrieve paginated chunks generated for the document."""
    doc = DocumentService.get(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )
    return DocumentService.get_chunks_paginated(db, document_id, page=page, page_size=page_size)


@router.get("/{document_id}/chunks/{chunk_id}/vector", response_model=ChunkVectorResponse)
def get_chunk_vector(document_id: UUID, chunk_id: UUID, db: Session = Depends(get_db)):
    """Retrieve the full 384-dimensional vector, norm, and serialization byte size."""
    doc = DocumentService.get(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )
    vec = DocumentService.get_chunk_vector(db, document_id, chunk_id)
    if not vec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Embedding vector for chunk '{chunk_id}' not found."
        )
    return vec


@router.get("/{document_id}/facts", response_model=List[FactResponse])
def get_document_facts(document_id: UUID, db: Session = Depends(get_db)):
    """Retrieve extracted structured facts with source references and exact text anchors."""
    doc = DocumentService.get(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )
    facts = DocumentService.get_facts(db, document_id)
    return [FactResponse.model_validate(f) for f in facts]


@router.get("/{document_id}/summaries", response_model=List[SummaryResponse])
def get_document_summaries(document_id: UUID, db: Session = Depends(get_db)):
    """Retrieve summaries generated for the document."""
    doc = DocumentService.get(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )
    summaries = DocumentService.get_summaries(db, document_id)
    return [SummaryResponse.model_validate(s) for s in summaries]


@router.get("/{document_id}/events", response_model=PaginatedResponse[EventResponse])
def get_document_events(
    document_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Retrieve timestamped sequence of processing events."""
    doc = DocumentService.get(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )
    return DocumentService.get_events_paginated(db, document_id, page=page, page_size=page_size)


@router.get("/{document_id}/audit", response_model=TransformationLedgerResponse)
def get_document_audit_ledger(document_id: UUID, db: Session = Depends(get_db)):
    """Retrieve the versioned transformation ledger record for the document."""
    doc = DocumentService.get(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )
    ledger = DocumentService.get_ledger(db, document_id)
    if not ledger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No transformation ledger found for document '{document_id}' (version {doc.processing_version})."
        )
    return TransformationLedgerResponse.model_validate(ledger)


@router.post("/{document_id}/chunking-comparison", response_model=ChunkingComparisonResponse)
def compare_chunking_targets(document_id: UUID, db: Session = Depends(get_db)):
    """
    Run non-destructive diagnostic comparison of chunking targets (256, 512, 800, 1024 tokens)
    against the embedding model's strict 512 token limit.
    """
    doc = DocumentService.get(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )
    result = DocumentService.compare_chunking_targets(db, document_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot perform chunking comparison without document raw text."
        )
    return result


@router.get("/{document_id}/evaluation", response_model=EvaluationResponse)
def get_document_evaluation(document_id: UUID, db: Session = Depends(get_db)):
    """Run evidence retention evaluation across raw text, chunks, facts, and summaries."""
    doc = DocumentService.get(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )
    eval_res = DocumentService.evaluate_retention(db, document_id)
    if not eval_res:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot perform retention evaluation without document raw text."
        )
    return eval_res


@router.get("/{document_id}/storage-footprint", response_model=StorageFootprintResponse)
def get_document_storage_footprint(document_id: UUID, db: Session = Depends(get_db)):
    """Retrieve exact storage utilization and database expansion metrics."""
    doc = DocumentService.get(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )
    sf = DocumentService.get_storage_footprint(db, document_id)
    if not sf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Storage footprint metrics not available."
        )
    return sf


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: UUID, db: Session = Depends(get_db)):
    """Delete a document and cascade all chunks, facts, summaries, and events."""
    success = DocumentService.delete(db, document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )
    return None
