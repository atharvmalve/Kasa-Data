from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from app.db.models import (
    Document, DocumentChunk, DocumentSummary, ExtractedFact, ProcessingEvent, TransformationLedger
)
from app.schemas.document import DocumentResponse
from app.schemas.chunk import ChunkResponse, ChunkVectorResponse
from app.schemas.pagination import PaginatedResponse
from app.schemas.audit import (
    TransformationLedgerResponse,
    ChunkingComparisonResponse,
    ChunkingTargetComparison,
    ChunkCandidate,
    EvaluationResponse,
    StorageFootprintResponse
)
from app.schemas.event import EventResponse
from app.services.chunking_service import ChunkingService
from app.services.evaluation_service import EvaluationService
from app.services.normalization_service import NormalizationService
from app.services.tokenizer_service import TokenizerService


class DocumentService:
    @staticmethod
    def get(db: Session, document_id: UUID) -> Optional[Document]:
        return db.query(Document).filter(Document.id == document_id).first()

    @staticmethod
    def get_with_chunk_count(db: Session, document_id: UUID) -> Optional[DocumentResponse]:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return None

        chunk_count = db.query(func.count(DocumentChunk.id)).filter(
            DocumentChunk.document_id == doc.id,
            DocumentChunk.processing_version == doc.processing_version
        ).scalar() or 0

        return DocumentResponse(
            id=doc.id,
            datapack_id=doc.datapack_id,
            filename=doc.filename,
            file_extension=doc.file_extension,
            mime_type=doc.mime_type,
            size_bytes=doc.size_bytes,
            md5_checksum=doc.md5_checksum,
            sha256_checksum=doc.sha256_checksum,
            processing_status=doc.processing_status,
            processing_version=doc.processing_version,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            processed_at=doc.processed_at,
            last_error=doc.last_error,
            summary_status=doc.summary_status,
            embedding_status=doc.embedding_status,
            embedding_model=doc.embedding_model,
            embedding_dimension=doc.embedding_dimension,
            source_metadata=doc.source_metadata or {},
            chunk_count=chunk_count
        )

    @staticmethod
    def list_by_datapack(db: Session, datapack_id: UUID) -> List[DocumentResponse]:
        docs = db.query(Document).filter(
            Document.datapack_id == datapack_id
        ).order_by(Document.created_at.desc()).all()

        results: List[DocumentResponse] = []
        for doc in docs:
            count = db.query(func.count(DocumentChunk.id)).filter(
                DocumentChunk.document_id == doc.id,
                DocumentChunk.processing_version == doc.processing_version
            ).scalar() or 0

            results.append(DocumentResponse(
                id=doc.id,
                datapack_id=doc.datapack_id,
                filename=doc.filename,
                file_extension=doc.file_extension,
                mime_type=doc.mime_type,
                size_bytes=doc.size_bytes,
                md5_checksum=doc.md5_checksum,
                sha256_checksum=doc.sha256_checksum,
                processing_status=doc.processing_status,
                processing_version=doc.processing_version,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                processed_at=doc.processed_at,
                last_error=doc.last_error,
                summary_status=doc.summary_status,
                embedding_status=doc.embedding_status,
                embedding_model=doc.embedding_model,
                embedding_dimension=doc.embedding_dimension,
                source_metadata=doc.source_metadata or {},
                chunk_count=count
            ))
        return results

    @staticmethod
    def get_chunks_paginated(
        db: Session, document_id: UUID, page: int = 1, page_size: int = 20
    ) -> PaginatedResponse[ChunkResponse]:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return PaginatedResponse(items=[], total=0, page=page, page_size=page_size, total_pages=0)

        query = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id,
            DocumentChunk.processing_version == doc.processing_version
        ).order_by(DocumentChunk.chunk_index.asc())

        total = query.count()
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        offset = (page - 1) * page_size
        chunks = query.offset(offset).limit(page_size).all()

        items = []
        for c in chunks:
            v_preview = None
            if c.embedding and isinstance(c.embedding, list) and len(c.embedding) >= 8:
                v_preview = [round(x, 4) for x in c.embedding[:8]]
            
            resp = ChunkResponse(
                id=c.id,
                document_id=c.document_id,
                processing_version=c.processing_version,
                chunk_index=c.chunk_index,
                content=c.content,
                token_count=c.token_count,
                token_count_model=c.token_count_model,
                character_start=c.character_start,
                character_end=c.character_end,
                source_location=c.source_location or {},
                heading_path=c.heading_path or [],
                split_reason=c.split_reason or "target_size_limit",
                embedding_status=c.embedding_status,
                embedding_model=c.embedding_model,
                embedding_dimension=c.embedding_dimension,
                embedding_input_hash=c.embedding_input_hash,
                embedding_latency_ms=c.embedding_latency_ms,
                embedding_norm=c.embedding_norm,
                embedding_bytes=c.embedding_bytes,
                content_hash=c.content_hash,
                created_at=c.created_at,
                vector_preview=v_preview
            )
            items.append(resp)

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    def get_chunk_vector(db: Session, document_id: UUID, chunk_id: UUID) -> Optional[ChunkVectorResponse]:
        c = db.query(DocumentChunk).filter(
            DocumentChunk.id == chunk_id,
            DocumentChunk.document_id == document_id
        ).first()
        if not c or not c.embedding:
            return None

        emb = c.embedding if isinstance(c.embedding, list) else []
        serialized_bytes = c.embedding_bytes or len(json.dumps(emb).encode("utf-8"))

        return ChunkVectorResponse(
            chunk_id=c.id,
            document_id=c.document_id,
            chunk_index=c.chunk_index,
            dimension=c.embedding_dimension or len(emb),
            norm=c.embedding_norm,
            datatype="float32",
            serialized_bytes=serialized_bytes,
            vector=emb
        )

    @staticmethod
    def get_events_paginated(
        db: Session, document_id: UUID, page: int = 1, page_size: int = 50
    ) -> PaginatedResponse[EventResponse]:
        query = db.query(ProcessingEvent).filter(
            ProcessingEvent.document_id == document_id
        ).order_by(ProcessingEvent.created_at.desc())

        total = query.count()
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        offset = (page - 1) * page_size
        events = query.offset(offset).limit(page_size).all()

        items = [EventResponse.model_validate(e) for e in events]
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    def get_facts(db: Session, document_id: UUID) -> List[ExtractedFact]:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return []
        return db.query(ExtractedFact).filter(
            ExtractedFact.document_id == document_id,
            ExtractedFact.processing_version == doc.processing_version
        ).order_by(ExtractedFact.created_at.desc()).all()

    @staticmethod
    def get_summaries(db: Session, document_id: UUID) -> List[DocumentSummary]:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return []
        return db.query(DocumentSummary).filter(
            DocumentSummary.document_id == document_id,
            DocumentSummary.processing_version == doc.processing_version
        ).order_by(DocumentSummary.created_at.desc()).all()

    @staticmethod
    def get_ledger(db: Session, document_id: UUID) -> Optional[TransformationLedger]:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return None
        return db.query(TransformationLedger).filter(
            TransformationLedger.document_id == document_id,
            TransformationLedger.processing_version == doc.processing_version
        ).first()

    @staticmethod
    def compare_chunking_targets(db: Session, document_id: UUID) -> Optional[ChunkingComparisonResponse]:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc or not doc.raw_text:
            return None

        # Run non-destructive comparison on normalized text
        norm = NormalizationService.normalize_text(doc.raw_text, doc.file_extension)
        pages = doc.source_metadata.get("pages") if doc.source_metadata else None
        headings = doc.source_metadata.get("headings") if doc.source_metadata else None

        raw_comparisons = ChunkingService.compare_chunk_sizes(
            raw_text=norm.normalized_text,
            file_extension=doc.file_extension,
            pages=pages,
            headings=headings,
            target_sizes=[256, 512, 800, 1024]
        )

        comparisons_list = []
        for rc in raw_comparisons:
            candidates = [
                ChunkCandidate(
                    chunk_index=c["chunk_index"],
                    token_count=c["token_count"],
                    char_count=c["char_count"],
                    split_reason=c["split_reason"],
                    content_preview=c["content_preview"],
                    heading_path=c["heading_path"]
                )
                for c in rc["chunks"]
            ]
            comparisons_list.append(ChunkingTargetComparison(
                target_tokens=rc["target_tokens"],
                chunk_count=rc["chunk_count"],
                min_tokens=rc["min_tokens"],
                max_tokens=rc["max_tokens"],
                mean_tokens=rc["mean_tokens"],
                truncation_risk=rc["truncation_risk"],
                risk_reason=rc.get("risk_reason"),
                chunks=candidates
            ))

        return ChunkingComparisonResponse(
            document_id=doc.id,
            tokenizer_name=TokenizerService.TOKENIZER_NAME,
            model_max_length=TokenizerService.MODEL_MAX_LENGTH,
            comparisons=comparisons_list,
            architectural_finding=(
                f"The local embedding model '{TokenizerService.TOKENIZER_NAME}' has a strict input limit of "
                f"{TokenizerService.MODEL_MAX_LENGTH} tokens. Chunks targeting 800 or 1024 tokens that exceed "
                f"{TokenizerService.MODEL_MAX_LENGTH} tokens suffer silent truncation during embedding inference. "
                "Targeting 256 or 512 tokens guarantees 100% token preservation without truncation loss."
            )
        )

    @staticmethod
    def evaluate_retention(db: Session, document_id: UUID) -> Optional[EvaluationResponse]:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc or not doc.raw_text:
            return None

        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id,
            DocumentChunk.processing_version == doc.processing_version
        ).order_by(DocumentChunk.chunk_index.asc()).all()

        facts = db.query(ExtractedFact).filter(
            ExtractedFact.document_id == document_id,
            ExtractedFact.processing_version == doc.processing_version
        ).all()

        summaries = db.query(DocumentSummary).filter(
            DocumentSummary.document_id == document_id,
            DocumentSummary.processing_version == doc.processing_version
        ).all()

        chunk_dicts = [{"content": c.content, "chunk_index": c.chunk_index} for c in chunks]
        fact_dicts = [
            {"statement": f.statement, "exact_source_text": f.exact_source_text}
            for f in facts
        ]
        summary_dicts = [{"content": s.content} for s in summaries]

        eval_res = EvaluationService.evaluate_document_retention(
            raw_text=doc.raw_text,
            chunks=chunk_dicts,
            facts=fact_dicts,
            summaries=summary_dicts
        )

        return EvaluationResponse(
            document_id=doc.id,
            dataset_version=eval_res.get("dataset_version", EvaluationService.DATASET_VERSION),
            dataset_type=eval_res.get("dataset_type", "dynamic_deterministic_probes"),
            status=eval_res.get("status", "completed"),
            evaluated_items_count=eval_res.get("evaluated_items_count", 0),
            total_required_claims=eval_res.get("total_required_claims", 0),
            metrics=eval_res.get("metrics", {}),
            item_results=eval_res.get("item_results", []),
            methodology_note=eval_res.get("methodology_note", "")
        )

    @staticmethod
    def get_storage_footprint(db: Session, document_id: UUID) -> Optional[StorageFootprintResponse]:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return None

        ledger = db.query(TransformationLedger).filter(
            TransformationLedger.document_id == document_id,
            TransformationLedger.processing_version == doc.processing_version
        ).first()

        if ledger and ledger.storage_footprint:
            sf = ledger.storage_footprint
            return StorageFootprintResponse(
                document_id=doc.id,
                file_size_bytes=sf.get("file_size_bytes", doc.size_bytes),
                raw_text_bytes=sf.get("raw_text_bytes", 0),
                normalized_text_bytes=sf.get("normalized_text_bytes", 0),
                chunk_text_bytes=sf.get("chunk_text_bytes", 0),
                chunk_count=sf.get("chunk_count", 0),
                vector_count=sf.get("vector_count", 0),
                embedding_dimension=sf.get("embedding_dimension", 384),
                vector_raw_float32_bytes=sf.get("vector_raw_float32_bytes", 0),
                vector_json_serialized_bytes=sf.get("vector_json_serialized_bytes", 0),
                metadata_overhead_bytes=sf.get("metadata_overhead_bytes", 0),
                total_database_estimated_bytes=sf.get("total_database_estimated_bytes", 0),
                expansion_ratio=sf.get("expansion_ratio", 1.0),
                vector_to_chunk_ratio=sf.get("vector_to_chunk_ratio", 1.0),
                explanation=sf.get("explanation", "")
            )

        # Fallback calculation
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document_id,
            DocumentChunk.processing_version == doc.processing_version
        ).all()
        events_count = db.query(ProcessingEvent).filter(
            ProcessingEvent.document_id == document_id,
            ProcessingEvent.processing_version == doc.processing_version
        ).count()
        facts_count = db.query(ExtractedFact).filter(
            ExtractedFact.document_id == document_id,
            ExtractedFact.processing_version == doc.processing_version
        ).count()
        summaries_count = db.query(DocumentSummary).filter(
            DocumentSummary.document_id == document_id,
            DocumentSummary.processing_version == doc.processing_version
        ).count()

        norm = NormalizationService.normalize_text(doc.raw_text or "", doc.file_extension)
        sf = EvaluationService.compute_storage_footprint(
            file_size_bytes=doc.size_bytes,
            raw_text=doc.raw_text or "",
            normalized_text=norm.normalized_text,
            chunks=chunks,
            events_count=events_count,
            facts_count=facts_count,
            summaries_count=summaries_count
        )

        return StorageFootprintResponse(
            document_id=doc.id,
            file_size_bytes=sf["file_size_bytes"],
            raw_text_bytes=sf["raw_text_bytes"],
            normalized_text_bytes=sf["normalized_text_bytes"],
            chunk_text_bytes=sf["chunk_text_bytes"],
            chunk_count=sf["chunk_count"],
            vector_count=sf["vector_count"],
            embedding_dimension=sf["embedding_dimension"],
            vector_raw_float32_bytes=sf["vector_raw_float32_bytes"],
            vector_json_serialized_bytes=sf["vector_json_serialized_bytes"],
            metadata_overhead_bytes=sf["metadata_overhead_bytes"],
            total_database_estimated_bytes=sf["total_database_estimated_bytes"],
            expansion_ratio=sf["expansion_ratio"],
            vector_to_chunk_ratio=sf["vector_to_chunk_ratio"],
            explanation=sf["explanation"]
        )

    @staticmethod
    def delete(db: Session, document_id: UUID) -> bool:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return False
        db.delete(doc)
        db.commit()
        return True
