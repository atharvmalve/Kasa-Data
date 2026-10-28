"""
Safe, idempotent document reprocessing CLI for Kasa.

Usage:
  python scripts/reprocess_document.py --filename "Atharv_Malve_Product Engineer.pdf" [--dry-run]
  python scripts/reprocess_document.py --document-id "2ca41478-c9dd-4741-8689-0cbad6138c66" [--dry-run]
"""
import sys
import os
import argparse
import uuid
import logging

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import SessionLocal
from app.db.models import Document, DocumentChunk, TransformationLedger, ExtractedFact
from app.services.ingestion_service import IngestionService
from app.services.tokenizer_service import TokenizerService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("kasa.reprocess")


def reprocess_document(document_id: str = None, filename: str = None, dry_run: bool = False):
    db = SessionLocal()
    try:
        query = db.query(Document)
        if document_id:
            try:
                doc_uuid = uuid.UUID(document_id)
            except ValueError:
                logger.error(f"Invalid UUID: '{document_id}'")
                sys.exit(1)
            docs = query.filter(Document.id == doc_uuid).all()
        elif filename:
            docs = query.filter(Document.filename == filename).all()
        else:
            logger.error("Must provide either --document-id or --filename.")
            sys.exit(1)

        if not docs:
            logger.error(f"No document found matching criteria (id={document_id}, filename='{filename}').")
            sys.exit(1)
        if len(docs) > 1:
            logger.error(f"Ambiguous query: found {len(docs)} matching documents. Please specify unique --document-id.")
            for d in docs:
                logger.error(f"  Match: ID={d.id}, Filename='{d.filename}', Datapack={d.datapack_id}")
            sys.exit(1)

        doc = docs[0]
        logger.info("=" * 60)
        logger.info("TARGET DOCUMENT IDENTIFIED:")
        logger.info(f"  Document ID:        {doc.id}")
        logger.info(f"  Filename:           {doc.filename}")
        logger.info(f"  Current Version:    {doc.processing_version}")
        logger.info(f"  Current Status:     {doc.processing_status}")
        logger.info(f"  File Size:          {doc.size_bytes} bytes")
        logger.info(f"  Raw Text Present:   {'YES' if doc.raw_text else 'NO'} ({len(doc.raw_text or '')} chars)")
        logger.info("=" * 60)

        if not doc.raw_text:
            logger.error("Target document has no raw extracted text. Cannot reprocess without source text.")
            sys.exit(1)

        # Existing chunks count
        existing_chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc.id,
            DocumentChunk.processing_version == doc.processing_version
        ).all()
        logger.info(f"Current version {doc.processing_version} has {len(existing_chunks)} chunk(s):")
        for c in existing_chunks:
            logger.info(f"  Chunk {c.chunk_index}: tokens={c.token_count}, status={c.embedding_status}, split_reason={c.split_reason}")

        if dry_run:
            logger.info("[DRY RUN] Preview complete. No changes written to database.")
            return

        next_version = doc.processing_version + 1
        logger.info(f"Starting reprocessing to version {next_version}...")

        updated_doc = IngestionService.retry_processing(db, doc.id)
        db.refresh(updated_doc)

        logger.info("=" * 60)
        logger.info(f"REPROCESSING COMPLETE: Version {updated_doc.processing_version}, Status: '{updated_doc.processing_status}'")
        logger.info("=" * 60)

        # Postcondition verification
        new_chunks = db.query(DocumentChunk).filter(
            DocumentChunk.document_id == doc.id,
            DocumentChunk.processing_version == updated_doc.processing_version
        ).order_by(DocumentChunk.chunk_index.asc()).all()

        logger.info(f"Postcondition Verification: {len(new_chunks)} chunk(s) produced:")
        for c in new_chunks:
            logger.info(
                f"  Chunk {c.chunk_index}: tokens={c.token_count} (limit: {TokenizerService.EFFECTIVE_MAX_TOKENS}), "
                f"split={c.split_reason}, embedding={c.embedding_status}, norm={c.embedding_norm}"
            )
            assert c.token_count <= TokenizerService.EFFECTIVE_MAX_TOKENS, (
                f"VIOLATION: Chunk {c.chunk_index} has {c.token_count} tokens, exceeding safe limit {TokenizerService.EFFECTIVE_MAX_TOKENS}!"
            )
            assert len(c.content_hash) == 64, f"Invalid content hash on chunk {c.chunk_index}"
            if c.embedding:
                assert len(c.embedding) == 384, f"Invalid embedding dimension on chunk {c.chunk_index}"
                assert c.embedding_norm is not None and abs(c.embedding_norm - 1.0) < 0.05, f"Vector not normalized: {c.embedding_norm}"

        ledger = db.query(TransformationLedger).filter(
            TransformationLedger.document_id == doc.id,
            TransformationLedger.processing_version == updated_doc.processing_version
        ).first()

        if ledger:
            logger.info(f"Transformation Ledger recorded: {ledger.target_tokens} target tokens, timings: {ledger.timing_breakdown}")

        logger.info("All postconditions verified successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reprocess a document in Kasa safely.")
    parser.add_argument("--document-id", help="UUID of document to reprocess")
    parser.add_argument("--filename", help="Filename of document to reprocess")
    parser.add_argument("--dry-run", action="store_true", help="Inspect without mutating database")

    args = parser.parse_args()
    if not args.document_id and not args.filename:
        parser.print_help()
        sys.exit(1)

    reprocess_document(document_id=args.document_id, filename=args.filename, dry_run=args.dry_run)

