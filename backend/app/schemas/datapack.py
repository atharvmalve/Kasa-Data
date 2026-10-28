from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class DataPackBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Datapack display name")
    description: Optional[str] = Field(None, max_length=2000, description="Optional description")


class DataPackCreate(DataPackBase):
    pass


class DataPackUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class DataPackResponse(DataPackBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    file_count: int = 0
    processing_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

