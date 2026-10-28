"use client";

import Link from "next/link";
import { useState } from "react";
import { FileText, RotateCcw, ChevronRight, Trash2, Loader2 } from "lucide-react";
import { Document } from "@/types";
import { StatusBadge } from "./StatusBadge";
import { api } from "@/lib/api";

interface DocumentListProps {
  documents: Document[];
  onRefresh: () => void;
}

export function DocumentList({ documents, onRefresh }: DocumentListProps) {
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  const handleRetry = async (e: React.MouseEvent, docId: string) => {
    e.preventDefault();
    e.stopPropagation();
    setRetryingId(docId);
    try {
      await api.retryProcessing(docId);
      onRefresh();
    } catch (err) {
      console.error("Retry failed:", err);
    } finally {
      setRetryingId(null);
    }
  };

  const handleDelete = async (e: React.MouseEvent, docId: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this document?")) return;
    setDeletingId(docId);
    try {
      await api.deleteDocument(docId);
      onRefresh();
    } catch (err) {
      console.error("Delete failed:", err);
    } finally {
      setDeletingId(null);
    }
  };

  if (documents.length === 0) {
    return (
      <div className="rounded-xl border border-[#E8E2DF] bg-white p-8 text-center">
        <FileText className="w-8 h-8 text-[#665E59]/50 mx-auto mb-2" />
        <p className="text-xs font-medium text-[#100703]">No documents uploaded yet</p>
        <p className="text-[11px] text-[#665E59] mt-0.5">
          Drop files above to parse text, compute hashes and extract knowledge.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-[#E8E2DF] bg-white overflow-hidden shadow-xs">
      <div className="divide-y divide-[#E8E2DF]">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="flex items-center justify-between p-4 hover:bg-[#FAFAFA] transition-colors group"
          >
            <Link
              href={`/documents/${doc.id}`}
              className="flex items-center gap-3 min-w-0 flex-1 mr-4"
            >
              <div className="w-8 h-8 rounded-lg bg-[#F3EFEF] flex items-center justify-center shrink-0 text-[#9B1C1C]">
                <FileText className="w-4 h-4" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-[#100703] truncate hover:text-[#9B1C1C]">
                    {doc.filename}
                  </span>
                  <span className="text-[10px] font-mono text-[#665E59] px-1.5 py-0.2 rounded bg-[#F3EFEF]">
                    v{doc.processing_version}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-[11px] text-[#665E59] mt-0.5">
                  <span>{formatBytes(doc.size_bytes)}</span>
                  <span>•</span>
                  <span>{doc.chunk_count} {doc.chunk_count === 1 ? "chunk" : "chunks"}</span>
                  <span>•</span>
                  <span>{formatDate(doc.updated_at || doc.created_at)}</span>
                </div>
              </div>
            </Link>

            <div className="flex items-center gap-3 shrink-0">
              <StatusBadge status={doc.processing_status} />

              {(doc.processing_status === "failed" || doc.processing_status === "partially_processed") && (
                <button
                  onClick={(e) => handleRetry(e, doc.id)}
                  disabled={retryingId === doc.id}
                  title="Retry ingestion pipeline"
                  className="p-1.5 rounded-lg text-[#665E59] hover:text-[#9B1C1C] hover:bg-[#F3EFEF] transition-colors disabled:opacity-50"
                >
                  {retryingId === doc.id ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-[#9B1C1C]" />
                  ) : (
                    <RotateCcw className="w-3.5 h-3.5" />
                  )}
                </button>
              )}

              <button
                onClick={(e) => handleDelete(e, doc.id)}
                disabled={deletingId === doc.id}
                title="Delete document"
                className="p-1.5 rounded-lg text-[#665E59] hover:text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-50"
              >
                {deletingId === doc.id ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-rose-600" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" />
                )}
              </button>

              <Link
                href={`/documents/${doc.id}`}
                className="p-1.5 rounded-lg text-[#665E59] hover:text-[#100703] hover:bg-[#F3EFEF] transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

