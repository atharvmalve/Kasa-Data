from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, Any, List


class ChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    processing_version: int
    chunk_index: int
    content: str
    token_count: Optional[int] = None
    token_count_model: Optional[str] = None
    character_start: Optional[int] = None
    character_end: Optional[int] = None
    source_location: dict[str, Any] = {}
    heading_path: list[Any] = []
    split_reason: str = "target_size_limit"
    embedding_status: str
    embedding_model: Optional[str] = None
    embedding_dimension: Optional[int] = None
    embedding_input_hash: Optional[str] = None
    embedding_latency_ms: Optional[int] = None
    embedding_norm: Optional[float] = None
    embedding_bytes: Optional[int] = None
    content_hash: str
    created_at: datetime
    vector_preview: Optional[List[float]] = None

    model_config = ConfigDict(from_attributes=True)


class ChunkVectorResponse(BaseModel):
    chunk_id: UUID
    document_id: UUID
    chunk_index: int
    dimension: int
    norm: Optional[float] = None
    datatype: str = "float32"
    serialized_bytes: int
    vector: List[float]
