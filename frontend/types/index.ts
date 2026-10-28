export interface DataPack {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  file_count: number;
  processing_status?: string | null;
}

export interface Document {
  id: string;
  datapack_id: string;
  filename: string;
  file_extension: string;
  mime_type: string;
  size_bytes: number;
  md5_checksum: string;
  sha256_checksum: string;
  processing_status: "uploaded" | "processing" | "partially_processed" | "processed" | "failed";
  processing_version: number;
  created_at: string;
  updated_at: string;
  processed_at: string | null;
  last_error: string | null;
  summary_status: string;
  embedding_status: string;
  embedding_model: string | null;
  embedding_dimension: number | null;
  source_metadata: Record<string, unknown>;
  chunk_count: number;
}

export interface DocumentContent {
  id: string;
  filename: string;
  raw_text: string | null;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  processing_version: number;
  chunk_index: number;
  content: string;
  token_count: number | null;
  token_count_model?: string | null;
  character_start: number | null;
  character_end: number | null;
  source_location: Record<string, unknown>;
  heading_path: string[];
  split_reason?: string;
  embedding_status: string;
  embedding_model: string | null;
  embedding_dimension: number | null;
  embedding_norm?: number | null;
  embedding_bytes?: number | null;
  embedding_input_hash?: string | null;
  embedding_latency_ms?: number | null;
  content_hash: string;
  created_at: string;
  vector_preview?: number[] | null;
}

export interface ChunkVectorResponse {
  chunk_id: string;
  document_id: string;
  chunk_index: number;
  dimension: number;
  norm: number | null;
  datatype: string;
  serialized_bytes: number;
  vector: number[];
}

export interface DocumentSummary {
  id: string;
  document_id: string;
  processing_version: number;
  summary_type: string;
  content: string;
  token_count: number | null;
  model_name: string | null;
  status: string;
  created_at: string;
}

export interface ExtractedFact {
  id: string;
  document_id: string;
  processing_version: number;
  fact_type: string;
  subject: string | null;
  predicate: string | null;
  object_value: string | null;
  statement: string;
  confidence: number | null;
  source_chunk_id: string | null;
  source_location: Record<string, unknown>;
  exact_source_text?: string | null;
  source_char_start?: number | null;
  source_char_end?: number | null;
  extraction_method: string;
  validation_status?: string | null;
  validation_reason?: string | null;
  created_at: string;
}

export interface ProcessingEvent {
  id: string;
  document_id: string;
  processing_version: number;
  stage: string;
  status: string;
  message: string;
  duration_ms: number | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface NormalizationOperation {
  name: string;
  version: string;
  applied: boolean;
  chars_before: number;
  chars_after: number;
  chars_delta: number;
  tokens_before: number;
  tokens_after: number;
  tokens_delta: number;
  diff_snippet: string | null;
  reason: string;
  warning?: string | null;
}

export interface TransformationLedger {
  id: string;
  document_id: string;
  processing_version: number;
  file_size_bytes: number;
  file_md5: string;
  file_sha256: string;
  extracted_char_count: number;
  extracted_byte_count: number;
  extracted_token_count: number;
  tokenizer_name: string;
  tokenizer_version: string;
  page_count: number;
  pages_with_text: number;
  pages_without_text: number;
  extraction_warnings: unknown[];
  normalization_operations: NormalizationOperation[];
  normalized_char_count: number;
  normalized_byte_count: number;
  normalized_token_count: number;
  chunking_strategy: string;
  target_tokens: number;
  overlap_tokens: number;
  chunk_count: number;
  chunk_token_stats: {
    min: number;
    max: number;
    mean: number;
  };
  embedding_provider: string;
  embedding_model: string;
  embedding_dimension: number;
  embedding_datatype: string;
  embedding_normalized: boolean;
  embedding_total_latency_ms: number | null;
  embedding_storage_bytes: number;
  enrichment_model: string | null;
  enrichment_latency_ms: number | null;
  enrichment_token_usage: Record<string, unknown>;
  timing_breakdown?: Record<string, number> | null;
  effective_embedding_limit?: number | null;
  storage_footprint: StorageFootprint;
  pipeline_version: string;
  created_at: string;
}

export interface ChunkCandidate {
  chunk_index: number;
  token_count: number;
  char_count: number;
  split_reason: string;
  content_preview: string;
  heading_path: string[];
}

export interface ChunkingTargetComparison {
  target_tokens: number;
  chunk_count: number;
  min_tokens: number;
  max_tokens: number;
  mean_tokens: number;
  truncation_risk: boolean;
  risk_reason: string | null;
  chunks: ChunkCandidate[];
}

export interface ChunkingComparisonResponse {
  document_id: string;
  tokenizer_name: string;
  model_max_length: number;
  comparisons: ChunkingTargetComparison[];
  architectural_finding: string;
}

export interface EvaluationItemResult {
  id: string;
  question: string;
  required_claims: string[];
  claims_retained_in_chunks: number;
  claims_retained_in_facts: number;
  claims_retained_in_summary: number;
  total_claims: number;
  best_chunk_rank: number | null;
}

export interface EvaluationResponse {
  document_id: string;
  dataset_version: string;
  dataset_type?: string | null;
  evaluated_items_count: number;
  total_required_claims: number;
  metrics: {
    chunk_evidence_coverage_pct: number;
    chunk_claims_retained: string;
    fact_evidence_coverage_pct: number;
    fact_claims_retained: string;
    summary_evidence_coverage_pct: number;
    summary_claims_retained: string;
    exact_identifier_retention_pct: number;
    exact_identifiers_retained: string;
    mean_reciprocal_rank_chunks: number;
    fact_source_attribution_accuracy_pct: number;
    verified_facts_count: string;
  };
  item_results: EvaluationItemResult[];
  methodology_note: string;
}

export interface StorageFootprint {
  file_size_bytes: number;
  raw_text_bytes: number;
  normalized_text_bytes: number;
  chunk_text_bytes: number;
  chunk_count: number;
  vector_count: number;
  embedding_dimension: number;
  vector_raw_float32_bytes: number;
  vector_json_serialized_bytes: number;
  metadata_overhead_bytes: number;
  metadata_overhead_is_estimated?: boolean;
  total_database_estimated_bytes: number;
  expansion_ratio: number;
  derived_storage_to_file_ratio?: number;
  vector_to_chunk_ratio: number;
  explanation: string;
}

export interface StorageFootprintResponse extends StorageFootprint {
  document_id: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
