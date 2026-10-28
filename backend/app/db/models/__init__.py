import uuid
from typing import Optional, List, Any
from datetime import datetime
from sqlalchemy import (
    String, Text, Integer, BigInteger, Float, Boolean, DateTime, ForeignKey,
    UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now


# Use JSONB on PostgreSQL/YugabyteDB, fallback to JSON
JsonType = JSONB().with_variant(JSON(), "sqlite")


class DataPack(Base):
    __tablename__ = "datapacks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    # Relationships
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="datapack",
        cascade="all, delete-orphan",
        order_by="Document.created_at.desc()"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    datapack_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datapacks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(32), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    md5_checksum: Mapped[str] = mapped_column(String(32), nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(32), default="uploaded", index=True)
    processing_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary_status: Mapped[str] = mapped_column(String(32), default="pending")
    embedding_status: Mapped[str] = mapped_column(String(32), default="pending")
    embedding_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    embedding_dimension: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    __table_args__ = (
        UniqueConstraint("datapack_id", "sha256_checksum", name="uq_datapack_sha256"),
    )

    # Relationships
    datapack: Mapped["DataPack"] = relationship("DataPack", back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index"
    )
    summaries: Mapped[List["DocumentSummary"]] = relationship(
        "DocumentSummary",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentSummary.created_at.desc()"
    )
    facts: Mapped[List["ExtractedFact"]] = relationship(
        "ExtractedFact",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ExtractedFact.created_at.desc()"
    )
    events: Mapped[List["ProcessingEvent"]] = relationship(
        "ProcessingEvent",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="ProcessingEvent.created_at.asc()"
    )
    ledgers: Mapped[List["TransformationLedger"]] = relationship(
        "TransformationLedger",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="TransformationLedger.processing_version.desc()"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    processing_version: Mapped[int] = mapped_column(Integer, default=1)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_count_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    split_reason: Mapped[str] = mapped_column(String(64), default="target_size_limit")
    character_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    character_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_location: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    heading_path: Mapped[list[Any]] = mapped_column(JsonType, default=list)
    embedding: Mapped[Optional[list[float]]] = mapped_column(JsonType, nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    embedding_dimension: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding_status: Mapped[str] = mapped_column(String(32), default="pending")
    embedding_input_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    embedding_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding_norm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    embedding_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        UniqueConstraint("document_id", "processing_version", "chunk_index", name="uq_doc_version_chunk_index"),
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    facts: Mapped[List["ExtractedFact"]] = relationship(
        "ExtractedFact",
        back_populates="source_chunk",
        cascade="all, delete-orphan"
    )


class DocumentSummary(Base):
    __tablename__ = "document_summaries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    processing_version: Mapped[int] = mapped_column(Integer, default=1)
    summary_type: Mapped[str] = mapped_column(String(64), default="document")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="summaries")


class ExtractedFact(Base):
    __tablename__ = "extracted_facts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    processing_version: Mapped[int] = mapped_column(Integer, default=1)
    fact_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    predicate: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    object_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    exact_source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_char_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_char_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(32), default="accepted")
    validation_reason: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source_location: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    extraction_method: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="facts")
    source_chunk: Mapped["DocumentChunk"] = relationship("DocumentChunk", back_populates="facts")


class ProcessingEvent(Base):
    __tablename__ = "processing_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    processing_version: Mapped[int] = mapped_column(Integer, default=1)
    stage: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JsonType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="events")


class TransformationLedger(Base):
    __tablename__ = "transformation_ledgers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    processing_version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_md5: Mapped[str] = mapped_column(String(32), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_byte_count: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    tokenizer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tokenizer_version: Mapped[str] = mapped_column(String(64), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=1)
    pages_with_text: Mapped[int] = mapped_column(Integer, default=1)
    pages_without_text: Mapped[int] = mapped_column(Integer, default=0)
    extraction_warnings: Mapped[list[Any]] = mapped_column(JsonType, default=list)
    normalization_operations: Mapped[list[Any]] = mapped_column(JsonType, default=list)
    normalized_char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    normalized_byte_count: Mapped[int] = mapped_column(Integer, nullable=False)
    normalized_token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    chunking_strategy: Mapped[str] = mapped_column(String(64), default="structure_aware_tokenizer")
    target_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    overlap_tokens: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_token_stats: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    embedding_provider: Mapped[str] = mapped_column(String(64), default="sentence_transformers")
    embedding_model: Mapped[str] = mapped_column(String(128), default="sentence-transformers/all-MiniLM-L6-v2")
    embedding_dimension: Mapped[int] = mapped_column(Integer, default=384)
    embedding_datatype: Mapped[str] = mapped_column(String(32), default="float32")
    embedding_normalized: Mapped[bool] = mapped_column(Boolean, default=True)
    embedding_total_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding_storage_bytes: Mapped[int] = mapped_column(Integer, default=0)
    enrichment_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    enrichment_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    enrichment_token_usage: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    storage_footprint: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    timing_breakdown: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)
    pipeline_version: Mapped[str] = mapped_column(String(32), default="1.1.1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        UniqueConstraint("document_id", "processing_version", name="uq_ledger_doc_version"),
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="ledgers")
