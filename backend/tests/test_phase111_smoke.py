import pytest
from app.services.tokenizer_service import TokenizerService
from app.services.normalization_service import NormalizationService
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.enrichment_service import EnrichmentService, StructuredFactData
from app.services.evaluation_service import EvaluationService


def test_phase111_comprehensive_smoke():
    """
    Final functional smoke test covering:
    1. Short document
    2. Document exceeding the embedding limit
    3. PDF-style line-wrap example (word fragments)
    4. Genuine hyphenated compound (preserved)
    5. Duplicate and incomplete facts
    6. Document with no evaluation fixture (unevaluated state)
    """
    # 1. Short document processing
    short_text = "Kasa is a local-first verifiable context engine."
    short_chunks = ChunkingService.chunk_document(raw_text=short_text, file_extension=".txt")
    assert len(short_chunks) == 1
    assert short_chunks[0].token_count < 20
    emb_out, _ = EmbeddingService.embed_texts_with_metadata([short_chunks[0].content])
    assert len(emb_out) == 1
    assert emb_out[0].dimension == 384
    assert abs(emb_out[0].l2_norm - 1.0) < 0.05

    # 2. Document exceeding embedding limit (> 510 tokens)
    long_raw = (
        "Enterprise cloud infrastructure with automated multi-region deployment. "
        "High availability consensus architecture using YugabyteDB and RocksDB engines. "
    ) * 40
    long_tokens = TokenizerService.count_tokens(long_raw)
    assert long_tokens > 510  # Exceeds model sequence limit

    # Chunking MUST split into subchunks each strictly <= 510 tokens
    long_chunks = ChunkingService.chunk_document(
        raw_text=long_raw,
        file_extension=".txt",
        target_tokens=400,
        enforce_limit=True
    )
    assert len(long_chunks) >= 2
    for c in long_chunks:
        assert c.token_count <= TokenizerService.EFFECTIVE_MAX_TOKENS
    # Verify embedding inference executes without failure
    long_emb, _ = EmbeddingService.embed_texts_with_metadata([c.content for c in long_chunks])
    assert len(long_emb) == len(long_chunks)
    assert all(e is not None and e.dimension == 384 for e in long_emb)

    # 3 & 4. PDF normalization: genuine compound vs line-wrapped fragments
    pdf_sample = (
        "Operating in high-\nvolume environments requiring orches-\n"
        "tration and continuous atten-\ndance with secure soft-\nware."
    )
    norm_res = NormalizationService.normalize_text(pdf_sample, file_extension=".pdf")
    # Genuine compound preserved
    assert "high-volume" in norm_res.normalized_text
    assert "highvolume" not in norm_res.normalized_text
    # Line wrapped fragments merged
    assert "orchestration" in norm_res.normalized_text
    assert "attendance" in norm_res.normalized_text
    assert "software" in norm_res.normalized_text

    # 5. Duplicate and incomplete facts
    chunk_text = "Founded Acme Corp in 2020 and served as CEO until 2024."
    f_valid = StructuredFactData(
        fact_type="entity",
        statement="Founded Acme Corp in 2020",
        subject="Founder",
        predicate="founded",
        object_value="Acme Corp",
        exact_source_text="Acme Corp",
        source_char_start=8,
        source_char_end=17
    )
    status, reason = EnrichmentService.validate_fact(f_valid, chunk_text)
    assert status == "accepted"
    assert reason is None

    # Incomplete fact (trailing dash)
    f_incomplete = StructuredFactData(
        fact_type="constraint",
        statement="Tenure: 2024 –",
        subject="Tenure",
        predicate="during",
        object_value="2024 –"
    )
    status_inc, reason_inc = EnrichmentService.validate_fact(f_incomplete, chunk_text)
    assert status_inc == "flagged"
    assert reason_inc == "incomplete_value"

    # Duplicate fact
    seen_triples = {("founder", "founded", "acme corp")}
    status_dup, reason_dup = EnrichmentService.validate_fact(f_valid, chunk_text, seen_triples=seen_triples)
    assert status_dup == "flagged"
    assert reason_dup == "duplicate_triple"

    # 6. Document with no evaluation fixture
    unmatched_text = "Generic unstructured notes without standard benchmarks."
    eval_unmatched = EvaluationService.evaluate_document_retention(
        raw_text=unmatched_text,
        chunks=[{"content": unmatched_text, "chunk_index": 0}],
        facts=[],
        summaries=[]
    )
    assert eval_unmatched["status"] == "unevaluated"
    assert eval_unmatched["evaluated_items_count"] == 0
    assert eval_unmatched["metrics"]["chunk_claims_retained"] == "0/0"

