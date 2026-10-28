from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.db.session import get_db
from app.schemas.datapack import DataPackCreate, DataPackUpdate, DataPackResponse
from app.schemas.document import DocumentResponse
from app.services.datapack_service import DataPackService
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService
from app.services.extraction_service import ExtractionError, UnsupportedFileTypeError

router = APIRouter(prefix="/datapacks", tags=["DataPacks"])


@router.get("", response_model=List[DataPackResponse])
def list_datapacks(db: Session = Depends(get_db)):
    """List all datapacks with document counts and processing status."""
    return DataPackService.list_all(db)


@router.post("", response_model=DataPackResponse, status_code=status.HTTP_201_CREATED)
def create_datapack(data: DataPackCreate, db: Session = Depends(get_db)):
    """Create a new datapack."""
    dp = DataPackService.create(db, data)
    return DataPackResponse(
        id=dp.id,
        name=dp.name,
        description=dp.description,
        created_at=dp.created_at,
        updated_at=dp.updated_at,
        file_count=0,
        processing_status="empty"
    )


@router.get("/{datapack_id}", response_model=DataPackResponse)
def get_datapack(datapack_id: UUID, db: Session = Depends(get_db)):
    """Retrieve datapack details by ID."""
    dp = DataPackService.get(db, datapack_id)
    if not dp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DataPack '{datapack_id}' not found."
        )
    docs = DocumentService.list_by_datapack(db, datapack_id)
    statuses = [d.processing_status for d in docs]
    agg = "empty"
    if docs:
        if any(s == "processing" for s in statuses):
            agg = "processing"
        elif any(s == "failed" for s in statuses):
            agg = "has_failures"
        elif any(s == "partially_processed" for s in statuses):
            agg = "partially_processed"
        elif all(s == "processed" for s in statuses):
            agg = "processed"
        else:
            agg = "pending"

    return DataPackResponse(
        id=dp.id,
        name=dp.name,
        description=dp.description,
        created_at=dp.created_at,
        updated_at=dp.updated_at,
        file_count=len(docs),
        processing_status=agg
    )


@router.patch("/{datapack_id}", response_model=DataPackResponse)
def update_datapack(datapack_id: UUID, data: DataPackUpdate, db: Session = Depends(get_db)):
    """Update datapack name or description."""
    dp = DataPackService.update(db, datapack_id, data)
    if not dp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DataPack '{datapack_id}' not found."
        )
    return DataPackResponse.model_validate(dp)


@router.delete("/{datapack_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_datapack(datapack_id: UUID, db: Session = Depends(get_db)):
    """Delete a datapack and cascade all its documents."""
    success = DataPackService.delete(db, datapack_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DataPack '{datapack_id}' not found."
        )
    return None


@router.get("/{datapack_id}/documents", response_model=List[DocumentResponse])
def list_datapack_documents(datapack_id: UUID, db: Session = Depends(get_db)):
    """List all documents belonging to a datapack."""
    dp = DataPackService.get(db, datapack_id)
    if not dp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DataPack '{datapack_id}' not found."
        )
    return DocumentService.list_by_datapack(db, datapack_id)


@router.post("/{datapack_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    datapack_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a file (.pdf, .md, .txt) and initiate the ingestion pipeline."""
    dp = DataPackService.get(db, datapack_id)
    if not dp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DataPack '{datapack_id}' not found."
        )

    # Validate file extension
    ext = file.filename.lower().split(".")[-1] if file.filename and "." in file.filename else ""
    if ext not in ["pdf", "md", "txt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '.{ext}' is not supported. Allowed extensions: .pdf, .md, .txt"
        )

    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {str(e)}"
        )

    try:
        doc, is_duplicate = IngestionService.ingest_file(
            db=db,
            datapack_id=datapack_id,
            filename=file.filename or "uploaded_file",
            file_bytes=content,
            mime_type=file.content_type or "application/octet-stream"
        )
        res = DocumentService.get_with_chunk_count(db, doc.id)
        return res
    except UnsupportedFileTypeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ExtractionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during ingestion: {str(e)}"
        )

