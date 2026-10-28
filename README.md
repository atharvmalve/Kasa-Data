# Kasa --- Context Engine

**A local-first document context engine for turning files into
structured, auditable knowledge.**

Kasa ingests documents, preserves their original evidence, normalizes
extracted text, creates model-aware chunks, generates local embeddings,
and exposes the processing pipeline through an inspection-focused
interface.

The goal is not just to store document text. Kasa makes it possible to
inspect how a document becomes machine-usable context: what changed, how
it was chunked, which embedding was generated, what enrichment was
produced, and how each artifact relates to its source.

> **Status:** Phase 1 Complete & Verified (Acceptance Gate Passed).
> The local-first context ingestion, auditable normalization, model-aware chunking,
> fail-safe local embeddings (510 token limit enforcement), structured knowledge extraction
> with provenance verification, execution timing breakdown, and storage accounting are
> fully implemented, tested, and operational.

## Contents

-   [Why Kasa?](#why-kasa)
-   [What it can do](#what-it-can-do)
-   [Architecture](#architecture)
-   [Technology stack](#technology-stack)
-   [Current implementation snapshot](#current-implementation-snapshot)
-   [Getting started](#getting-started)
-   [Configuration](#configuration)
-   [Working with documents](#working-with-documents)
-   [Development and testing](#development-and-testing)
-   [Project structure](#project-structure)
-   [Known limitations](#known-limitations)
-   [Contributing](#contributing)
-   [License](#license)

## Why Kasa?

Document-processing pipelines can hide important details behind a single
"processed" status. Text may be altered during normalization, chunks may
exceed a model's context limit, and summaries or extracted facts may be
difficult to trace back to the source.

Kasa takes an inspectable approach:

-   **Preserve source evidence.** Keep the uploaded file and extracted
    raw text distinct from derived representations.
-   **Make transformations visible.** Track normalization operations and
    before/after measurements.
-   **Respect model limits.** Use tokenizer-aware chunking and inspect
    embedding metadata.
-   **Keep provenance close to the data.** Relate chunks and extracted
    knowledge to the source document.
-   **Expose the pipeline.** Review processing events, timings, vectors,
    storage estimates, and evaluation tools through the UI.

Kasa is designed as a foundation for applications that need reliable,
inspectable document context.

## What it can do

### Document ingestion

-   Ingest PDF, Markdown, and plain-text documents.
-   Extract text while retaining the original upload.
-   Record document metadata and content checksums.
-   Track processing status and processing history.
-   Retry document processing through the application.

### Auditable normalization

-   Apply deterministic text-normalization operations, including Unicode
    normalization and newline cleanup.
-   Detect and handle selected PDF line-wrap artifacts.
-   Record which transformations were applied or skipped.
-   Inspect character and tokenizer-count changes before and after
    normalization.

Normalization is a derived representation; the original extracted text
remains the evidence against which changes can be checked.

### Structure-aware chunking

-   Split normalized text into ordered chunks.
-   Record chunk sizes, source offsets, hashes, and split diagnostics
    where available.
-   Compare candidate chunking targets.
-   Inspect chunks in the document UI.
-   Check chunk sizes against the embedding model's supported input
    length.

### Local embeddings

-   Generate embeddings with `sentence-transformers/all-MiniLM-L6-v2`.
-   Store 384-dimensional vectors with chunk metadata.
-   Inspect vector values, dimensions, input hashes, serialized payload
    sizes, and L2 norms.
-   Enforce a safe model-input limit before embedding rather than
    relying on silent model truncation.

### Optional enrichment

-   Generate document summaries through the configured Groq integration.
-   Extract structured facts using deterministic extraction and optional
    LLM-assisted enrichment.
-   Inspect extracted knowledge and processing outcomes.
-   Keep enrichment separate from the original source text.

LLM enrichment depends on provider configuration and can fail
independently of local extraction and embedding.

### Context Audit and processing visibility

The web interface provides document views for:

-   Overview and document identity
-   Original extracted text
-   Chunks and their metadata
-   Extracted knowledge
-   Processing events and stage timings
-   Context Audit, including normalization changes, chunking
    diagnostics, vector inspection, storage accounting, and evaluation
    tools

Metrics are only meaningful when their measurement method and scope are
clear. Storage figures may be estimates rather than physical database
measurements, and evaluation results depend on the available
ground-truth fixture.

## Architecture

``` text
                  ┌──────────────────────┐
                  │   PDF / Markdown /   │
                  │      Plain Text      │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │   Text Extraction    │
                  └──────────┬───────────┘
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
       ┌──────────────────┐    ┌──────────────────┐
       │ Original Evidence│    │ Normalization     │
       │ and File Metadata│    │ + Audit Ledger    │
       └──────────────────┘    └─────────┬────────┘
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
                         ┌──────────────┴─────────────┐
                         ▼                            ▼
              ┌──────────────────┐        ┌──────────────────┐
              │ YugabyteDB / YSQL│        │ Optional Summary │
              │ and Provenance   │        │ and Fact Enrich. │
              └─────────┬────────┘        └─────────┬────────┘
                        └──────────────┬────────────┘
                                       ▼
                              ┌────────────────────┐
                              │ FastAPI + Next.js  │
                              │ Inspection UI      │
                              └────────────────────┘
```

### Main components

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  Next.js frontend                    Document management, chunk
                                      inspection, processing history, and
                                      Context Audit UI

  FastAPI backend                     Ingestion orchestration, API
                                      endpoints, and processing services

  YugabyteDB (YSQL)                   Persistent document records and
                                      derived processing artifacts

  Sentence Transformers               Local text embeddings

  Hugging Face tokenizer              Token counting and model-aware
                                      chunk boundaries

  Groq integration                    Optional summaries and LLM-assisted
                                      fact extraction

  Alembic                             Database schema migrations
  -----------------------------------------------------------------------

## Technology stack

-   **Frontend:** Next.js, React, TypeScript, Tailwind CSS
-   **Backend:** Python, FastAPI, Pydantic, SQLAlchemy
-   **Database:** YugabyteDB using YSQL
-   **Migrations:** Alembic
-   **Embeddings:** Sentence Transformers ---
    `sentence-transformers/all-MiniLM-L6-v2`
-   **Enrichment:** Optional Groq API integration
-   **Runtime:** Local development with Docker-supported database
    infrastructure

## Current implementation snapshot

The following figures describe the implementation and an observed
single-document run. They are **not a standardized performance
benchmark**.

  ------------------------------------------------------------------------------
  Measurement                         Current implementation / observed result
  ----------------------------------- ------------------------------------------
  Embedding model                     `sentence-transformers/all-MiniLM-L6-v2`

  Embedding vector dimension          384

  Model maximum sequence length       512 tokens, subject to tokenizer
                                      special-token accounting

  Observed safe content limit         510 WordPiece tokens in the current audit
                                      configuration; verified against the loaded
                                      tokenizer/model before relying on it

  Sample document                     3 chunks generated

  Sample vector storage               Approximately 3.9 KB serialized per vector
                                      in the observed UI

  Observed end-to-end processing time Approximately 23.8 seconds for one sample
                                      document, including optional enrichment
                                      and database writes
  ------------------------------------------------------------------------------

**How to interpret these numbers:** timings depend on hardware, model
initialization, document structure, database state, and external
enrichment latency. The sample processing time is not a throughput
claim. Serialized vector size is not the same as raw float32 payload
size or physical database storage. Run measurements in your own
environment before comparing performance.

## Getting started

Kasa is intended to run locally. The exact commands may vary slightly
with the current repository layout; use the checked-in dependency files,
environment example, and application entry points as the source of
truth.

### Prerequisites

Install:

-   Git
-   Python 3.11 or a version supported by the backend dependency files
-   Node.js and npm compatible with the frontend
-   Docker, for a local database environment
-   A running YugabyteDB YSQL instance

Optional: - A Groq API key for summary generation and LLM-assisted fact
extraction

### 1. Clone the repository

``` bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd kasa-context-engine
```

Replace the repository URL and directory name with the values used when
publishing the project.

### 2. Start YugabyteDB

Start a local YugabyteDB instance with YSQL accessible on port `5433`,
or use the repository's Docker Compose configuration if one is provided.

Confirm that the database is accepting connections before starting the
backend. Use the database name, username, password, and host configured
for your local environment.

Kasa's local development setup has used port `5433` for YSQL.

### 3. Configure the backend

Open a terminal in the backend directory.

Create and activate a virtual environment:

**Windows PowerShell**

``` powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

``` bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the backend dependencies using the dependency file included in
the repository. For example, if the project contains `requirements.txt`:

``` bash
pip install -r requirements.txt
```

If the project uses `pyproject.toml`, Poetry, or another dependency
manager instead, follow that file's instructions.

Configure the backend environment using the checked-in `.env.example` or
documented settings. At minimum, verify the YSQL connection settings.
Set the Groq API key only if you want optional LLM enrichment.

**Never commit `.env` files, database credentials, API keys, or private
documents.**

### 4. Apply database migrations

From the backend environment, run the project's Alembic migrations:

``` bash
alembic upgrade head
```

Run this only after configuring the database connection. If the
repository specifies a working directory or migration configuration
path, execute the command from that location.

If migrations fail, inspect the error and migration state before
retrying. Do not reset an existing database to resolve a migration
problem.

### 5. Start the FastAPI backend

Use the application entry point defined by the current backend package.
A typical FastAPI development command looks like:

``` bash
uvicorn <module_path>:app --reload
```

Replace `<module_path>` with the actual module containing the FastAPI
`app` instance. Check the backend source or existing run configuration
rather than guessing the import path.

Once running, open the API documentation at the backend's `/docs` route
if FastAPI's interactive documentation is enabled.

### 6. Configure and start the frontend

Open another terminal in the frontend directory:

``` bash
npm install
```

Create the local frontend environment file if the project provides an
example, and set the backend API base URL to the address where FastAPI
is running.

Start the development server:

``` bash
npm run dev
```

Open <http://localhost:3000>.

### 7. Process a document

1.  Open the Kasa web interface.
2.  Create or select a data pack if required by the current UI.
3.  Upload a PDF, Markdown, or plain-text document.
4.  Wait for processing to finish.
5.  Inspect the document's original text, chunks, extracted knowledge,
    processing history, and Context Audit.
6.  Review warnings and reported measurements rather than assuming that
    a `Processed` status proves every derived artifact is semantically
    correct.

## Configuration

Configuration names can change during development. Check the
repository's backend configuration module and `.env.example` for the
exact supported variable names.

Typical configuration categories include:

  -----------------------------------------------------------------------
  Setting                             Purpose
  ----------------------------------- -----------------------------------
  Database connection                 Connect the backend to local
                                      YugabyteDB / YSQL

  Embedding model                     Select the supported local Sentence
                                      Transformers model

  Groq API key                        Enable optional summary and
                                      LLM-assisted extraction

  Frontend API base URL               Point the Next.js app to the local
                                      FastAPI server

  Upload/storage path                 Configure where original uploaded
                                      files are stored, if applicable
  -----------------------------------------------------------------------

Do not assume that every category is configurable in every revision. Use
the actual configuration schema in the repository.

## Development and testing

Run checks from the relevant backend or frontend directory.

### Backend tests

If the repository uses pytest:

``` bash
pytest
```

For a focused test:

``` bash
pytest path/to/test_file.py -q
```

### Frontend checks

Use the scripts defined in `package.json`. Common commands include:

``` bash
npm run lint
npm run build
```

Run TypeScript checks using the script provided by the repository, or
the project's configured TypeScript compiler command.

### Before opening a pull request

-   Add or update tests for changed behavior.
-   Verify that raw source evidence remains unchanged.
-   Check that token counts and source offsets are consistent.
-   Confirm that embedding inputs respect the actual model limit.
-   Verify migration behavior without deleting existing data.
-   Run backend tests and frontend checks.
-   Document any checks that could not be run locally.

## Project structure

The exact layout may evolve. The main areas of the codebase are expected
to include:

``` text
kasa-context-engine/
├── backend/
│   ├── API routes
│   ├── database models and migrations
│   ├── extraction and ingestion services
│   ├── normalization and chunking services
│   ├── embedding and enrichment services
│   └── tests
├── frontend/
│   ├── app/
│   ├── components/
│   └── API client and TypeScript types
├── README.md
└── .env.example
```

Use the actual repository tree as authoritative; these names describe
the logical organization rather than guaranteeing every path exists
exactly as shown.

## Known limitations

Kasa is under active development. Keep these limitations in mind:

-   PDF text extraction quality depends on the source document and
    extraction library.
-   Normalization is heuristic and must be validated against the raw
    text.
-   Embeddings represent text numerically; a valid vector does not
    guarantee semantic correctness.
-   LLM-generated summaries and facts can be incomplete or inaccurate
    and require provenance and validation.
-   Performance numbers vary by machine, model initialization, and
    provider latency.
-   Storage figures may represent serialized payload estimates rather
    than physical database usage.
-   Evaluation quality depends on the availability and coverage of
    labelled ground-truth examples.
-   Retrieval and agent workflows are not part of the current documented
    feature set.

Issues and contributions that improve correctness, reproducibility, and
observability are especially welcome.

## Contributing

Contributions are welcome. For substantial changes, open an issue first
to discuss the problem and proposed approach.

### Suggested workflow

1.  Fork the repository.
2.  Create a focused branch.
3.  Make a small, reviewable change.
4.  Add tests for the behavior being changed.
5.  Run the relevant backend and frontend checks.
6.  Update documentation when behavior or configuration changes.
7.  Open a pull request explaining the problem, solution, testing
    performed, and any known limitations.

### Contribution principles

-   Preserve original evidence and provenance.
-   Prefer deterministic, testable transformations.
-   Never silently truncate model input.
-   Make failure states explicit.
-   Do not fabricate metrics or claim unverified performance
    improvements.
-   Keep optional LLM integrations isolated from the core local
    pipeline.
-   Avoid committing secrets, personal documents, generated artifacts,
    or local database files.

### Reporting bugs

Include, where possible:

-   Operating system and Python/Node versions
-   Database version and connection mode
-   Steps to reproduce
-   Expected and actual behavior
-   Relevant sanitized logs
-   Test results

Do not attach private documents or secrets to public issues. A small
synthetic reproduction is preferred.

## License

Choose and add a license before accepting external contributions. If no
license file is present, the project is not automatically open source
merely because its source code is public.

------------------------------------------------------------------------

**Kasa --- make document context inspectable, reproducible, and grounded
in its source.**
#   K a s a - D a t a  
 