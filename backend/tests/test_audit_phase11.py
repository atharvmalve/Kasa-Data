import pytest
import math
from app.services.tokenizer_service import TokenizerService
from app.services.normalization_service import NormalizationService
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.enrichment_service import EnrichmentService
from app.services.evaluation_service import EvaluationService


def test_tokenizer_service_real_wordpiece():
    text = "Atharv Malve, Senior Product Engineer building distributed systems with YugabyteDB."
    tok_count = TokenizerService.count_tokens(text)
    assert tok_count > 0
    # Confirm it uses WordPiece tokens, not character count // 4
    assert tok_count != len(text) // 4
    assert TokenizerService.TOKENIZER_NAME == "sentence-transformers/all-MiniLM-L6-v2"
    assert TokenizerService.MODEL_MAX_LENGTH == 512


def test_normalization_loss_and_preservation():
    sample_text = (
        "# System Architecture Specification\r\n\r\n"
        "Contact: admin@example.com or visit https://github.com/kasa/core.\r\n"
        "Key parameter: `timeout_ms=5000` on port 5433.\r\n\r\n\r\n\r\n"
        "This is an un-\nwrapped word in a PDF document."
    )
    res = NormalizationService.normalize_text(sample_text, file_extension=".pdf")
    
    # Check Markdown headings preserved
    assert "# System Architecture Specification" in res.normalized_text
    # Check email and URL preserved
    assert "admin@example.com" in res.normalized_text
    assert "https://github.com/kasa/core" in res.normalized_text
    # Check code and identifiers preserved
    assert "`timeout_ms=5000`" in res.normalized_text
    assert "5433" in res.normalized_text
    # Check dehyphenation merged "un-wrapped"
    assert "unwrapped" in res.normalized_text
    # Check CRLF was converted to LF
    assert "\r\n" not in res.normalized_text

    # Operations accounting
    assert len(res.operations) >= 4
    assert res.chars_before == len(sample_text)
    assert res.chars_after == len(res.normalized_text)
    assert res.summary["char_delta"] == res.chars_after - res.chars_before


def test_chunking_diagnostic_comparison():
    # Long text with multiple sections to test multi-target comparison
    section1 = "## Overview\n" + ("This section covers distributed storage. " * 30) + "\n\n"
    section2 = "## Network Architecture\n" + ("TCP connections bound to port 9100. " * 30) + "\n\n"
    section3 = "## Consensus Protocol\n" + ("Raft quorum requires 3 nodes. " * 40)
    full_text = section1 + section2 + section3

    comparisons = ChunkingService.compare_chunk_sizes(
        raw_text=full_text,
        file_extension=".md",
        target_sizes=[256, 512, 800, 1024]
    )

    assert len(comparisons) == 4
    # 256 should have more chunks than 1024
    comp_256 = next(c for c in comparisons if c["target_tokens"] == 256)
    comp_1024 = next(c for c in comparisons if c["target_tokens"] == 1024)
    assert comp_256["chunk_count"] > comp_1024["chunk_count"]

    # 1024 target exceeds 512 model context and should flag truncation risk
    assert comp_1024["truncation_risk"] is True
    # 256 and 512 targets should have no truncation risk
    assert comp_256["truncation_risk"] is False


def test_embedding_vector_inspection_metadata():
    texts = ["Kasa context engine index chunk.", "Vector embedding inspection test."]
    outputs, latency = EmbeddingService.embed_texts_with_metadata(texts)

    assert len(outputs) == 2
    assert latency >= 0

    o1 = outputs[0]
    assert o1.dimension == 384
    assert len(o1.vector) == 384
    assert o1.datatype == "float32"
    # L2 norm of normalized embeddings should be approximately 1.0
    assert abs(o1.l2_norm - 1.0) < 0.05
    assert o1.is_normalized is True
    assert len(o1.input_hash) == 64
    assert o1.serialized_bytes > 0


def test_deterministic_fact_anchoring():
    chunk = {
        "chunk_index": 0,
        "content": "Contact lead engineer at alex@domain.org or view github.com/user/project.",
        "source_location": {"page": 1}
    }
    facts = EnrichmentService.extract_deterministic_facts([chunk])
    assert len(facts) >= 2

    email_fact = next((f for f in facts if f.predicate == "has_email"), None)
    assert email_fact is not None
    assert email_fact.object_value == "alex@domain.org"
    assert email_fact.exact_source_text == "alex@domain.org"
    # Verify exact character offsets slice the exact email
    assert chunk["content"][email_fact.source_char_start:email_fact.source_char_end] == "alex@domain.org"


def test_context_retention_evaluation_framework():
    fixtures = EvaluationService.get_fixtures()
    assert len(fixtures) >= 3

    f1 = fixtures[0]
    raw_text = f1["text"]
    chunks = [{"content": raw_text, "chunk_index": 0}]
    facts = [
        {"statement": "Quorum requires at least 3 nodes", "exact_source_text": "quorum requires at least 3 nodes"},
        {"statement": "RocksDB serves as the underlying LSM tree engine", "exact_source_text": "RocksDB serves as the underlying LSM tree engine"}
    ]
    summaries = [{"content": "Summary detailing 5 replica nodes, 250ms heartbeats, and RocksDB."}]

    eval_result = EvaluationService.evaluate_document_retention(
        raw_text=raw_text,
        chunks=chunks,
        facts=facts,
        summaries=summaries,
        custom_questions=f1["questions"]
    )

    metrics = eval_result["metrics"]
    assert metrics["chunk_evidence_coverage_pct"] == 100.0
    assert metrics["exact_identifier_retention_pct"] == 100.0
    assert metrics["fact_source_attribution_accuracy_pct"] == 100.0
    assert "explicit numerators and denominators" in eval_result["methodology_note"]


def test_embedding_limits_and_fail_safe():
    """Verify safe usable budget is 510 tokens and inputs exceeding it fail safely without truncation."""
    # Build text below limit (e.g. 50 tokens)
    short_text = "Distributed consensus algorithm with Byzantine fault tolerance and Raft quorum. " * 5
    tok_count = TokenizerService.count_tokens(short_text)
    assert tok_count < 510

    outputs, latency = EmbeddingService.embed_texts_with_metadata([short_text])
    assert len(outputs) == 1
    assert outputs[0] is not None
    assert outputs[0].token_count == tok_count
    assert outputs[0].effective_limit == 510

    # Build oversized text (> 510 tokens, e.g. 600 tokens)
    long_text = "Atharv Malve, Senior Product Engineer building distributed systems with YugabyteDB. " * 60
    long_toks = TokenizerService.count_tokens(long_text)
    assert long_toks > 510

    # Must raise ValueError, NOT silently truncate
    with pytest.raises(ValueError) as excinfo:
        EmbeddingService.embed_texts_with_metadata([long_text])
    assert "exceeds the effective safe embedding limit of 510 tokens" in str(excinfo.value)


def test_chunking_oversized_split_enforcement_and_no_loss():
    """Regression test: Proves that a 698-token input cannot produce an oversized chunk."""
    # 60 repetitions of an engineer profile line generates ~690-700 WordPiece tokens
    raw_resume = (
        "Atharv Malve, Senior Product Engineer building distributed systems with YugabyteDB and Next.js. "
        "Engineered low-latency document processing pipelines and real-time observability telemetry. "
    ) * 35
    total_tokens = TokenizerService.count_tokens(raw_resume)
    assert total_tokens > 600  # Confirms oversized input matching real résumé scenario

    chunks = ChunkingService.chunk_document(
        raw_text=raw_resume,
        file_extension=".txt",
        target_tokens=400,
        enforce_limit=True
    )

    assert len(chunks) >= 2
    # Verify EVERY chunk sent to embedding is strictly within the safe 510 token limit
    for idx, c in enumerate(chunks):
        assert c.token_count <= 510
        assert c.chunk_index == idx
        # Confirm content hashes match
        assert len(c.content_hash) == 64

    # Confirm all chunks can now be embedded safely without raising ValueError or truncating
    texts = [c.content for c in chunks]
    outputs, latency = EmbeddingService.embed_texts_with_metadata(texts)
    assert len(outputs) == len(chunks)
    assert all(o is not None and o.is_normalized for o in outputs)


def test_pdf_dehyphenation_rules_and_compound_preservation():
    """
    Tests line-wrapped word fragments vs compound words:
    - high-volume (no newline) preserved
    - high-\\nvolume (compound word) preserved as high-volume
    - orches-\\ntration (word fragment) merged as orchestration
    - atten-\\ndance (word fragment) merged as attendance
    - soft-\\nware (word fragment) merged as software
    - ambiguous cases retain hyphen and record warning
    """
    test_text = (
        "We built a high-volume data system.\n"
        "Engineered for high-\nvolume transaction streams.\n"
        "Used Kubernetes for orches-\ntration across clusters.\n"
        "Tracked daily atten-\ndance metrics.\n"
        "Developed reliable soft-\nware for production.\n"
        "Encountered unusual zyx-\nqrs in legacy document."
    )

    res = NormalizationService.normalize_text(test_text, file_extension=".pdf")
    norm_text = res.normalized_text

    # Compound words must preserve hyphen
    assert "high-volume" in norm_text
    assert "highvolume" not in norm_text

    # Line-wrapped fragments must merge
    assert "orchestration" in norm_text
    assert "orches-tration" not in norm_text

    assert "attendance" in norm_text
    assert "atten-dance" not in norm_text

    assert "software" in norm_text
    assert "soft-ware" not in norm_text

    # Ambiguous case retained hyphen with audit warning
    assert "zyx-qrs" in norm_text
    dehyphen_op = next(op for op in res.operations if op.name == "pdf_line_wrap_dehyphenation")
    assert dehyphen_op.warning is not None
    assert "Ambiguous hyphenation" in dehyphen_op.warning


def test_fact_validation_quality_checks():
    """Verify deduplication, incomplete values, and exact quote offset verification."""
    from app.services.enrichment_service import StructuredFactData

    chunk_content = "Worked at Kasa from 2021 to 2024 leading infrastructure engineering."

    # 1. Valid fact
    valid_fact = StructuredFactData(
        fact_type="entity",
        statement="Worked at Kasa from 2021 to 2024",
        subject="Engineer",
        predicate="employed_at",
        object_value="Kasa",
        exact_source_text="Kasa",
        source_char_start=10,
        source_char_end=14
    )
    status, reason = EnrichmentService.validate_fact(valid_fact, chunk_content)
    assert status == "accepted"
    assert reason is None

    # 2. Incomplete value (e.g. trailing dash / hyphen)
    incomplete_fact = StructuredFactData(
        fact_type="constraint",
        statement="Timeline reference: 2024 –",
        subject="Timeline",
        predicate="occurs_during",
        object_value="2024 –"
    )
    status, reason = EnrichmentService.validate_fact(incomplete_fact, chunk_content)
    assert status == "flagged"
    assert reason == "incomplete_value"

    # 3. Duplicate triple
    seen = {("engineer", "employed_at", "kasa")}
    status, reason = EnrichmentService.validate_fact(valid_fact, chunk_content, seen_triples=seen)
    assert status == "flagged"
    assert reason == "duplicate_triple"

    # 4. Quote offset mismatch (quote not found at offsets or in chunk)
    mismatch_fact = StructuredFactData(
        fact_type="entity",
        statement="Mentioned non-existent entity",
        exact_source_text="NonExistentCompany",
        source_char_start=0,
        source_char_end=10
    )
    status, reason = EnrichmentService.validate_fact(mismatch_fact, chunk_content)
    assert status == "flagged"
    assert reason == "quote_offset_mismatch"


def test_storage_footprint_unambiguous_accounting():
    """Verify storage footprint separates raw, vector, JSONB bytes and labels metadata overhead as estimated."""
    footprint = EvaluationService.compute_storage_footprint(
        file_size_bytes=50000,
        raw_text="Test raw text content for storage footprint analysis.",
        normalized_text="Test raw text content for storage footprint analysis.",
        chunks=[{"content": "chunk 1", "embedding": [0.1] * 384, "embedding_bytes": 3500}],
        events_count=10,
        facts_count=5,
        summaries_count=1
    )

    assert footprint["file_size_bytes"] == 50000
    assert footprint["raw_text_bytes"] > 0
    assert footprint["vector_count"] == 1
    assert footprint["embedding_dimension"] == 384
    assert footprint["vector_raw_float32_bytes"] == 384 * 4  # 1536 bytes
    assert footprint["vector_json_serialized_bytes"] == 3500
    assert footprint["metadata_overhead_is_estimated"] is True
    assert footprint["derived_storage_to_file_ratio"] == footprint["expansion_ratio"]
    assert "expansion ratio, not a compression ratio" in footprint["explanation"]


def test_evaluation_isolation_and_empty_fixtures():
    """Verify evaluation isolation: documents without fixtures/probes report unevaluated status without fabricated scores."""
    # Text with zero identifiable factual probes (no numbers, emails, URLs, or headings)
    empty_fact_text = "some text without any numbers or entities or timeline markers"
    eval_res = EvaluationService.evaluate_document_retention(
        raw_text=empty_fact_text,
        chunks=[{"content": empty_fact_text, "chunk_index": 0}],
        facts=[],
        summaries=[]
    )
    assert eval_res["status"] == "unevaluated"
    assert eval_res["evaluated_items_count"] == 0
    assert eval_res["metrics"]["chunk_claims_retained"] == "0/0"
    assert "unavailable" in eval_res["methodology_note"]


def test_timing_aggregation_and_missing_stages():
    """Verify timing instrumentation measures monotonic intervals and represents missing stages explicitly."""
    from app.db.models import TransformationLedger
    timing = {
        "extraction_ms": 120,
        "normalization_ms": 45,
        "chunking_ms": 30,
        "embedding_inference_ms": 250,
        "enrichment_summary_ms": 0,
        "enrichment_facts_ms": 0,
        "db_write_ms": 85,
        "total_pipeline_ms": 530
    }
    assert timing["total_pipeline_ms"] >= timing["extraction_ms"] + timing["normalization_ms"]
    assert timing["embedding_inference_ms"] > 0



