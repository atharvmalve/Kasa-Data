"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Plus, FolderGit2, Calendar, FileText, ChevronRight, Loader2 } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { CreateDataPackModal } from "@/components/CreateDataPackModal";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { DataPack } from "@/types";

export default function DataPacksPage() {
  const [datapacks, setDatapacks] = useState<DataPack[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;
    api.listDataPacks()
      .then((data) => {
        if (isMounted) {
          setDatapacks(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error("Failed to load datapacks:", err);
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="flex min-h-screen bg-[#FAFAFA]">
      <Sidebar />

      <main className="flex-1 p-8 max-w-6xl">
        {/* Header */}
        <div className="flex items-start justify-between mb-8 pb-5 border-b border-[#E8E2DF]">
          <div>
            <h1 className="text-xl font-semibold text-[#100703] tracking-tight">Data Packs</h1>
            <p className="text-xs text-[#665E59] mt-1">
              Your documents, structured into reliable context.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-[#9B1C1C] text-white hover:bg-[#7E1717] transition-colors flex items-center gap-1.5 shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            Create data pack
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-20 text-[#665E59]">
            <Loader2 className="w-5 h-5 animate-spin mr-2 text-[#9B1C1C]" />
            <span className="text-xs">Loading data packs...</span>
          </div>
        ) : datapacks.length === 0 ? (
          /* Empty State */
          <div className="rounded-xl border border-[#E8E2DF] bg-white p-12 text-center max-w-lg mx-auto mt-8">
            <div className="w-12 h-12 rounded-xl bg-[#F3EFEF] flex items-center justify-center text-[#9B1C1C] mx-auto mb-3">
              <FolderGit2 className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-semibold text-[#100703]">No data packs yet</h3>
            <p className="text-xs text-[#665E59] mt-1 mb-5">
              Create your first data pack to begin ingesting and enriching source documents.
            </p>
            <button
              onClick={() => setIsModalOpen(true)}
              className="px-4 py-2 rounded-lg text-xs font-medium bg-[#9B1C1C] text-white hover:bg-[#7E1717] transition-colors inline-flex items-center gap-1.5 shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              Create data pack
            </button>
          </div>
        ) : (
          /* Data Packs List */
          <div className="rounded-xl border border-[#E8E2DF] bg-white overflow-hidden shadow-xs">
            <div className="divide-y divide-[#E8E2DF]">
              {datapacks.map((dp) => (
                <Link
                  key={dp.id}
                  href={`/datapacks/${dp.id}`}
                  className="flex items-center justify-between p-4 hover:bg-[#FAFAFA] transition-colors group"
                >
                  <div className="flex items-start gap-3.5 min-w-0 flex-1 mr-4">
                    <div className="w-8 h-8 rounded-lg bg-[#F3EFEF] flex items-center justify-center shrink-0 text-[#9B1C1C] mt-0.5">
                      <FolderGit2 className="w-4 h-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-[#100703] group-hover:text-[#9B1C1C] transition-colors">
                          {dp.name}
                        </span>
                        {dp.processing_status && (
                          <StatusBadge status={dp.processing_status} />
                        )}
                      </div>
                      {dp.description && (
                        <p className="text-xs text-[#665E59] line-clamp-1 mt-0.5">
                          {dp.description}
                        </p>
                      )}
                      <div className="flex items-center gap-3 text-[11px] text-[#665E59] mt-1.5">
                        <span className="flex items-center gap-1">
                          <FileText className="w-3 h-3" />
                          {dp.file_count} {dp.file_count === 1 ? "document" : "documents"}
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          Updated {formatDate(dp.updated_at || dp.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 text-[#665E59] group-hover:text-[#100703] transition-colors shrink-0">
                    <span className="text-xs font-medium">Open</span>
                    <ChevronRight className="w-4 h-4" />
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Modal */}
        <CreateDataPackModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onSuccess={(newPack) => {
            setDatapacks((prev) => [newPack, ...prev]);
          }}
        />
      </main>
    </div>
  );
}
