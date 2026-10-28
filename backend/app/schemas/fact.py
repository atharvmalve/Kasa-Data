from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, Any


class FactResponse(BaseModel):
    id: UUID
    document_id: UUID
    processing_version: int
    fact_type: str
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object_value: Optional[str] = None
    statement: str
    confidence: Optional[float] = None
    source_chunk_id: Optional[UUID] = None
    source_location: dict[str, Any] = {}
    exact_source_text: Optional[str] = None
    source_char_start: Optional[int] = None
    source_char_end: Optional[int] = None
    extraction_method: str
    validation_status: str = "accepted"
    validation_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FactLLMItem(BaseModel):
    fact_type: str
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object_value: Optional[str] = None
    statement: str
    confidence: Optional[float] = 1.0
    source_chunk_index: int
    exact_quote: Optional[str] = None
