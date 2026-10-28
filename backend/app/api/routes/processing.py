from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService

router = APIRouter(tags=["Processing"])


@router.post("/documents/{document_id}/retry", response_model=DocumentResponse)
def retry_document_processing(document_id: UUID, db: Session = Depends(get_db)):
    """Retry failed processing or reprocess an existing document."""
    doc = DocumentService.get(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found."
        )

    try:
        updated_doc = IngestionService.retry_processing(db, document_id)
        return DocumentService.get_with_chunk_count(db, updated_doc.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry document processing: {str(e)}"
        )

