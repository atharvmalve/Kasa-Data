import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.db.base import utc_now
from app.db.models import (
    Document, DocumentChunk, DocumentSummary, ExtractedFact, ProcessingEvent, TransformationLedger
)
from app.utils.hashing import compute_checksums
from app.services.extraction_service import (
    ExtractionService, ExtractionError, UnsupportedFileTypeError, EmptyDocumentError, ScannedPdfError
)
from app.services.tokenizer_service import TokenizerService
from app.services.normalization_service import NormalizationService
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.enrichment_service import EnrichmentService, StructuredFactData
from app.services.evaluation_service import EvaluationService


class IngestionService:
    @staticmethod
    def _record_event(
        db: Session,
        document_id: uuid.UUID,
        version: int,
        stage: str,
        status: str,
        message: str,
        duration_ms: Optional[int] = None,
        metadata: Optional[dict] = None
    ):
        event = ProcessingEvent(
            document_id=document_id,
            processing_version=version,
            stage=stage,
            status=status,
            message=message,
            duration_ms=duration_ms,
            metadata_json=metadata or {}
        )
        db.add(event)
        db.commit()

    @classmethod
    def ingest_file(
        cls,
        db: Session,
        datapack_id: uuid.UUID,
        filename: str,
        file_bytes: bytes,
        mime_type: str = "application/octet-stream"
    ) -> Tuple[Document, bool]:
        """
        Ingest a file into the specified datapack.
        Returns (document, is_duplicate).
        """
        # Validate extension
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        if ext not in ["pdf", "md", "txt"]:
            raise UnsupportedFileTypeError(
                f"File '{filename}' has unsupported extension '.{ext}'. Allowed types: .pdf, .md, .txt"
            )

        # Validate size
        if len(file_bytes) > settings.MAX_FILE_SIZE_BYTES:
            max_mb = settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise ValueError(f"File size exceeds maximum allowed limit of {max_mb} MB.")

        # Compute checksums
        md5_chk, sha256_chk = compute_checksums(file_bytes)

        # Check for duplicate in datapack
        existing = db.query(Document).filter(
            Document.datapack_id == datapack_id,
            Document.sha256_checksum == sha256_chk
        ).first()

        if existing:
            # Record duplicate event and return existing document
            cls._record_event(
                db=db,
                document_id=existing.id,
                version=existing.processing_version,
                stage="upload",
                status="skipped",
                message=f"Duplicate content detected for file '{filename}'. Reusing existing document.",
                metadata={"duplicate_of": str(existing.id), "sha256": sha256_chk}
            )
            return existing, True

        # Create new Document record
        doc = Document(
            datapack_id=datapack_id,
            filename=filename,
            file_extension=f".{ext}",
            mime_type=mime_type,
            size_bytes=len(file_bytes),
            md5_checksum=md5_chk,
            sha256_checksum=sha256_chk,
            processing_status="uploaded",
            processing_version=1,
            summary_status="pending",
            embedding_status="pending",
            source_metadata={}
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        cls._record_event(
            db=db,
            document_id=doc.id,
            version=doc.processing_version,
            stage="upload",
            status="completed",
            message=f"File '{filename}' uploaded successfully ({len(file_bytes)} bytes).",
            metadata={"size_bytes": len(file_bytes), "md5": md5_chk, "sha256": sha256_chk}
        )

        # Run pipeline
        cls.process_pipeline(db, doc, file_bytes=file_bytes)
        db.refresh(doc)
        return doc, False

    @classmethod
    def process_pipeline(
        cls,
        db: Session,
        doc: Document,
        file_bytes: Optional[bytes] = None
    ):
        """Execute extraction, deterministic normalization, chunking, embedding, enrichment, and ledger recording."""
        pipeline_start_t = time.time()
        version = doc.processing_version
        doc.processing_status = "processing"
        doc.last_error = None
        db.commit()

        extraction_ms = 0
        normalization_ms = 0
        chunking_ms = 0
        embedding_inference_ms = 0
        enrichment_summary_ms = 0
        enrichment_facts_ms = 0
        db_write_ms = 0

        # STAGE 1: Text Extraction
        t0 = time.time()
        cls._record_event(db, doc.id, version, "extraction", "started", "Beginning text extraction.")
        
        extraction_res = None
        if file_bytes is not None:
            try:
                extraction_res = ExtractionService.extract(file_bytes, doc.filename, doc.mime_type)
                doc.raw_text = extraction_res.raw_text
                doc.source_metadata = extraction_res.source_metadata
                db.commit()
                
                extraction_ms = int((time.time() - t0) * 1000)
                cls._record_event(
                    db, doc.id, version, "extraction", "completed",
                    f"Text extracted successfully ({len(extraction_res.raw_text)} chars).",
                    duration_ms=extraction_ms,
                    metadata=extraction_res.source_metadata
                )
            except Exception as e:
                extraction_ms = int((time.time() - t0) * 1000)
                error_msg = f"Extraction failed: {str(e)}"
                doc.processing_status = "failed"
                doc.last_error = error_msg
                db.commit()
                cls._record_event(db, doc.id, version, "extraction", "failed", error_msg, duration_ms=extraction_ms)
                return
        else:
            # Reprocessing/retry with existing raw_text
            if not doc.raw_text:
                doc.processing_status = "failed"
                doc.last_error = "No raw text available for reprocessing."
                db.commit()
                cls._record_event(db, doc.id, version, "extraction", "failed", "No raw text available for reprocessing.")
                return

        # STAGE 1.5: Deterministic Normalization
        t0 = time.time()
        cls._record_event(db, doc.id, version, "normalization", "started", "Beginning deterministic normalization audit.")
        norm_res = NormalizationService.normalize_text(doc.raw_text, doc.file_extension)
        normalized_text = norm_res.normalized_text
        normalization_ms = int((time.time() - t0) * 1000)
        cls._record_event(
            db, doc.id, version, "normalization", "completed",
            f"Normalized text ({norm_res.summary['initial_chars']} -> {norm_res.summary['final_chars']} chars, delta: {norm_res.summary['char_delta']}).",
            duration_ms=normalization_ms,
            metadata=norm_res.summary
        )

        # STAGE 2: Structure-Aware Tokenizer Chunking (with embedding limit enforcement)
        t0 = time.time()
        cls._record_event(db, doc.id, version, "chunking", "started", "Beginning structure-aware chunking with HuggingFace tokenizer.")
        try:
            pages = extraction_res.pages if extraction_res else doc.source_metadata.get("pages")
            headings = extraction_res.headings if extraction_res else doc.source_metadata.get("headings")
            chunk_datas = ChunkingService.chunk_document(
                raw_text=normalized_text,
                file_extension=doc.file_extension,
                pages=pages,
                headings=headings,
                target_tokens=settings.TARGET_CHUNK_TOKENS,
                overlap_tokens=settings.CHUNK_OVERLAP_TOKENS,
                enforce_limit=True
            )

            if not chunk_datas:
                raise ValueError("No chunks produced from document.")

            db_write_t0 = time.time()
            # Remove any pre-existing chunks for this version to avoid duplicates
            db.query(DocumentChunk).filter(
                DocumentChunk.document_id == doc.id,
                DocumentChunk.processing_version == version
            ).delete()

            chunk_records = []
            for cd in chunk_datas:
                c = DocumentChunk(
                    document_id=doc.id,
                    processing_version=version,
                    chunk_index=cd.chunk_index,
                    content=cd.content,
                    token_count=cd.token_count,
                    token_count_model=cd.token_count_model,
                    character_start=cd.character_start,
                    character_end=cd.character_end,
                    source_location=cd.source_location,
                    heading_path=cd.heading_path,
                    split_reason=cd.split_reason,
                    embedding_status="pending",
                    content_hash=cd.content_hash
                )
                chunk_records.append(c)

            db.bulk_save_objects(chunk_records)
            db.commit()
            db_write_ms += int((time.time() - db_write_t0) * 1000)

            chunking_ms = int((time.time() - t0) * 1000)
            cls._record_event(
                db, doc.id, version, "chunking", "completed",
                f"Generated {len(chunk_records)} chunks using {TokenizerService.TOKENIZER_NAME}.",
                duration_ms=chunking_ms,
                metadata={"chunk_count": len(chunk_records), "tokenizer": TokenizerService.TOKENIZER_NAME}
            )
        except Exception as e:
            chunking_ms = int((time.time() - t0) * 1000)
            error_msg = f"Chunking failed: {str(e)}"
            doc.processing_status = "failed"
            doc.last_error = error_msg
            db.commit()
            cls._record_event(db, doc.id, version, "chunking", "failed", error_msg, duration_ms=chunking_ms)
            return

        # STAGE 3: Local Embeddings with Metadata Tracking
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc.id,
            DocumentChunk.processing_version == version
        ).order_by(DocumentChunk.chunk_index.asc()).all()

        t0 = time.time()
        cls._record_event(db, doc.id, version, "embedding", "started", f"Generating local embeddings ({settings.EMBEDDING_MODEL}).")
        embedding_success = False
        total_emb_bytes = 0
        total_emb_latency = 0
        try:
            texts = [c.content for c in chunks]
            emb_outputs, total_emb_latency = EmbeddingService.embed_texts_with_metadata(texts)

            db_write_t0 = time.time()
            for idx, c in enumerate(chunks):
                if emb_outputs and idx < len(emb_outputs) and emb_outputs[idx]:
                    output = emb_outputs[idx]
                    c.embedding = output.vector
                    c.embedding_norm = output.l2_norm
                    c.embedding_bytes = output.serialized_bytes
                    c.embedding_input_hash = output.input_hash
                    c.embedding_latency_ms = int(total_emb_latency / max(1, len(chunks)))
                    c.embedding_status = "completed"
                    c.embedding_model = settings.EMBEDDING_MODEL
                    c.embedding_dimension = settings.EMBEDDING_DIMENSION
                    total_emb_bytes += output.serialized_bytes
                else:
                    c.embedding_status = "failed"

            doc.embedding_status = "completed"
            doc.embedding_model = settings.EMBEDDING_MODEL
            doc.embedding_dimension = settings.EMBEDDING_DIMENSION
            db.commit()
            db_write_ms += int((time.time() - db_write_t0) * 1000)

            embedding_inference_ms = int((time.time() - t0) * 1000)
            cls._record_event(
                db, doc.id, version, "embedding", "completed",
                f"Generated {len(chunks)} embeddings ({settings.EMBEDDING_DIMENSION}-dim, {total_emb_bytes} bytes serialized).",
                duration_ms=embedding_inference_ms,
                metadata={
                    "model": settings.EMBEDDING_MODEL,
                    "dimension": settings.EMBEDDING_DIMENSION,
                    "total_bytes": total_emb_bytes
                }
            )
            embedding_success = True
        except Exception as e:
            embedding_inference_ms = int((time.time() - t0) * 1000)
            error_msg = f"Embedding generation failed: {str(e)}"
            logger.warning(error_msg)
            for c in chunks:
                c.embedding_status = "failed"
            doc.embedding_status = "failed"
            db.commit()
            cls._record_event(db, doc.id, version, "embedding", "failed", error_msg, duration_ms=embedding_inference_ms)

        # STAGE 4: Optional LLM Summary
        t0 = time.time()
        summary_usage = None
        if EnrichmentService.is_configured():
            cls._record_event(db, doc.id, version, "enrichment_summary", "started", "Generating document summary with Groq.")
            summary_res = EnrichmentService.generate_summary(doc.raw_text, doc.filename)
            summary_text, summary_err = summary_res
            summary_usage = getattr(summary_res, "usage", {})
            enrichment_summary_ms = int((time.time() - t0) * 1000)
            if summary_text:
                db_write_t0 = time.time()
                db.query(DocumentSummary).filter(
                    DocumentSummary.document_id == doc.id,
                    DocumentSummary.processing_version == version
                ).delete()

                tok_count = TokenizerService.count_tokens(summary_text)
                summary_rec = DocumentSummary(
                    document_id=doc.id,
                    processing_version=version,
                    summary_type="document",
                    content=summary_text,
                    token_count=tok_count,
                    model_name=settings.GROQ_MODEL,
                    status="completed"
                )
                db.add(summary_rec)
                doc.summary_status = "completed"
                db.commit()
                db_write_ms += int((time.time() - db_write_t0) * 1000)

                cls._record_event(
                    db, doc.id, version, "enrichment_summary", "completed",
                    "Document summary generated successfully.",
                    duration_ms=enrichment_summary_ms,
                    metadata={"model": settings.GROQ_MODEL, "usage": summary_usage or {}}
                )
            else:
                doc.summary_status = "failed"
                db.commit()
                cls._record_event(
                    db, doc.id, version, "enrichment_summary", "failed",
                    summary_err or "Failed to generate summary.",
                    duration_ms=enrichment_summary_ms
                )
        else:
            enrichment_summary_ms = int((time.time() - t0) * 1000)
            doc.summary_status = "not_configured"
            db.commit()
            cls._record_event(
                db, doc.id, version, "enrichment_summary", "skipped",
                "Groq API key not configured. Summary skipped."
            )

        # STAGE 5: Structured Facts (Deterministic Pattern Facts + LLM Facts)
        t0 = time.time()
        fact_usage = None
        cls._record_event(db, doc.id, version, "enrichment_facts", "started", "Extracting structured facts (deterministic + LLM).")
        chunk_dicts = [
            {"chunk_index": c.chunk_index, "content": c.content, "source_location": c.source_location, "id": c.id}
            for c in chunks
        ]

        # Always run deterministic extraction first
        det_facts = EnrichmentService.extract_deterministic_facts(chunk_dicts)

        if EnrichmentService.is_configured():
            facts_res = EnrichmentService.extract_facts(chunk_dicts, doc.filename)
            all_facts, facts_err = facts_res
            fact_usage = getattr(facts_res, "usage", {})
        else:
            all_facts = det_facts
            facts_err = None

        enrichment_facts_ms = int((time.time() - t0) * 1000)

        db_write_t0 = time.time()
        # Clean old facts for this version
        db.query(ExtractedFact).filter(
            ExtractedFact.document_id == doc.id,
            ExtractedFact.processing_version == version
        ).delete()

        chunk_map = {c.chunk_index: c for c in chunks}
        fallback_chunk = chunks[0] if chunks else None

        for f in all_facts:
            source_c = chunk_map.get(f.source_chunk_index, fallback_chunk)
            if source_c:
                fact_rec = ExtractedFact(
                    document_id=doc.id,
                    processing_version=version,
                    fact_type=f.fact_type,
                    subject=f.subject,
                    predicate=f.predicate,
                    object_value=f.object_value,
                    statement=f.statement,
                    confidence=f.confidence,
                    source_chunk_id=source_c.id,
                    source_location=source_c.source_location or {},
                    exact_source_text=f.exact_source_text,
                    source_char_start=f.source_char_start,
                    source_char_end=f.source_char_end,
                    extraction_method=f.extraction_method,
                    validation_status=getattr(f, "validation_status", "accepted"),
                    validation_reason=getattr(f, "validation_reason", None)
                )
                db.add(fact_rec)
        db.commit()
        db_write_ms += int((time.time() - db_write_t0) * 1000)

        cls._record_event(
            db, doc.id, version, "enrichment_facts", "completed",
            f"Extracted {len(all_facts)} structured facts ({len(det_facts)} deterministic).",
            duration_ms=enrichment_facts_ms,
            metadata={"fact_count": len(all_facts), "deterministic_count": len(det_facts)}
        )

        # STAGE 6: Storage Footprint & Transformation Ledger Persistence
        events_count = db.query(ProcessingEvent).filter(
            ProcessingEvent.document_id == doc.id,
            ProcessingEvent.processing_version == version
        ).count()
        facts_count = len(all_facts)
        summaries_count = 1 if doc.summary_status == "completed" else 0

        footprint = EvaluationService.compute_storage_footprint(
            file_size_bytes=doc.size_bytes,
            raw_text=doc.raw_text or "",
            normalized_text=normalized_text,
            chunks=chunks,
            events_count=events_count,
            facts_count=facts_count,
            summaries_count=summaries_count
        )

        # Compute token statistics across chunks
        chunk_tokens = [c.token_count for c in chunks] if chunks else [0]
        min_tok = min(chunk_tokens) if chunk_tokens else 0
        max_tok = max(chunk_tokens) if chunk_tokens else 0
        mean_tok = round(sum(chunk_tokens) / max(1, len(chunk_tokens)), 1)

        src_meta = doc.source_metadata or {}
        page_count = src_meta.get("page_count", 1)
        pages_with_text = src_meta.get("pages_with_text", page_count)
        pages_without_text = src_meta.get("pages_without_text", 0)
        extraction_warnings = src_meta.get("warnings", [])

        db_write_t0 = time.time()
        # Clean old ledger for this version
        db.query(TransformationLedger).filter(
            TransformationLedger.document_id == doc.id,
            TransformationLedger.processing_version == version
        ).delete()

        total_pipeline_ms = int((time.time() - pipeline_start_t) * 1000)
        timing_breakdown = {
            "extraction_ms": extraction_ms if file_bytes is not None else None,
            "normalization_ms": normalization_ms,
            "chunking_ms": chunking_ms,
            "embedding_inference_ms": embedding_inference_ms,
            "enrichment_summary_ms": enrichment_summary_ms,
            "enrichment_facts_ms": enrichment_facts_ms,
            "db_write_ms": db_write_ms,
            "total_pipeline_ms": total_pipeline_ms
        }

        ledger = TransformationLedger(
            document_id=doc.id,
            processing_version=version,
            file_size_bytes=doc.size_bytes,
            file_md5=doc.md5_checksum,
            file_sha256=doc.sha256_checksum,
            extracted_char_count=len(doc.raw_text or ""),
            extracted_byte_count=len((doc.raw_text or "").encode("utf-8")),
            extracted_token_count=norm_res.summary.get("initial_tokens", 0),
            tokenizer_name=TokenizerService.TOKENIZER_NAME,
            tokenizer_version=TokenizerService.TOKENIZER_VERSION,
            page_count=page_count,
            pages_with_text=pages_with_text,
            pages_without_text=pages_without_text,
            extraction_warnings=extraction_warnings,
            normalization_operations=[op.to_dict() if hasattr(op, "to_dict") else op for op in norm_res.operations],
            normalized_char_count=norm_res.summary.get("final_chars", 0),
            normalized_byte_count=len(normalized_text.encode("utf-8")),
            normalized_token_count=norm_res.summary.get("final_tokens", 0),
            chunking_strategy="structure_aware_tokenizer",
            target_tokens=settings.TARGET_CHUNK_TOKENS,
            overlap_tokens=settings.CHUNK_OVERLAP_TOKENS,
            chunk_count=len(chunks),
            chunk_token_stats={"min": min_tok, "max": max_tok, "mean": mean_tok},
            embedding_provider="sentence_transformers",
            embedding_model=settings.EMBEDDING_MODEL,
            embedding_dimension=settings.EMBEDDING_DIMENSION,
            embedding_datatype="float32",
            embedding_normalized=True,
            embedding_total_latency_ms=total_emb_latency,
            embedding_storage_bytes=total_emb_bytes,
            enrichment_model=settings.GROQ_MODEL if EnrichmentService.is_configured() else None,
            enrichment_latency_ms=((summary_usage or {}).get("latency_ms", 0) + (fact_usage or {}).get("latency_ms", 0)),
            enrichment_token_usage={"summary": summary_usage or {}, "facts": fact_usage or {}},
            timing_breakdown=timing_breakdown,
            storage_footprint=footprint,
            pipeline_version="1.1.1"
        )
        db.add(ledger)
        db.commit()
        db_write_ms += int((time.time() - db_write_t0) * 1000)
        # update db_write_ms inside ledger timing breakdown
        timing_breakdown["db_write_ms"] = db_write_ms
        timing_breakdown["total_pipeline_ms"] = int((time.time() - pipeline_start_t) * 1000)
        ledger.timing_breakdown = dict(timing_breakdown)
        db.commit()

        # STAGE 7: Final Status Update
        doc.processed_at = utc_now()
        if embedding_success and doc.summary_status in ["completed", "skipped", "not_configured"]:
            doc.processing_status = "processed"
        elif not embedding_success:
            doc.processing_status = "partially_processed"
            doc.last_error = "Local embedding generation failed."
        elif doc.summary_status == "failed":
            doc.processing_status = "partially_processed"
            doc.last_error = "Enrichment failed."
        else:
            doc.processing_status = "processed"

        db.commit()

        cls._record_event(
            db, doc.id, version, "completion",
            "completed" if doc.processing_status == "processed" else "partially_completed",
            f"Document processing finished with status '{doc.processing_status}' and transformation ledger recorded."
        )

    @classmethod
    def retry_processing(cls, db: Session, document_id: uuid.UUID) -> Document:
        """Retry processing for a document by incrementing version and restarting."""
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document with id {document_id} not found.")

        # Increment version
        doc.processing_version += 1
        new_version = doc.processing_version
        doc.processing_status = "processing"
        doc.last_error = None
        doc.embedding_status = "pending"
        doc.summary_status = "pending"
        db.commit()

        cls._record_event(
            db, doc.id, new_version, "retry", "started",
            f"Reprocessing retry initiated for version {new_version}."
        )

        cls.process_pipeline(db, doc, file_bytes=None)
        db.refresh(doc)
        return doc
