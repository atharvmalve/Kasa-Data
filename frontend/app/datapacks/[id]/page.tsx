"use client";

import { useEffect, useState, useCallback, use } from "react";
import Link from "next/link";
import { ArrowLeft, RefreshCw, FolderGit2, Loader2, AlertCircle } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { UploadZone } from "@/components/UploadZone";
import { DocumentList } from "@/components/DocumentList";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { DataPack, Document } from "@/types";

export default function DataPackDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const [datapack, setDatapack] = useState<DataPack | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async (isSilent = false) => {
    if (!isSilent) setRefreshing(true);
    try {
      const [dpData, docsData] = await Promise.all([
        api.getDataPack(id),
        api.listDocuments(id),
      ]);
      setDatapack(dpData);
      setDocuments(docsData);
      setError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load data pack.";
      setError(msg);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id]);

  useEffect(() => {
    let isMounted = true;
    Promise.all([api.getDataPack(id), api.listDocuments(id)])
      .then(([dpData, docsData]) => {
        if (isMounted) {
          setDatapack(dpData);
          setDocuments(docsData);
          setError(null);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          const msg = err instanceof Error ? err.message : "Failed to load data pack.";
          setError(msg);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [id]);

  // Auto-polling when documents are processing
  useEffect(() => {
    const hasProcessing = documents.some(
      (d) => d.processing_status === "processing" || d.processing_status === "uploaded"
    );
    if (!hasProcessing) return;

    const timer = setInterval(() => {
      loadData(true);
    }, 2500);

    return () => clearInterval(timer);
  }, [documents, loadData]);

  return (
    <div className="flex min-h-screen bg-[#FAFAFA]">
      <Sidebar />

      <main className="flex-1 p-8 max-w-6xl">
        {/* Breadcrumb */}
        <div className="mb-4">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-[#665E59] hover:text-[#9B1C1C] transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Data Packs
          </Link>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20 text-[#665E59]">
            <Loader2 className="w-5 h-5 animate-spin mr-2 text-[#9B1C1C]" />
            <span className="text-xs">Loading data pack...</span>
          </div>
        ) : error || !datapack ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center max-w-md mx-auto mt-8 text-rose-700 text-xs">
            <AlertCircle className="w-6 h-6 mx-auto mb-2 text-rose-600" />
            <p className="font-semibold">{error || "Data pack not found."}</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between pb-5 border-b border-[#E8E2DF]">
              <div>
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-[#F3EFEF] flex items-center justify-center text-[#9B1C1C]">
                    <FolderGit2 className="w-4 h-4" />
                  </div>
                  <h1 className="text-xl font-semibold text-[#100703] tracking-tight">
                    {datapack.name}
                  </h1>
                  {datapack.processing_status && (
                    <StatusBadge status={datapack.processing_status} />
                  )}
                </div>
                {datapack.description && (
                  <p className="text-xs text-[#665E59] mt-1.5 max-w-2xl">
                    {datapack.description}
                  </p>
                )}
              </div>

              <button
                onClick={() => loadData()}
                disabled={refreshing}
                className="px-3 py-1.5 rounded-lg text-xs font-medium border border-[#E8E2DF] bg-white text-[#665E59] hover:text-[#100703] hover:bg-[#FAFAFA] transition-colors flex items-center gap-1.5 disabled:opacity-50 shadow-xs"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin text-[#9B1C1C]" : ""}`} />
                Refresh
              </button>
            </div>

            {/* Upload Zone */}
            <UploadZone
              datapackId={datapack.id}
              onUploadSuccess={() => loadData()}
            />

            {/* Documents Section */}
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-semibold text-[#100703] uppercase tracking-wider">
                  Documents ({documents.length})
                </h2>
              </div>

              <DocumentList
                documents={documents}
                onRefresh={() => loadData()}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
