from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Any


class EventResponse(BaseModel):
    id: UUID
    document_id: UUID
    processing_version: int
    stage: str
    status: str
    message: str
    duration_ms: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

