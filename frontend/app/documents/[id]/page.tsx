"use client";

import { useEffect, useState, useCallback, use } from "react";
import Link from "next/link";
import {
  ArrowLeft, RotateCcw, FileText, Layers,
  Sparkles, History, AlignLeft, ShieldCheck, Loader2, ChevronLeft, ChevronRight, Scale, Copy, Check
} from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { StatusBadge } from "@/components/StatusBadge";
import { ContextAuditTab } from "@/components/ContextAuditTab";
import { api } from "@/lib/api";
import {
  Document, DocumentContent, DocumentChunk, DocumentSummary,
  ExtractedFact, ProcessingEvent, PaginatedResponse
} from "@/types";

export default function DocumentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const [document, setDocument] = useState<Document | null>(null);
  const [content, setContent] = useState<DocumentContent | null>(null);
  const [chunksPage, setChunksPage] = useState<PaginatedResponse<DocumentChunk>>({
    items: [],
    total: 0,
    page: 1,
    page_size: 15,
    total_pages: 0,
  });
  const [summaries, setSummaries] = useState<DocumentSummary[]>([]);
  const [facts, setFacts] = useState<ExtractedFact[]>([]);
  const [eventsPage, setEventsPage] = useState<PaginatedResponse<ProcessingEvent>>({
    items: [],
    total: 0,
    page: 1,
    page_size: 50,
    total_pages: 0,
  });

  const [activeTab, setActiveTab] = useState<"overview" | "content" | "chunks" | "knowledge" | "events" | "audit">("overview");
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chunkPageNumber, setChunkPageNumber] = useState(1);
  const [copiedChunkId, setCopiedChunkId] = useState<string | null>(null);

  const loadDocumentData = useCallback(async () => {
    try {
      const [docData, contentData, chunksData, summariesData, factsData, eventsData] =
        await Promise.all([
          api.getDocument(id),
          api.getDocumentContent(id),
          api.getDocumentChunks(id, chunkPageNumber, 15),
          api.getDocumentSummaries(id),
          api.getDocumentFacts(id),
          api.getDocumentEvents(id, 1, 50),
        ]);

      setDocument(docData);
      setContent(contentData);
      setChunksPage(chunksData);
      setSummaries(summariesData);
      setFacts(factsData);
      setEventsPage(eventsData);
      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load document.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [id, chunkPageNumber]);

  useEffect(() => {
    let isMounted = true;
    Promise.all([
      api.getDocument(id),
      api.getDocumentContent(id),
      api.getDocumentChunks(id, chunkPageNumber, 15),
      api.getDocumentSummaries(id),
      api.getDocumentFacts(id),
      api.getDocumentEvents(id, 1, 50),
    ])
      .then(([docData, contentData, chunksData, summariesData, factsData, eventsData]) => {
        if (isMounted) {
          setDocument(docData);
          setContent(contentData);
          setChunksPage(chunksData);
          setSummaries(summariesData);
          setFacts(factsData);
          setEventsPage(eventsData);
          setError(null);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : "Failed to load document.";
          setError(msg);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [id, chunkPageNumber]);

  // Polling if processing
  useEffect(() => {
    if (!document || (document.processing_status !== "processing" && document.processing_status !== "uploaded")) {
      return;
    }
    const timer = setInterval(() => {
      loadDocumentData();
    }, 2500);
    return () => clearInterval(timer);
  }, [document, loadDocumentData]);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await api.retryProcessing(id);
      await loadDocumentData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Retry failed.";
      alert(`Retry failed: ${msg}`);
    } finally {
      setRetrying(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "N/A";
    try {
      return new Date(dateStr).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen bg-[#FAFAFA]">
        <Sidebar />
        <main className="flex-1 p-8 flex items-center justify-center text-[#665E59]">
          <Loader2 className="w-5 h-5 animate-spin mr-2 text-[#9B1C1C]" />
          <span className="text-xs">Loading document inspection view...</span>
        </main>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="flex min-h-screen bg-[#FAFAFA]">
        <Sidebar />
        <main className="flex-1 p-8">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-[#665E59] hover:text-[#9B1C1C] transition-colors mb-4"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back
          </Link>
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center text-rose-700 text-xs">
            {error || "Document not found."}
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-[#FAFAFA]">
      <Sidebar />

      <main className="flex-1 p-8 max-w-6xl">
        {/* Breadcrumb */}
        <div className="mb-4">
          <Link
            href={`/datapacks/${document.datapack_id}`}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-[#665E59] hover:text-[#9B1C1C] transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Data Pack
          </Link>
        </div>

        {/* Header */}
        <div className="flex items-start justify-between pb-5 border-b border-[#E8E2DF] mb-6">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#F3EFEF] flex items-center justify-center text-[#9B1C1C]">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-semibold text-[#100703] tracking-tight">
                  {document.filename}
                </h1>
                <StatusBadge status={document.processing_status} />
                <span className="text-[10px] font-mono text-[#665E59] px-2 py-0.5 rounded bg-[#F3EFEF]">
                  v{document.processing_version}
                </span>
              </div>
              <p className="text-[11px] text-[#665E59] mt-0.5">
                {document.file_extension.toUpperCase()} • {formatBytes(document.size_bytes)} • Uploaded {formatDate(document.created_at)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium border border-[#E8E2DF] bg-white text-[#665E59] hover:text-[#100703] hover:bg-[#FAFAFA] transition-colors flex items-center gap-1.5 disabled:opacity-50 shadow-xs"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${retrying ? "animate-spin text-[#9B1C1C]" : ""}`} />
              Retry processing
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-1 border-b border-[#E8E2DF] mb-6">
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-3.5 py-2 text-xs font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === "overview"
                ? "border-[#9B1C1C] text-[#9B1C1C] font-semibold"
                : "border-transparent text-[#665E59] hover:text-[#100703]"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            Overview
          </button>
          <button
            onClick={() => setActiveTab("content")}
            className={`px-3.5 py-2 text-xs font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === "content"
                ? "border-[#9B1C1C] text-[#9B1C1C] font-semibold"
                : "border-transparent text-[#665E59] hover:text-[#100703]"
            }`}
          >
            <AlignLeft className="w-3.5 h-3.5" />
            Original Text
          </button>
          <button
            onClick={() => setActiveTab("chunks")}
            className={`px-3.5 py-2 text-xs font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === "chunks"
                ? "border-[#9B1C1C] text-[#9B1C1C] font-semibold"
                : "border-transparent text-[#665E59] hover:text-[#100703]"
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Chunks ({chunksPage.total})
          </button>
          <button
            onClick={() => setActiveTab("knowledge")}
            className={`px-3.5 py-2 text-xs font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === "knowledge"
                ? "border-[#9B1C1C] text-[#9B1C1C] font-semibold"
                : "border-transparent text-[#665E59] hover:text-[#100703]"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            Extracted Knowledge ({facts.length})
          </button>
          <button
            onClick={() => setActiveTab("events")}
            className={`px-3.5 py-2 text-xs font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === "events"
                ? "border-[#9B1C1C] text-[#9B1C1C] font-semibold"
                : "border-transparent text-[#665E59] hover:text-[#100703]"
            }`}
          >
            <History className="w-3.5 h-3.5" />
            Processing Details ({eventsPage.total})
          </button>
          <button
            onClick={() => setActiveTab("audit")}
            className={`px-3.5 py-2 text-xs font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === "audit"
                ? "border-[#9B1C1C] text-[#9B1C1C] font-semibold"
                : "border-transparent text-[#665E59] hover:text-[#100703]"
            }`}
          >
            <Scale className="w-3.5 h-3.5" />
            Context Audit
          </button>
        </div>

        {/* TAB 1: OVERVIEW */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            {document.last_error && (
              <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800">
                <span className="font-semibold block mb-1">Processing Error:</span>
                <p className="font-mono text-[11px] whitespace-pre-wrap">{document.last_error}</p>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Identity & Checksums */}
              <div className="rounded-xl border border-[#E8E2DF] bg-white p-5 space-y-3 shadow-xs">
                <h3 className="text-xs font-semibold text-[#100703] uppercase tracking-wider">
                  Document Identity & Evidence
                </h3>
                <div className="space-y-2 text-xs divide-y divide-[#E8E2DF]/60">
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#665E59]">Filename</span>
                    <span className="font-medium text-[#100703]">{document.filename}</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#665E59]">File Size</span>
                    <span className="font-medium text-[#100703]">{formatBytes(document.size_bytes)} ({document.size_bytes.toLocaleString()} bytes)</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#665E59]">MIME Type</span>
                    <span className="font-mono text-[11px] text-[#100703]">{document.mime_type}</span>
                  </div>
                  <div className="py-1.5">
                    <span className="text-[#665E59] block mb-1">SHA-256 Checksum</span>
                    <span className="font-mono text-[11px] text-[#100703] break-all bg-[#FAFAFA] p-1.5 rounded border border-[#E8E2DF] block">
                      {document.sha256_checksum}
                    </span>
                  </div>
                  <div className="py-1.5">
                    <span className="text-[#665E59] block mb-1">MD5 Checksum</span>
                    <span className="font-mono text-[11px] text-[#100703] bg-[#FAFAFA] p-1.5 rounded border border-[#E8E2DF] block">
                      {document.md5_checksum}
                    </span>
                  </div>
                </div>
              </div>

              {/* Pipeline & Embedding Status */}
              <div className="rounded-xl border border-[#E8E2DF] bg-white p-5 space-y-3 shadow-xs">
                <h3 className="text-xs font-semibold text-[#100703] uppercase tracking-wider">
                  Pipeline & Model Metadata
                </h3>
                <div className="space-y-2 text-xs divide-y divide-[#E8E2DF]/60">
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#665E59]">Processing Status</span>
                    <StatusBadge status={document.processing_status} />
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#665E59]">Processing Version</span>
                    <span className="font-mono text-[#100703]">v{document.processing_version}</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#665E59]">Generated Chunks</span>
                    <span className="font-medium text-[#100703]">{document.chunk_count}</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#665E59]">Local Embedding Model</span>
                    <span className="font-mono text-[11px] text-[#100703]">{document.embedding_model || "sentence-transformers/all-MiniLM-L6-v2"}</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#665E59]">Embedding Dimension</span>
                    <span className="font-mono text-[#100703]">{document.embedding_dimension || 384}</span>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#665E59]">Embedding Status</span>
                    <StatusBadge status={document.embedding_status} />
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#665E59]">Summary Enrichment</span>
                    <StatusBadge status={document.summary_status} />
                  </div>
                  <div className="flex justify-between py-1.5">
                    <span className="text-[#665E59]">Last Processed</span>
                    <span className="text-[#100703]">{formatDate(document.processed_at)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: ORIGINAL TEXT */}
        {activeTab === "content" && (
          <div className="rounded-xl border border-[#E8E2DF] bg-white p-6 shadow-xs">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-[#E8E2DF]">
              <h3 className="text-xs font-semibold text-[#100703] uppercase tracking-wider">
                Preserved Original Extracted Text
              </h3>
              <span className="text-[11px] text-[#665E59]">
                {content?.raw_text?.length || 0} characters
              </span>
            </div>
            {content?.raw_text ? (
              <pre className="font-mono text-xs text-[#100703] whitespace-pre-wrap leading-relaxed max-h-[600px] overflow-y-auto p-4 bg-[#FAFAFA] rounded-lg border border-[#E8E2DF]">
                {content.raw_text}
              </pre>
            ) : (
              <p className="text-xs text-[#665E59]">No text extracted.</p>
            )}
          </div>
        )}

        {/* TAB 3: CHUNKS */}
        {activeTab === "chunks" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-[#665E59]">
                Showing page {chunksPage.page} of {Math.max(1, chunksPage.total_pages)} ({chunksPage.total} total chunks)
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  disabled={chunkPageNumber <= 1}
                  onClick={() => setChunkPageNumber((p) => Math.max(1, p - 1))}
                  className="p-1.5 rounded border border-[#E8E2DF] bg-white text-[#665E59] disabled:opacity-40"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                </button>
                <button
                  disabled={chunkPageNumber >= chunksPage.total_pages}
                  onClick={() => setChunkPageNumber((p) => p + 1)}
                  className="p-1.5 rounded border border-[#E8E2DF] bg-white text-[#665E59] disabled:opacity-40"
                >
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            <div className="space-y-3">
              {chunksPage.items.map((chunk) => {
                const pageNumber = typeof chunk.source_location === "object" && chunk.source_location !== null && "page" in chunk.source_location
                  ? String(chunk.source_location.page)
                  : null;

                return (
                  <div
                    key={chunk.id}
                    id={`chunk-${chunk.id}`}
                    className="rounded-xl border border-[#E8E2DF] bg-white p-4 shadow-xs space-y-2 hover:border-[#665E59]/40 transition-colors"
                  >
                    <div className="flex items-center justify-between text-xs pb-2 border-b border-[#E8E2DF]/60">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-[#9B1C1C]">Chunk #{chunk.chunk_index}</span>
                        {chunk.token_count && (
                          <span className="text-[11px] text-[#665E59]">{chunk.token_count} WordPiece tokens</span>
                        )}
                        {chunk.split_reason && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-100 font-mono text-zinc-700">
                            {chunk.split_reason}
                          </span>
                        )}
                        {chunk.heading_path && chunk.heading_path.length > 0 && (
                          <span className="text-[11px] px-1.5 py-0.5 rounded bg-[#F3EFEF] text-[#665E59]">
                            {chunk.heading_path.join(" > ")}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={chunk.embedding_status} />
                        <span className="font-mono text-[10px] text-[#665E59]" title={`Content Hash: ${chunk.content_hash}`}>
                          hash:{chunk.content_hash.slice(0, 8)}...
                        </span>
                      </div>
                    </div>

                    <p className="font-mono text-xs text-[#100703] whitespace-pre-wrap leading-relaxed bg-[#FAFAFA] p-3 rounded-lg border border-[#E8E2DF]/60">
                      {chunk.content}
                    </p>

                    <div className="text-[10px] text-[#665E59] flex items-center justify-between pt-1">
                      <span>
                        Offsets: char {chunk.character_start ?? 0}–{chunk.character_end ?? 0}
                        {pageNumber && ` • Page ${pageNumber}`}
                        {chunk.embedding_norm !== undefined && chunk.embedding_norm !== null && (
                          <> • Norm: {chunk.embedding_norm.toFixed(4)}</>
                        )}
                        {chunk.embedding_bytes && (
                          <> • JSONB: {formatBytes(chunk.embedding_bytes)}</>
                        )}
                      </span>
                      <div className="flex items-center gap-3">
                        <button
                          onClick={async () => {
                            try {
                              const res = await api.getChunkVector(document.id, chunk.id);
                              await navigator.clipboard.writeText(JSON.stringify(res.vector));
                              setCopiedChunkId(chunk.id);
                              setTimeout(() => setCopiedChunkId(null), 2000);
                            } catch (err) {
                              console.error(err);
                            }
                          }}
                          className="text-[#9B1C1C] hover:underline flex items-center gap-1 font-sans"
                        >
                          {copiedChunkId === chunk.id ? (
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
                        <span className="font-mono">ID: {chunk.id}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* TAB 4: EXTRACTED KNOWLEDGE */}
        {activeTab === "knowledge" && (
          <div className="space-y-6">
            {/* Summaries */}
            <div className="rounded-xl border border-[#E8E2DF] bg-white p-5 shadow-xs space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-[#E8E2DF]">
                <h3 className="text-xs font-semibold text-[#100703] uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-[#9B1C1C]" />
                  Document Summary
                </h3>
                <StatusBadge status={document.summary_status} />
              </div>

              {summaries.length > 0 ? (
                <div className="space-y-3">
                  {summaries.map((s) => (
                    <div key={s.id} className="text-xs leading-relaxed text-[#100703] whitespace-pre-wrap bg-[#FAFAFA] p-4 rounded-lg border border-[#E8E2DF]">
                      {s.content}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-[#665E59] py-3 text-center">
                  {document.summary_status === "not_configured"
                    ? "Groq enrichment is not configured (GROQ_API_KEY absent). Set GROQ_API_KEY to enable LLM summaries."
                    : "No summary generated for this document."}
                </div>
              )}
            </div>

            {/* Structured Facts */}
            <div className="rounded-xl border border-[#E8E2DF] bg-white p-5 shadow-xs space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-[#E8E2DF]">
                <h3 className="text-xs font-semibold text-[#100703] uppercase tracking-wider">
                  Extracted Structured Facts ({facts.length})
                </h3>
              </div>

              {facts.length > 0 ? (
                <div className="divide-y divide-[#E8E2DF]">
                  {facts.map((fact) => (
                    <div key={fact.id} className="py-3 space-y-1.5">
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded font-medium text-[10px] bg-[#9B1C1C]/10 text-[#9B1C1C] uppercase tracking-wider">
                            {fact.fact_type}
                          </span>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-100 text-[#665E59]">
                            {fact.extraction_method}
                          </span>
                          {fact.validation_status === "flagged" ? (
                            <span className="px-1.5 py-0.5 rounded font-medium text-[10px] bg-amber-50 text-amber-700 border border-amber-200">
                              Flagged ({fact.validation_reason || "quality_check"})
                            </span>
                          ) : fact.validation_status === "accepted" ? (
                            <span className="px-1.5 py-0.5 rounded font-medium text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Verified Provenance
                            </span>
                          ) : null}
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => {
                              setActiveTab("chunks");
                            }}
                            className="text-[11px] text-[#9B1C1C] hover:underline flex items-center gap-1"
                          >
                            Trace to Chunk
                          </button>
                        </div>
                      </div>

                      <p className="text-xs text-[#100703] font-medium leading-relaxed">
                        {fact.statement}
                      </p>

                      {fact.exact_source_text && (
                        <div className="text-[11px] font-mono text-[#100703] bg-emerald-50/70 border border-emerald-200 p-2.5 rounded">
                          <span className="text-[10px] font-sans font-semibold uppercase text-emerald-800 block mb-0.5">
                            Verbatim Source Evidence:
                          </span>
                          &quot;{fact.exact_source_text}&quot;
                          {fact.source_char_start !== null && fact.source_char_end !== null && (
                            <span className="text-[10px] text-emerald-700 font-sans ml-2">
                              (chars {fact.source_char_start}–{fact.source_char_end})
                            </span>
                          )}
                        </div>
                      )}

                      {(fact.subject || fact.predicate || fact.object_value) && (
                        <div className="text-[11px] font-mono text-[#665E59] flex items-center gap-3 bg-[#FAFAFA] p-2 rounded border border-[#E8E2DF]/60">
                          {fact.subject && <span>Subject: <strong className="text-[#100703]">{fact.subject}</strong></span>}
                          {fact.predicate && <span>Predicate: <strong className="text-[#100703]">{fact.predicate}</strong></span>}
                          {fact.object_value && <span>Object: <strong className="text-[#100703]">{fact.object_value}</strong></span>}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-[#665E59] py-3 text-center">
                  No structured facts extracted.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 5: PROCESSING DETAILS */}
        {activeTab === "events" && (
          <div className="rounded-xl border border-[#E8E2DF] bg-white p-5 shadow-xs space-y-4">
            <h3 className="text-xs font-semibold text-[#100703] uppercase tracking-wider pb-2 border-b border-[#E8E2DF]">
              Chronological Pipeline Events ({eventsPage.total})
            </h3>

            <div className="space-y-3">
              {eventsPage.items.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start justify-between p-3 rounded-lg border border-[#E8E2DF] bg-[#FAFAFA] text-xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-[#100703] capitalize">
                        {event.stage.replace(/_/g, " ")}
                      </span>
                      <StatusBadge status={event.status} />
                      <span className="text-[10px] font-mono text-[#665E59]">
                        v{event.processing_version}
                      </span>
                    </div>
                    <p className="text-[#665E59]">{event.message}</p>
                  </div>

                  <div className="text-right text-[11px] text-[#665E59] shrink-0 ml-4">
                    {event.duration_ms !== null && (
                      <span className="font-mono text-[#100703] block font-medium">
                        {event.duration_ms} ms
                      </span>
                    )}
                    <span>{formatDate(event.created_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 6: CONTEXT AUDIT */}
        {activeTab === "audit" && (
          <ContextAuditTab documentId={id} chunks={chunksPage.items} />
        )}
      </main>
    </div>
  );
}
