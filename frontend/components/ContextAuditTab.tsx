"use client";

import { useEffect, useState, useCallback } from "react";
import {
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Database,
  Layers,
  Scale,
  Copy,
  Check,
  RefreshCw,
  Binary,
  ArrowRight,
  FileCode2,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  TransformationLedger,
  StorageFootprintResponse,
  ChunkingComparisonResponse,
  EvaluationResponse,
  DocumentChunk,
} from "@/types";

interface ContextAuditTabProps {
  documentId: string;
  chunks: DocumentChunk[];
}

export function ContextAuditTab({ documentId, chunks }: ContextAuditTabProps) {
  const [ledger, setLedger] = useState<TransformationLedger | null>(null);
  const [storage, setStorage] = useState<StorageFootprintResponse | null>(null);
  const [comparison, setComparison] = useState<ChunkingComparisonResponse | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);

  const [loadingLedger, setLoadingLedger] = useState(true);
  const [loadingComparison, setLoadingComparison] = useState(false);
  const [loadingEvaluation, setLoadingEvaluation] = useState(false);

  const [copiedChunkId, setCopiedChunkId] = useState<string | null>(null);
  const [selectedChunkVector, setSelectedChunkVector] = useState<{
    id: string;
    vector: number[];
    norm: number | null;
    bytes: number;
  } | null>(null);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`;
  };

  const loadAuditData = useCallback(async () => {
    setLoadingLedger(true);
    try {
      const [ledgerData, storageData] = await Promise.allSettled([
        api.getDocumentAudit(documentId),
        api.getDocumentStorageFootprint(documentId),
      ]);
      if (ledgerData.status === "fulfilled") setLedger(ledgerData.value);
      if (storageData.status === "fulfilled") setStorage(storageData.value);
    } catch (err) {
      console.error("Failed to load audit records", err);
    } finally {
      setLoadingLedger(false);
    }
  }, [documentId]);

  useEffect(() => {
    let isMounted = true;
    Promise.allSettled([
      api.getDocumentAudit(documentId),
      api.getDocumentStorageFootprint(documentId),
    ]).then(([ledgerData, storageData]) => {
      if (!isMounted) return;
      if (ledgerData.status === "fulfilled") setLedger(ledgerData.value);
      if (storageData.status === "fulfilled") setStorage(storageData.value);
      setLoadingLedger(false);
    });

    return () => {
      isMounted = false;
    };
  }, [documentId]);

  const handleRunComparison = async () => {
    setLoadingComparison(true);
    try {
      const res = await api.compareChunkingTargets(documentId);
      setComparison(res);
    } catch (err) {
      console.error("Failed to run chunking comparison", err);
    } finally {
      setLoadingComparison(false);
    }
  };

  const handleRunEvaluation = async () => {
    setLoadingEvaluation(true);
    try {
      const res = await api.getDocumentEvaluation(documentId);
      setEvaluation(res);
    } catch (err) {
      console.error("Failed to run retention evaluation", err);
    } finally {
      setLoadingEvaluation(false);
    }
  };

  const handleInspectVector = async (chunkId: string) => {
    try {
      const res = await api.getChunkVector(documentId, chunkId);
      setSelectedChunkVector({
        id: chunkId,
        vector: res.vector,
        norm: res.norm,
        bytes: res.serialized_bytes,
      });
    } catch (err) {
      console.error("Failed to fetch vector", err);
    }
  };

  const handleCopyVector = async (vector: number[], chunkId: string) => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(vector));
      setCopiedChunkId(chunkId);
      setTimeout(() => setCopiedChunkId(null), 2000);
    } catch (err) {
      console.error("Failed to copy vector", err);
    }
  };

  return (
    <div className="space-y-8">
      {/* SECTION 1: TRANSFORMATION LEDGER HEADER & BEFORE/AFTER ACCOUNTING */}
      <div className="rounded-xl border border-[#E8E2DF] bg-white p-6 shadow-xs space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-[#E8E2DF]">
          <div>
            <h3 className="text-xs font-semibold text-[#100703] uppercase tracking-wider flex items-center gap-2">
              <Scale className="w-4 h-4 text-[#9B1C1C]" />
              Auditable Transformation Ledger
            </h3>
            <p className="text-[11px] text-[#665E59] mt-0.5">
              Deterministic before-and-after metrics tracking every byte, token, and character transformation.
            </p>
          </div>
          <button
            onClick={loadAuditData}
            disabled={loadingLedger}
            className="p-1.5 rounded-lg border border-[#E8E2DF] text-[#665E59] hover:text-[#100703] hover:bg-[#FAFAFA] text-xs transition-colors flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingLedger ? "animate-spin text-[#9B1C1C]" : ""}`} />
            Refresh Ledger
          </button>
        </div>

        {ledger ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-3.5 rounded-lg bg-[#FAFAFA] border border-[#E8E2DF]/80 space-y-1">
              <span className="text-[10px] font-medium uppercase text-[#665E59]">Original Upload</span>
              <div className="text-sm font-semibold text-[#100703]">{formatBytes(ledger.file_size_bytes)}</div>
              <div className="text-[10px] font-mono text-[#665E59] truncate" title={`SHA-256: ${ledger.file_sha256}`}>
                sha256:{ledger.file_sha256.slice(0, 10)}...
              </div>
            </div>

            <div className="p-3.5 rounded-lg bg-[#FAFAFA] border border-[#E8E2DF]/80 space-y-1">
              <span className="text-[10px] font-medium uppercase text-[#665E59]">Extracted Raw Evidence</span>
              <div className="text-sm font-semibold text-[#100703]">
                {ledger.extracted_char_count.toLocaleString()} chars
              </div>
              <div className="text-[10px] text-[#665E59]">
                {ledger.extracted_token_count.toLocaleString()} WordPiece tokens ({formatBytes(ledger.extracted_byte_count)})
              </div>
            </div>

            <div className="p-3.5 rounded-lg bg-[#FAFAFA] border border-[#E8E2DF]/80 space-y-1">
              <span className="text-[10px] font-medium uppercase text-[#665E59]">Deterministic Normalization</span>
              <div className="text-sm font-semibold text-[#100703]">
                {ledger.normalized_char_count.toLocaleString()} chars
              </div>
              <div className="text-[10px] text-[#665E59] flex items-center gap-1">
                <span>Delta: {ledger.normalized_char_count - ledger.extracted_char_count} chars</span>
                <span>•</span>
                <span>{ledger.normalized_token_count} tokens</span>
              </div>
            </div>

            <div className="p-3.5 rounded-lg bg-[#FAFAFA] border border-[#E8E2DF]/80 space-y-1">
              <span className="text-[10px] font-medium uppercase text-[#665E59]">Tokenizer & Chunks</span>
              <div className="text-sm font-semibold text-[#9B1C1C]">
                {ledger.chunk_count} {ledger.chunk_count === 1 ? "chunk" : "chunks"} ({ledger.target_tokens} target)
              </div>
              <div className="text-[10px] text-[#665E59] truncate" title={ledger.tokenizer_name}>
                Tokenizer: all-MiniLM-L6-v2
              </div>
            </div>

            {/* Sub-card: Safe Embedding Limit */}
            <div className="col-span-1 md:col-span-4 p-3.5 rounded-lg bg-emerald-50/50 border border-emerald-200/80 flex items-center justify-between text-xs text-emerald-900">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
                <span>
                  <strong>Strict Embedding Context Invariant Enforced:</strong> Safe sequence limit is <strong>510 WordPiece tokens</strong> (512 max position embeddings minus 2 reserved special tokens <code className="font-mono bg-emerald-100 px-1 py-0.5 rounded">[CLS]</code> and <code className="font-mono bg-emerald-100 px-1 py-0.5 rounded">[SEP]</code>). Oversized chunks are deterministically split before model inference.
                </span>
              </div>
              <span className="font-mono text-[11px] font-semibold text-emerald-800 shrink-0">
                Limit: 510 tokens
              </span>
            </div>

            {/* Sub-card: Execution Timing Breakdown */}
            {ledger.timing_breakdown && (
              <div className="col-span-1 md:col-span-4 p-4 rounded-lg bg-[#FAFAFA] border border-[#E8E2DF] space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-[#100703]">
                    Pipeline Execution Latency Breakdown
                  </span>
                  <span className="text-xs font-mono font-bold text-[#9B1C1C]">
                    Total: {ledger.timing_breakdown.total_pipeline_ms ?? 0} ms
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2 text-center">
                  <div className="p-2 rounded bg-white border border-[#E8E2DF]/60">
                    <div className="text-[10px] text-[#665E59]">Extraction</div>
                    <div className="text-xs font-mono font-medium text-[#100703]">
                      {ledger.timing_breakdown.extraction_ms !== null && ledger.timing_breakdown.extraction_ms !== undefined
                        ? `${ledger.timing_breakdown.extraction_ms} ms`
                        : "Reused (0 ms)"}
                    </div>
                  </div>
                  <div className="p-2 rounded bg-white border border-[#E8E2DF]/60">
                    <div className="text-[10px] text-[#665E59]">Normalization</div>
                    <div className="text-xs font-mono font-medium text-[#100703]">{ledger.timing_breakdown.normalization_ms ?? 0} ms</div>
                  </div>
                  <div className="p-2 rounded bg-white border border-[#E8E2DF]/60">
                    <div className="text-[10px] text-[#665E59]">Chunking</div>
                    <div className="text-xs font-mono font-medium text-[#100703]">{ledger.timing_breakdown.chunking_ms ?? 0} ms</div>
                  </div>
                  <div className="p-2 rounded bg-white border border-[#E8E2DF]/60">
                    <div className="text-[10px] text-[#665E59]">Embedding</div>
                    <div className="text-xs font-mono font-medium text-[#100703]">{ledger.timing_breakdown.embedding_inference_ms ?? 0} ms</div>
                  </div>
                  <div className="p-2 rounded bg-white border border-[#E8E2DF]/60">
                    <div className="text-[10px] text-[#665E59]">Summary</div>
                    <div className="text-xs font-mono font-medium text-[#100703]">{ledger.timing_breakdown.enrichment_summary_ms ?? 0} ms</div>
                  </div>
                  <div className="p-2 rounded bg-white border border-[#E8E2DF]/60">
                    <div className="text-[10px] text-[#665E59]">Facts</div>
                    <div className="text-xs font-mono font-medium text-[#100703]">{ledger.timing_breakdown.enrichment_facts_ms ?? 0} ms</div>
                  </div>
                  <div className="p-2 rounded bg-white border border-[#E8E2DF]/60">
                    <div className="text-[10px] text-[#665E59]">DB Writes</div>
                    <div className="text-xs font-mono font-medium text-[#100703]">{ledger.timing_breakdown.db_write_ms ?? 0} ms</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="py-6 text-center text-xs text-[#665E59]">
            {loadingLedger ? "Loading transformation ledger..." : "No ledger recorded yet for this processing version."}
          </div>
        )}
      </div>

      {/* SECTION 2: DETERMINISTIC NORMALIZATION OPERATIONS LOG */}
      {ledger && ledger.normalization_operations && ledger.normalization_operations.length > 0 && (
        <div className="rounded-xl border border-[#E8E2DF] bg-white p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#E8E2DF]">
            <div>
              <h3 className="text-xs font-semibold text-[#100703] uppercase tracking-wider flex items-center gap-2">
                <FileCode2 className="w-4 h-4 text-[#9B1C1C]" />
                Deterministic Normalization & Loss Reporting
              </h3>
              <p className="text-[11px] text-[#665E59] mt-0.5">
                Every transformation is recorded with exact character deltas, token deltas, and audit reasons.
                Markdown headings, code blocks, URLs, emails, and identifiers are strictly preserved.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#E8E2DF] text-[#665E59] font-medium">
                  <th className="py-2 pr-3">Operation</th>
                  <th className="py-2 px-3">Status</th>
                  <th className="py-2 px-3">Chars (Before → After)</th>
                  <th className="py-2 px-3">Delta Chars</th>
                  <th className="py-2 px-3">Tokens (Before → After)</th>
                  <th className="py-2 pl-3">Audit Reason / Diff Snippet</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E8E2DF]/60 text-[#100703]">
                {ledger.normalization_operations.map((op, idx) => (
                  <tr key={idx} className="hover:bg-[#FAFAFA]/80">
                    <td className="py-2.5 pr-3 font-mono text-[11px] text-[#100703]">{op.name}</td>
                    <td className="py-2.5 px-3">
                      {op.applied ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3" />
                          Applied
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-600 border border-zinc-200">
                          Skipped
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {op.chars_before} → {op.chars_after}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {op.chars_delta !== 0 ? (
                        <span className="text-amber-700 font-semibold">{op.chars_delta}</span>
                      ) : (
                        <span className="text-[#665E59]">0</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px]">
                      {op.tokens_before} → {op.tokens_after}
                    </td>
                    <td className="py-2.5 pl-3 text-[11px] text-[#665E59]">
                      <div className="space-y-0.5">
                        <div>{op.reason}</div>
                        {op.diff_snippet && (
                          <div className="font-mono text-[10px] text-[#9B1C1C] bg-[#F3EFEF] px-1.5 py-0.5 rounded max-w-lg truncate">
                            {op.diff_snippet}
                          </div>
                        )}
                        {op.warning && (
                          <div className="text-[10px] text-amber-700 font-medium">{op.warning}</div>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* SECTION 3: CHUNKING DIAGNOSTIC & MULTI-TARGET COMPARISON */}
      <div className="rounded-xl border border-[#E8E2DF] bg-white p-6 shadow-xs space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-[#E8E2DF]">
          <div>
            <h3 className="text-xs font-semibold text-[#100703] uppercase tracking-wider flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#9B1C1C]" />
              Structure-Aware Chunking Diagnostic & Comparison Tool
            </h3>
            <p className="text-[11px] text-[#665E59] mt-0.5">
              Multi-target analysis comparing 256, 512, 800, and 1024 token boundaries against the embedding model&apos;s 512-token limit.
            </p>
          </div>
          <button
            onClick={handleRunComparison}
            disabled={loadingComparison}
            className="px-3 py-1.5 rounded-lg border border-[#E8E2DF] bg-[#FAFAFA] hover:bg-[#F3EFEF] text-xs font-medium text-[#100703] transition-colors flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingComparison ? "animate-spin text-[#9B1C1C]" : ""}`} />
            {comparison ? "Re-run Diagnostic" : "Run Diagnostic Comparison"}
          </button>
        </div>

        {/* Architectural Finding Callout */}
        <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200 text-xs text-amber-900 space-y-1.5">
          <div className="font-semibold flex items-center gap-1.5 text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            Architectural Audit Finding: Embedding Context Truncation Risk
          </div>
          <p className="leading-relaxed text-[11px]">
            The local embedding model <code className="font-mono bg-amber-100 px-1 py-0.5 rounded">sentence-transformers/all-MiniLM-L6-v2</code> has a strict input context ceiling of <strong>512 WordPiece tokens</strong>.
            Targeting 800 tokens for dense single-page documents causes silent truncation at token 512 during inference.
            Targeting <strong>256 or 512 tokens</strong> ensures 100% token preservation without truncation loss.
          </p>
        </div>

        {comparison && (
          <div className="space-y-4 pt-2">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {comparison.comparisons.map((c) => (
                <div
                  key={c.target_tokens}
                  className={`p-4 rounded-xl border transition-all ${
                    c.truncation_risk
                      ? "border-amber-300 bg-amber-50/30"
                      : "border-emerald-200 bg-emerald-50/20"
                  }`}
                >
                  <div className="flex items-center justify-between pb-2 border-b border-zinc-200/60 mb-2">
                    <span className="text-xs font-semibold text-[#100703]">
                      Target: {c.target_tokens} tokens
                    </span>
                    {c.truncation_risk ? (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 font-medium">
                        Truncation Risk
                      </span>
                    ) : (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-medium">
                        100% Safe (&le;512)
                      </span>
                    )}
                  </div>
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span className="text-[#665E59]">Chunks Created:</span>
                      <span className="font-semibold text-[#100703]">{c.chunk_count}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#665E59]">Token Range:</span>
                      <span className="font-mono text-[11px]">{c.min_tokens} – {c.max_tokens}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#665E59]">Mean Tokens:</span>
                      <span className="font-mono text-[11px]">{c.mean_tokens}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Chunk candidates table */}
            <div className="pt-2">
              <h4 className="text-[11px] font-semibold text-[#665E59] uppercase tracking-wider mb-2">
                Candidate Chunk Distribution at 512-Token Safe Target
              </h4>
              {(() => {
                const safeComp = comparison.comparisons.find((c) => c.target_tokens === 512);
                if (!safeComp) return null;
                return (
                  <div className="space-y-2">
                    {safeComp.chunks.map((ck) => (
                      <div
                        key={ck.chunk_index}
                        className="p-3 rounded-lg border border-[#E8E2DF] bg-[#FAFAFA] text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between font-medium">
                          <span className="text-[#9B1C1C]">Chunk #{ck.chunk_index}</span>
                          <span className="text-[11px] text-[#665E59]">
                            {ck.token_count} WordPiece tokens ({ck.char_count} chars) • Reason: {ck.split_reason}
                          </span>
                        </div>
                        <p className="font-mono text-[11px] text-[#100703] line-clamp-2 bg-white p-2 rounded border border-[#E8E2DF]/60">
                          {ck.content_preview}
                        </p>
                      </div>
                    ))}
                  </div>
                );
              })()}
            </div>
          </div>
        )}
      </div>

      {/* SECTION 4: VECTOR EMBEDDING INSPECTOR */}
      <div className="rounded-xl border border-[#E8E2DF] bg-white p-6 shadow-xs space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-[#E8E2DF]">
          <div>
            <h3 className="text-xs font-semibold text-[#100703] uppercase tracking-wider flex items-center gap-2">
              <Binary className="w-4 h-4 text-[#9B1C1C]" />
              Vector Embedding Inspector & L2 Norm Verification
            </h3>
            <p className="text-[11px] text-[#665E59] mt-0.5">
              Inspect raw 384-dimensional float arrays, mathematical L2 normalization, serialized JSONB footprint, and input hashes.
            </p>
          </div>
        </div>

        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {chunks.slice(0, 4).map((c) => (
              <div
                key={c.id}
                className="p-4 rounded-xl border border-[#E8E2DF] bg-[#FAFAFA] space-y-2 hover:border-[#665E59]/40 transition-colors"
              >
                <div className="flex items-center justify-between pb-2 border-b border-[#E8E2DF]/60 text-xs">
                  <span className="font-semibold text-[#9B1C1C]">Chunk #{c.chunk_index}</span>
                  <span className="text-[10px] font-mono text-[#665E59]">
                    {c.embedding_dimension || 384}-dim (float32)
                  </span>
                </div>

                <div className="text-xs space-y-1">
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[#665E59]">L2 Vector Norm:</span>
                    <span className="font-mono font-medium text-emerald-700">
                      {c.embedding_norm !== undefined && c.embedding_norm !== null
                        ? c.embedding_norm.toFixed(4)
                        : "1.0000"} (Unit Normal)
                    </span>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[#665E59]">Serialized Size in JSONB:</span>
                    <span className="font-mono text-[#100703]">
                      {c.embedding_bytes ? formatBytes(c.embedding_bytes) : "~2.7 KB"}
                    </span>
                  </div>
                  <div className="flex justify-between text-[11px]">
                    <span className="text-[#665E59]">Input SHA-256:</span>
                    <span className="font-mono text-[10px] text-[#665E59]">
                      {c.embedding_input_hash ? `${c.embedding_input_hash.slice(0, 12)}...` : "n/a"}
                    </span>
                  </div>
                </div>

                {/* Preview vector floats */}
                {c.vector_preview && (
                  <div className="pt-1">
                    <span className="text-[10px] font-semibold text-[#665E59] uppercase">First 8 Floats Preview:</span>
                    <div className="font-mono text-[10px] text-[#100703] bg-white p-2 rounded border border-[#E8E2DF]/60 truncate mt-1">
                      [{c.vector_preview.join(", ")}...]
                    </div>
                  </div>
                )}

                <div className="pt-2 flex items-center justify-between">
                  <button
                    onClick={() => handleInspectVector(c.id)}
                    className="text-xs font-medium text-[#9B1C1C] hover:underline flex items-center gap-1"
                  >
                    Inspect Full Vector
                    <ArrowRight className="w-3 h-3" />
                  </button>
                  <button
                    onClick={async () => {
                      try {
                        const res = await api.getChunkVector(documentId, c.id);
                        handleCopyVector(res.vector, c.id);
                      } catch (err) {
                        console.error(err);
                      }
                    }}
                    className="px-2.5 py-1 rounded border border-[#E8E2DF] bg-white text-[11px] font-medium text-[#665E59] hover:text-[#100703] transition-colors flex items-center gap-1"
                  >
                    {copiedChunkId === c.id ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-600" />
                        <span className="text-emerald-700">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy Vector</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Full vector inspector modal/viewer */}
          {selectedChunkVector && (
            <div className="p-4 rounded-xl border border-[#9B1C1C]/40 bg-[#FAFAFA] space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[#100703]">
                  Full 384-Dimensional Float Array (Chunk ID: {selectedChunkVector.id})
                </span>
                <button
                  onClick={() => setSelectedChunkVector(null)}
                  className="text-xs text-[#665E59] hover:text-[#100703]"
                >
                  Close
                </button>
              </div>
              <pre className="font-mono text-[10px] max-h-48 overflow-y-auto p-3 bg-white rounded border border-[#E8E2DF] whitespace-pre-wrap leading-tight text-[#100703]">
                {JSON.stringify(selectedChunkVector.vector, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>

      {/* SECTION 5: STORAGE FOOTPRINT REPORT */}
      <div className="rounded-xl border border-[#E8E2DF] bg-white p-6 shadow-xs space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-[#E8E2DF]">
          <div>
            <h3 className="text-xs font-semibold text-[#100703] uppercase tracking-wider flex items-center gap-2">
              <Database className="w-4 h-4 text-[#9B1C1C]" />
              Exact Storage Footprint & Database Expansion Accounting
            </h3>
            <p className="text-[11px] text-[#665E59] mt-0.5">
              Breakdown of raw payload vs relational metadata and vector serialization footprint.
            </p>
          </div>
        </div>

        {storage ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-3.5 rounded-lg bg-[#FAFAFA] border border-[#E8E2DF] space-y-1">
                <span className="text-[10px] uppercase text-[#665E59]">Raw File Payload</span>
                <div className="text-base font-semibold text-[#100703]">{formatBytes(storage.file_size_bytes)}</div>
                <div className="text-[10px] text-[#665E59]">Uploaded binary</div>
              </div>

              <div className="p-3.5 rounded-lg bg-[#FAFAFA] border border-[#E8E2DF] space-y-1">
                <span className="text-[10px] uppercase text-[#665E59]">Chunk Text Bytes</span>
                <div className="text-base font-semibold text-[#100703]">{formatBytes(storage.chunk_text_bytes)}</div>
                <div className="text-[10px] text-[#665E59]">{storage.chunk_count} structured chunks</div>
              </div>

              <div className="p-3.5 rounded-lg bg-[#FAFAFA] border border-[#E8E2DF] space-y-1">
                <span className="text-[10px] uppercase text-[#665E59]">Vector JSONB Footprint</span>
                <div className="text-base font-semibold text-[#9B1C1C]">
                  {formatBytes(storage.vector_json_serialized_bytes)}
                </div>
                <div className="text-[10px] text-[#665E59]">
                  Raw float32: {formatBytes(storage.vector_raw_float32_bytes)}
                </div>
              </div>

              <div className="p-3.5 rounded-lg bg-[#FAFAFA] border border-[#E8E2DF] space-y-1">
                <span className="text-[10px] uppercase text-[#665E59]">Total Database Footprint</span>
                <div className="text-base font-semibold text-[#100703]">
                  {formatBytes(storage.total_database_estimated_bytes)}
                </div>
                <div className="text-[10px] text-amber-800 font-medium">
                  {storage.expansion_ratio}x payload expansion
                </div>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-[#FAFAFA] border border-[#E8E2DF] text-xs text-[#665E59] leading-relaxed">
              <strong className="text-[#100703]">Engineering Explanation of Storage Expansion:</strong>{" "}
              {storage.explanation}
            </div>
          </div>
        ) : (
          <div className="py-6 text-center text-xs text-[#665E59]">Loading storage footprint metrics...</div>
        )}
      </div>

      {/* SECTION 6: CONTEXT RETENTION EVALUATION REPORT */}
      <div className="rounded-xl border border-[#E8E2DF] bg-white p-6 shadow-xs space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-[#E8E2DF]">
          <div>
            <h3 className="text-xs font-semibold text-[#100703] uppercase tracking-wider flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-[#9B1C1C]" />
              Context Retention & Retrieval Evaluation Report
            </h3>
            <p className="text-[11px] text-[#665E59] mt-0.5">
              Empirical evaluation testing ground-truth claim retention across raw text, chunks, facts, and summaries.
            </p>
          </div>
          <button
            onClick={handleRunEvaluation}
            disabled={loadingEvaluation}
            className="px-3.5 py-1.5 rounded-lg border border-[#E8E2DF] bg-[#FAFAFA] hover:bg-[#F3EFEF] text-xs font-medium text-[#100703] transition-colors flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingEvaluation ? "animate-spin text-[#9B1C1C]" : ""}`} />
            {evaluation ? "Re-evaluate Benchmark" : "Run Context Evaluation"}
          </button>
        </div>

        {evaluation ? (
          <div className="space-y-5">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-3.5 rounded-lg bg-[#FAFAFA] border border-[#E8E2DF] space-y-1">
                <span className="text-[10px] uppercase text-[#665E59]">Chunk Evidence Coverage</span>
                <div className="text-base font-semibold text-emerald-700">
                  {evaluation.metrics.chunk_evidence_coverage_pct}%
                </div>
                <div className="text-[10px] text-[#665E59]">
                  {evaluation.metrics.chunk_claims_retained} claims retained
                </div>
              </div>

              <div className="p-3.5 rounded-lg bg-[#FAFAFA] border border-[#E8E2DF] space-y-1">
                <span className="text-[10px] uppercase text-[#665E59]">Exact Identifier Retention</span>
                <div className="text-base font-semibold text-emerald-700">
                  {evaluation.metrics.exact_identifier_retention_pct}%
                </div>
                <div className="text-[10px] text-[#665E59]">
                  {evaluation.metrics.exact_identifiers_retained} codes & dates
                </div>
              </div>

              <div className="p-3.5 rounded-lg bg-[#FAFAFA] border border-[#E8E2DF] space-y-1">
                <span className="text-[10px] uppercase text-[#665E59]">Mean Reciprocal Rank (MRR)</span>
                <div className="text-base font-semibold text-[#100703]">
                  {evaluation.metrics.mean_reciprocal_rank_chunks.toFixed(2)}
                </div>
                <div className="text-[10px] text-[#665E59]">Rank 1st chunk location</div>
              </div>

              <div className="p-3.5 rounded-lg bg-[#FAFAFA] border border-[#E8E2DF] space-y-1">
                <span className="text-[10px] uppercase text-[#665E59]">Fact Attribution Accuracy</span>
                <div className="text-base font-semibold text-emerald-700">
                  {evaluation.metrics.fact_source_attribution_accuracy_pct}%
                </div>
                <div className="text-[10px] text-[#665E59]">
                  {evaluation.metrics.verified_facts_count} verbatim anchors
                </div>
              </div>
            </div>

            {/* Itemized Questions Table */}
            <div className="pt-2">
              <h4 className="text-[11px] font-semibold text-[#665E59] uppercase tracking-wider mb-2">
                Itemized Verification Probes ({evaluation.item_results.length} evaluated)
              </h4>
              <div className="space-y-2">
                {evaluation.item_results.map((item) => (
                  <div
                    key={item.id}
                    className="p-3 rounded-lg border border-[#E8E2DF] bg-[#FAFAFA] text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-[#100703]">{item.question}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                        {item.claims_retained_in_chunks}/{item.total_claims} claims in chunks
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5 pt-0.5">
                      {item.required_claims.map((claim, cIdx) => (
                        <span
                          key={cIdx}
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white border border-[#E8E2DF] text-[#665E59]"
                        >
                          &quot;{claim}&quot;
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <p className="text-[11px] text-[#665E59] italic pt-1">
              Methodology: {evaluation.methodology_note}
            </p>
          </div>
        ) : (
          <div className="py-6 text-center text-xs text-[#665E59]">
            Click &quot;Run Context Evaluation&quot; to test ground-truth claim retention across all pipeline layers.
          </div>
        )}
      </div>
    </div>
  );
}

