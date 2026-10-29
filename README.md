# Kasa --- Context Engine

A local-first document context engine for turning files into structured, auditable knowledge.

Kasa ingests documents, preserves their original evidence, normalizes extracted text, creates model-aware chunks, generates local embeddings, and exposes the processing pipeline through an inspection-focused interface.

The goal is not just to store document text. Kasa makes it possible to inspect how a document becomes machine-usable context: what changed, how it was chunked, which embedding was generated, what enrichment was produced, and how each artifact relates to its source.

> **Status:** Active development. The ingestion, chunking, embedding, enrichment, processing-history, and context-audit workflows are implemented. Interfaces and setup details may evolve as the project develops.

---

## Contents

- [Why Kasa?](#why-kasa)
- [What it can do](#what-it-can-do)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Current implementation snapshot](#current-implementation-snapshot)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Working with documents](#working-with-documents)
- [Development and testing](#development-and-testing)
- [Project structure](#project-structure)
- [Known limitations](#known-limitations)
- [Contributing](#contributing)
- [License](#license)

---

## Why Kasa?

Document-processing pipelines can hide important details behind a single "processed" status. Text may be altered during normalization, chunks may exceed a model's context limit, and summaries or extracted facts may be difficult to trace back to the source.

Kasa takes an inspectable approach:

- **Preserve source evidence:** Keep the uploaded file and extracted raw text distinct from derived representations.
- **Make transformations visible:** Track normalization operations and before/after measurements.
- **Respect model limits:** Use tokenizer-aware chunking and inspect embedding metadata.
- **Keep provenance close to the data:** Relate chunks and extracted knowledge to the source document.
- **Expose the pipeline:** Review processing events, timings, vectors, storage estimates, and evaluation tools through the UI.

Kasa is designed as a foundation for applications that need reliable, inspectable document context.

---

## What it can do

### Document Ingestion
- Ingest PDF, Markdown, and plain-text documents.
- Extract text while retaining the original upload.
- Record document metadata and content checksums.
- Track processing status and processing history.
- Retry document processing through the application.

### Auditable Normalization
- Apply deterministic text-normalization operations, including Unicode normalization and newline cleanup.
- Detect and handle selected PDF line-wrap artifacts.
- Record which transformations were applied or skipped.
- Inspect character and tokenizer-count changes before and after normalization.

> *Note:* Normalization is a derived representation; the original extracted text remains the evidence against which changes can be checked.

### Structure-Aware Chunking
- Split normalized text into ordered chunks.
- Record chunk sizes, source offsets, hashes, and split diagnostics where available.
- Compare candidate chunking targets.
- Inspect chunks in the document UI.
- Check chunk sizes against the embedding model's supported input length.

### Local Embeddings
- Generate embeddings with `sentence-transformers/all-MiniLM-L6-v2`.
- Store 384-dimensional vectors with chunk metadata.
- Inspect vector values, dimensions, input hashes, serialized payload sizes, and L2 norms.
- Enforce a safe model-input limit before embedding rather than relying on silent model truncation.

### Optional Enrichment
- Generate document summaries through the configured Groq integration.
- Extract structured facts using deterministic extraction and optional LLM-assisted enrichment.
- Inspect extracted knowledge and processing outcomes.
- Keep enrichment separate from the original source text.

> *Note:* LLM enrichment depends on provider configuration and can fail independently of local extraction and embedding.

### Context Audit and Processing Visibility
The web interface provides document views for:
- Overview and document identity
- Original extracted text
- Chunks and their metadata
- Extracted knowledge
- Processing events and stage timings
- Context Audit, including normalization changes, chunking diagnostics, vector inspection, storage accounting, and evaluation tools

> *Note:* Metrics are only meaningful when their measurement method and scope are clear. Storage figures may be estimates rather than physical database measurements, and evaluation results depend on the available ground-truth fixture.

---

## Architecture

```text
                 ┌──────────────────────┐
                 │  PDF / Markdown /    │
                 │     Plain Text       │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │   Text Extraction    │
                 └──────────┬───────────┘
                            │
                 ┌──────────┴───────────┐
                 ▼                      ▼
        ┌──────────────────┐   ┌──────────────────┐
        │ Original Evidence│   │ Normalization    │
        │ and File Metadata│   │ + Audit Ledger   │
        └──────────────────┘   └─────────┬────────┘
                                         │
                                         ▼
                               ┌────────────────────┐
                               │ Tokenizer-aware    │
                               │ Chunking           │
                               └─────────┬──────────┘
                                         │
                                         ▼
                               ┌────────────────────┐
                               │ Local Embeddings   │
                               │ 384 dimensions     │
                               └─────────┬──────────┘
                                         │
                       ┌─────────────────┴──────────┐
                       ▼                            ▼
              ┌──────────────────┐         ┌──────────────────┐
              │ YugabyteDB / YSQL│         │ Optional Summary │
              │ and Provenance   │         │ and Fact Enrich. │
              └─────────┬────────┘         └─────────┬────────┘
                        └─────────────────┬──────────┘
                                          │
                                          ▼
                               ┌────────────────────┐
                               │ FastAPI + Next.js  │
                               │ Inspection UI      │
                               └────────────────────┘
