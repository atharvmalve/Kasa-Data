"use client";

import { useState } from "react";
import { X, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { DataPack } from "@/types";

interface CreateDataPackModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (dataPack: DataPack) => void;
}

export function CreateDataPackModal({ isOpen, onClose, onSuccess }: CreateDataPackModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Data pack name is required.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const newPack = await api.createDataPack({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      setName("");
      setDescription("");
      onSuccess(newPack);
      onClose();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to create data pack.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/30 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-xl border border-[#E8E2DF] shadow-lg w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="px-5 py-4 border-b border-[#E8E2DF] flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-[#100703]">Create Data Pack</h2>
            <p className="text-xs text-[#665E59]">Container for documents and extracted context.</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-[#665E59] hover:bg-[#F3EFEF] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">
              {error}
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[#100703]">
              Name <span className="text-[#9B1C1C]">*</span>
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Q3 Technical Architecture"
              className="w-full px-3 py-2 text-xs rounded-lg border border-[#E8E2DF] focus:outline-none focus:ring-1 focus:ring-[#9B1C1C] focus:border-[#9B1C1C] bg-[#FAFAFA]"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[#100703]">Description</label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional summary of included source documents..."
              className="w-full px-3 py-2 text-xs rounded-lg border border-[#E8E2DF] focus:outline-none focus:ring-1 focus:ring-[#9B1C1C] focus:border-[#9B1C1C] bg-[#FAFAFA] resize-none"
            />
          </div>

          <div className="pt-2 flex items-center justify-end gap-2 border-t border-[#E8E2DF]">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-[#665E59] hover:bg-[#F3EFEF] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-1.5 rounded-lg text-xs font-medium bg-[#9B1C1C] text-white hover:bg-[#7E1717] transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
