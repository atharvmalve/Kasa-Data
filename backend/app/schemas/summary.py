from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class SummaryResponse(BaseModel):
    id: UUID
    document_id: UUID
    processing_version: int
    summary_type: str
    content: str
    token_count: Optional[int] = None
    model_name: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

