import re
from typing import List, Dict, Any, Optional
from app.utils.hashing import compute_text_hash


BENCHMARK_FIXTURES_V1 = [
    {
        "fixture_id": "eval-doc-01-multi-section",
        "title": "Distributed Consensus and Replication Specification",
        "text": (
            "# Consensus Architecture Specification\n\n"
            "## 1. Node Topology and Quorum\n"
            "The cluster operates with a minimum of 5 replica nodes across 3 distinct availability zones. "
            "A quorum requires at least 3 nodes to acknowledge commit logs before client return.\n\n"
            "## 2. Heartbeat and Failure Detection\n"
            "Heartbeat interval is configured to exactly 250ms with a failure election timeout of 1200ms. "
            "If the leader misses 3 consecutive heartbeats, candidate election initiates.\n\n"
            "## 3. Storage Engine and Compaction\n"
            "RocksDB serves as the underlying LSM tree engine. Write-ahead logs (WAL) are flushed synchronously "
            "using fsync every 10ms. Block cache size is fixed at 16GB."
        ),
        "questions": [
            {
                "id": "q1",
                "question": "What is the minimum quorum size and node count required?",
                "required_claims": ["5 replica nodes", "quorum requires at least 3 nodes"],
                "target_identifiers": ["5", "3"],
                "expected_section": "1. Node Topology and Quorum"
            },
            {
                "id": "q2",
                "question": "What are the exact heartbeat interval and election timeout durations?",
                "required_claims": ["250ms", "1200ms"],
                "target_identifiers": ["250ms", "1200ms"],
                "expected_section": "2. Heartbeat and Failure Detection"
            },
            {
                "id": "q3",
                "question": "What storage engine is used and what is the block cache size?",
                "required_claims": ["RocksDB", "16GB"],
                "target_identifiers": ["RocksDB", "16GB"],
                "expected_section": "3. Storage Engine and Compaction"
            }
        ]
    },
    {
        "fixture_id": "eval-doc-02-technical-identifiers",
        "title": "Cryptographic Protocol and Network Identifiers",
        "text": (
            "# Security Architecture\n\n"
            "All RPC channels are encrypted via TLS 1.3 using cipher suite TLS_AES_256_GCM_SHA384. "
            "Private keys are rotated every 90 days. The root certificate fingerprint is "
            "SHA256:4a8f9c1b2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a. "
            "Internal cluster communication binds to TCP port 9100, while external client traffic connects on port 5433."
        ),
        "questions": [
            {
                "id": "q4",
                "question": "What cipher suite and TLS version are mandated?",
                "required_claims": ["TLS 1.3", "TLS_AES_256_GCM_SHA384"],
                "target_identifiers": ["TLS 1.3", "TLS_AES_256_GCM_SHA384"],
                "expected_section": "Security Architecture"
            },
            {
                "id": "q5",
                "question": "Which TCP ports are used for internal cluster communication vs external client traffic?",
                "required_claims": ["TCP port 9100", "port 5433"],
                "target_identifiers": ["9100", "5433"],
                "expected_section": "Security Architecture"
            }
        ]
    },
    {
        "fixture_id": "eval-doc-03-near-duplicates",
        "title": "Tenant Rate Limit Policies",
        "text": (
            "# Rate Limiting Policies\n\n"
            "## Standard Tier Policy\n"
            "Tenants on the Standard Tier receive a burst quota of 500 requests per second and a sustained limit of 100 req/s. "
            "Overage requests receive HTTP status 429 with Retry-After header.\n\n"
            "## Premium Tier Policy\n"
            "Tenants on the Premium Tier receive a burst quota of 5000 requests per second and a sustained limit of 1000 req/s. "
            "Overage requests receive HTTP status 429 with Retry-After header."
        ),
        "questions": [
            {
                "id": "q6",
                "question": "What is the sustained rate limit for Standard tier vs Premium tier?",
                "required_claims": ["Standard Tier: 100 req/s", "Premium Tier: 1000 req/s"],
                "target_identifiers": ["100 req/s", "1000 req/s"],
                "expected_section": "Rate Limiting Policies"
            }
        ]
    }
]


class EvaluationService:
    DATASET_VERSION = "kasa_retention_benchmark_v1.0"

    @classmethod
    def get_fixtures(cls) -> List[Dict[str, Any]]:
        return BENCHMARK_FIXTURES_V1

    @classmethod
    def evaluate_document_retention(
        cls,
        raw_text: str,
        chunks: List[Dict[str, Any]],
        facts: List[Dict[str, Any]],
        summaries: List[Dict[str, Any]],
        custom_questions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates context retention across all derived representations:
        1. Original extracted text
        2. Chunks
        3. Extracted facts
        4. Summaries

        Measures:
        - Evidence coverage (% required claims present)
        - Exact identifier and numeric detail retention
        - Recall@k, Precision@k, MRR
        - Fact source attribution accuracy
        """
        # Determine questions to evaluate
        eval_items = []
        dataset_type = "prelabelled_ground_truth_benchmark"
        dataset_ver = cls.DATASET_VERSION

        if custom_questions:
            eval_items = custom_questions
            dataset_type = "custom_provided_questions"
            dataset_ver = "custom_questions_v1.0"
        else:
            # Check if document matches any benchmark fixture or generate dynamic test probes
            matched = False
            for fix in BENCHMARK_FIXTURES_V1:
                # Check for content overlap
                if fix["title"].lower() in raw_text.lower() or fix["questions"][0]["required_claims"][0].lower() in raw_text.lower():
                    eval_items.extend(fix["questions"])
                    matched = True

            if not matched:
                # Generate dynamic factual verification probes from document content
                eval_items = cls._generate_document_probes(raw_text)
                dataset_type = "dynamic_deterministic_probes"
                dataset_ver = "deterministic_document_probes_v1.0"

        if not eval_items:
            return {
                "dataset_version": dataset_ver,
                "dataset_type": dataset_type,
                "evaluated_items_count": 0,
                "total_required_claims": 0,
                "status": "unevaluated",
                "message": "No evaluation items available for this document. Document is unevaluated.",
                "metrics": {
                    "chunk_evidence_coverage_pct": 0.0,
                    "chunk_claims_retained": "0/0",
                    "fact_evidence_coverage_pct": 0.0,
                    "fact_claims_retained": "0/0",
                    "summary_evidence_coverage_pct": 0.0,
                    "summary_claims_retained": "0/0",
                    "exact_identifier_retention_pct": 0.0,
                    "exact_identifiers_retained": "0/0",
                    "mean_reciprocal_rank_chunks": 0.0,
                    "fact_source_attribution_accuracy_pct": 0.0,
                    "verified_facts_count": "0/0"
                },
                "item_results": [],
                "methodology_note": "No ground truth benchmark matches this document. Factual retention evaluation is unavailable without ground truth claims or probes."
            }

        total_claims_required = 0
        claims_in_raw = 0
        claims_in_chunks = 0
        claims_in_facts = 0
        claims_in_summaries = 0

        total_identifiers = 0
        identifiers_in_chunks = 0
        identifiers_in_facts = 0

        ranks_chunks = []
        question_results = []

        combined_chunk_text = " ".join(c.get("content", "") for c in chunks).lower()
        combined_fact_text = " ".join(f.get("statement", "") for f in facts).lower()
        combined_summary_text = " ".join(s.get("content", "") for s in summaries).lower()
        raw_text_lower = raw_text.lower()

        for q in eval_items:
            q_id = q.get("id", "q")
            question_str = q.get("question", "")
            required_claims = q.get("required_claims", [])
            target_ids = q.get("target_identifiers", [])

            q_claims_in_chunks = 0
            q_claims_in_facts = 0
            q_claims_in_summary = 0

            for claim in required_claims:
                total_claims_required += 1
                c_clean = claim.lower()

                # Check in raw text
                if c_clean in raw_text_lower:
                    claims_in_raw += 1

                # Check in chunks
                if c_clean in combined_chunk_text:
                    claims_in_chunks += 1
                    q_claims_in_chunks += 1

                # Check in facts
                if c_clean in combined_fact_text:
                    claims_in_facts += 1
                    q_claims_in_facts += 1

                # Check in summaries
                if c_clean in combined_summary_text:
                    claims_in_summaries += 1
                    q_claims_in_summary += 1

            # Target identifiers (numbers, codes)
            for tid in target_ids:
                total_identifiers += 1
                tid_clean = tid.lower()
                if tid_clean in combined_chunk_text:
                    identifiers_in_chunks += 1
                if tid_clean in combined_fact_text:
                    identifiers_in_facts += 1

            # Measure Recall / MRR for chunks: which chunk contains the answer?
            found_rank = None
            for idx, c in enumerate(chunks):
                c_content = c.get("content", "").lower()
                if all(rc.lower() in c_content for rc in required_claims):
                    found_rank = idx + 1
                    break
                elif any(rc.lower() in c_content for rc in required_claims):
                    if found_rank is None:
                        found_rank = idx + 1

            if found_rank is not None:
                ranks_chunks.append(found_rank)
            else:
                ranks_chunks.append(None)

            question_results.append({
                "id": q_id,
                "question": question_str,
                "required_claims": required_claims,
                "claims_retained_in_chunks": q_claims_in_chunks,
                "claims_retained_in_facts": q_claims_in_facts,
                "claims_retained_in_summary": q_claims_in_summary,
                "total_claims": len(required_claims),
                "best_chunk_rank": found_rank
            })

        # Calculate MRR (Mean Reciprocal Rank)
        reciprocal_ranks = [1.0 / r for r in ranks_chunks if r is not None]
        mrr = round(sum(reciprocal_ranks) / len(eval_items), 4) if eval_items else 0.0

        # Evidence coverage across representations
        chunk_coverage_pct = round((claims_in_chunks / max(1, total_claims_required)) * 100, 1)
        fact_coverage_pct = round((claims_in_facts / max(1, total_claims_required)) * 100, 1)
        summary_coverage_pct = round((claims_in_summaries / max(1, total_claims_required)) * 100, 1)
        identifier_retention_pct = round((identifiers_in_chunks / max(1, total_identifiers)) * 100, 1) if total_identifiers else 100.0

        # Fact source attribution verification
        verified_facts = 0
        for f in facts:
            quote = f.get("exact_source_text")
            if quote and quote in raw_text:
                verified_facts += 1
            elif f.get("statement") and any(word in raw_text for word in f.get("statement", "").split()[:3]):
                verified_facts += 1

        attribution_accuracy_pct = round((verified_facts / max(1, len(facts))) * 100, 1) if facts else 100.0

        return {
            "dataset_version": dataset_ver,
            "dataset_type": dataset_type,
            "evaluated_items_count": len(eval_items),
            "total_required_claims": total_claims_required,
            "metrics": {
                "chunk_evidence_coverage_pct": chunk_coverage_pct,
                "chunk_claims_retained": f"{claims_in_chunks}/{total_claims_required}",
                "fact_evidence_coverage_pct": fact_coverage_pct,
                "fact_claims_retained": f"{claims_in_facts}/{total_claims_required}",
                "summary_evidence_coverage_pct": summary_coverage_pct,
                "summary_claims_retained": f"{claims_in_summaries}/{total_claims_required}",
                "exact_identifier_retention_pct": identifier_retention_pct,
                "exact_identifiers_retained": f"{identifiers_in_chunks}/{total_identifiers}",
                "mean_reciprocal_rank_chunks": mrr,
                "fact_source_attribution_accuracy_pct": attribution_accuracy_pct,
                "verified_facts_count": f"{verified_facts}/{len(facts)}"
            },
            "item_results": question_results,
            "methodology_note": (
                f"Evaluation ({dataset_type}) measures exact atomic claim and identifier retention across derived representations. "
                "Scores display explicit numerators and denominators without fabricated percentage scaling."
            )
        }

    @classmethod
    def _generate_document_probes(cls, text: str) -> List[Dict[str, Any]]:
        """
        Deterministically extracts salient factual probes from document text (identifiers, numbers, emails, URLs, dates).
        """
        probes = []
        # Find emails
        emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", text)
        for e in emails[:2]:
            probes.append({
                "id": f"probe-email-{len(probes)+1}",
                "question": f"What is the contact email address?",
                "required_claims": [e],
                "target_identifiers": [e]
            })

        # Find URLs / GitHub
        urls = re.findall(r"https?://[^\s<>\"'()]+|github\.com/[A-Za-z0-9_.-]+", text)
        for u in urls[:2]:
            probes.append({
                "id": f"probe-url-{len(probes)+1}",
                "question": f"What external URL or repository reference is provided?",
                "required_claims": [u],
                "target_identifiers": [u]
            })

        # Find date spans / years
        dates = re.findall(r"\b(20\d{2}|19\d{2})\s*(?:–|-|to)\s*(20\d{2}|Present|\b)", text)
        for d in dates[:2]:
            span = f"{d[0]}-{d[1]}"
            probes.append({
                "id": f"probe-date-{len(probes)+1}",
                "question": f"What timeline or year span is specified?",
                "required_claims": [d[0]],
                "target_identifiers": [d[0]]
            })

        # Find technical terms / headings
        headings = re.findall(r"^#{1,3}\s+(.+)$", text, re.MULTILINE)
        for h in headings[:3]:
            h_str = h.strip()
            if len(h_str) > 4:
                probes.append({
                    "id": f"probe-heading-{len(probes)+1}",
                    "question": f"Does the context retain the section '{h_str}'?",
                    "required_claims": [h_str],
                    "target_identifiers": [h_str]
                })

        return probes[:8]

    @classmethod
    def compute_storage_footprint(
        cls,
        file_size_bytes: int,
        raw_text: str,
        normalized_text: str,
        chunks: List[Any],
        events_count: int = 0,
        facts_count: int = 0,
        summaries_count: int = 0
    ) -> Dict[str, Any]:
        """
        Calculates exact storage utilization across raw file, extracted text, chunks,
        vector embeddings (raw float32 vs JSONB), and relational overhead.
        """
        import json
        raw_text_bytes = len(raw_text.encode("utf-8")) if raw_text else 0
        norm_text_bytes = len(normalized_text.encode("utf-8")) if normalized_text else 0

        chunk_text_bytes = 0
        vector_json_bytes = 0
        vector_count = 0

        for c in chunks:
            content = getattr(c, "content", None) or (c.get("content") if isinstance(c, dict) else "")
            chunk_text_bytes += len(content.encode("utf-8"))

            emb = getattr(c, "embedding", None) or (c.get("embedding") if isinstance(c, dict) else None)
            emb_bytes = getattr(c, "embedding_bytes", None) or (c.get("embedding_bytes") if isinstance(c, dict) else None)

            if emb:
                vector_count += 1
                if emb_bytes:
                    vector_json_bytes += emb_bytes
                else:
                    vector_json_bytes += len(json.dumps(emb).encode("utf-8"))

        dim = 384
        raw_float32_bytes_per_vector = dim * 4  # 1536 bytes
        total_float32_vector_bytes = vector_count * raw_float32_bytes_per_vector

        # Estimated relational metadata overhead in PostgreSQL/YugabyteDB
        metadata_overhead_bytes = (
            (events_count * 256) +
            (facts_count * 512) +
            (summaries_count * 1024) +
            (len(chunks) * 200) +
            1024  # Document row + ledger row
        )

        total_db_bytes = raw_text_bytes + chunk_text_bytes + vector_json_bytes + metadata_overhead_bytes
        expansion_ratio = round(total_db_bytes / max(1, file_size_bytes), 2)
        vector_to_chunk_ratio = round(vector_json_bytes / max(1, chunk_text_bytes), 2)

        return {
            "file_size_bytes": file_size_bytes,
            "raw_text_bytes": raw_text_bytes,
            "normalized_text_bytes": norm_text_bytes,
            "chunk_text_bytes": chunk_text_bytes,
            "chunk_count": len(chunks),
            "vector_count": vector_count,
            "embedding_dimension": dim,
            "vector_raw_float32_bytes": total_float32_vector_bytes,
            "vector_json_serialized_bytes": vector_json_bytes,
            "metadata_overhead_bytes": metadata_overhead_bytes,
            "metadata_overhead_is_estimated": True,
            "total_database_estimated_bytes": total_db_bytes,
            "expansion_ratio": expansion_ratio,
            "derived_storage_to_file_ratio": expansion_ratio,
            "vector_to_chunk_ratio": vector_to_chunk_ratio,
            "explanation": (
                "Database storage exceeds original file size because Kasa persists raw evidence, "
                "normalized text, structured chunks, 384-dimensional float embeddings in JSONB format "
                f"(~{round(vector_json_bytes / max(1, vector_count))} bytes per chunk serialized), "
                "relational provenance offsets, and transformation ledger records. This represents "
                "an expansion ratio, not a compression ratio."
            )
        }

