from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, Any


class DocumentResponse(BaseModel):
    id: UUID
    datapack_id: UUID
    filename: str
    file_extension: str
    mime_type: str
    size_bytes: int
    md5_checksum: str
    sha256_checksum: str
    processing_status: str
    processing_version: int
    created_at: datetime
    updated_at: datetime
    processed_at: Optional[datetime] = None
    last_error: Optional[str] = None
    summary_status: str
    embedding_status: str
    embedding_model: Optional[str] = None
    embedding_dimension: Optional[int] = None
    source_metadata: dict[str, Any] = {}
    chunk_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class DocumentContentResponse(BaseModel):
    id: UUID
    filename: str
    raw_text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

