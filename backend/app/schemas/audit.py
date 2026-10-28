from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any


class TransformationLedgerResponse(BaseModel):
    id: UUID
    document_id: UUID
    processing_version: int
    file_size_bytes: int
    file_md5: str
    file_sha256: str
    extracted_char_count: int
    extracted_byte_count: int
    extracted_token_count: int
    tokenizer_name: str
    tokenizer_version: str
    page_count: int
    pages_with_text: int
    pages_without_text: int
    extraction_warnings: List[Any]
    normalization_operations: List[Dict[str, Any]]
    normalized_char_count: int
    normalized_byte_count: int
    normalized_token_count: int
    chunking_strategy: str
    target_tokens: int
    overlap_tokens: int
    chunk_count: int
    chunk_token_stats: Dict[str, Any]
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    embedding_datatype: str
    embedding_normalized: bool
    embedding_total_latency_ms: Optional[int] = None
    embedding_storage_bytes: int
    enrichment_model: Optional[str] = None
    enrichment_latency_ms: Optional[int] = None
    enrichment_token_usage: Dict[str, Any]
    timing_breakdown: Optional[Dict[str, Any]] = None
    effective_embedding_limit: int = 510
    storage_footprint: Dict[str, Any]
    pipeline_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChunkCandidate(BaseModel):
    chunk_index: int
    token_count: int
    char_count: int
    split_reason: str
    content_preview: str
    heading_path: List[str]


class ChunkingTargetComparison(BaseModel):
    target_tokens: int
    chunk_count: int
    min_tokens: int
    max_tokens: int
    mean_tokens: float
    truncation_risk: bool
    risk_reason: Optional[str] = None
    chunks: List[ChunkCandidate]


class ChunkingComparisonResponse(BaseModel):
    document_id: UUID
    tokenizer_name: str
    model_max_length: int
    comparisons: List[ChunkingTargetComparison]
    architectural_finding: str


class EvaluationResponse(BaseModel):
    document_id: UUID
    dataset_version: str
    dataset_type: Optional[str] = None
    status: Optional[str] = "completed"
    evaluated_items_count: int
    total_required_claims: int
    metrics: Dict[str, Any]
    item_results: List[Dict[str, Any]]
    methodology_note: str


class StorageFootprintResponse(BaseModel):
    document_id: UUID
    file_size_bytes: int
    raw_text_bytes: int
    normalized_text_bytes: int
    chunk_text_bytes: int
    chunk_count: int
    vector_count: int
    embedding_dimension: int
    vector_raw_float32_bytes: int
    vector_json_serialized_bytes: int
    metadata_overhead_bytes: int
    total_database_estimated_bytes: int
    expansion_ratio: float
    vector_to_chunk_ratio: float
    explanation: str

