"use client";

import { useState, useRef } from "react";
import { UploadCloud, Loader2, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";

interface UploadZoneProps {
  datapackId: string;
  onUploadSuccess: () => void;
}

export function UploadZone({ datapackId, onUploadSuccess }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const allowedExtensions = [".pdf", ".md", ".txt"];

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    setError(null);
    setUploading(true);

    const validFiles: File[] = [];
    const invalidFiles: string[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const ext = `.${file.name.split(".").pop()?.toLowerCase()}`;
      if (allowedExtensions.includes(ext)) {
        validFiles.push(file);
      } else {
        invalidFiles.push(file.name);
      }
    }

    if (invalidFiles.length > 0) {
      setError(`Unsupported files skipped: ${invalidFiles.join(", ")}. Allowed: .pdf, .md, .txt`);
    }

    if (validFiles.length === 0) {
      setUploading(false);
      return;
    }

    try {
      for (const file of validFiles) {
        await api.uploadDocument(datapackId, file);
      }
      onUploadSuccess();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An error occurred during file upload.";
      setError(msg);
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !uploading && fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
          isDragging
            ? "border-[#9B1C1C] bg-[#9B1C1C]/5"
            : "border-[#E8E2DF] hover:border-[#665E59]/40 bg-white"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.md,.txt"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
          disabled={uploading}
        />

        <div className="flex flex-col items-center justify-center space-y-2">
          <div className="w-10 h-10 rounded-full bg-[#F3EFEF] flex items-center justify-center text-[#9B1C1C]">
            {uploading ? (
              <Loader2 className="w-5 h-5 animate-spin text-[#9B1C1C]" />
            ) : (
              <UploadCloud className="w-5 h-5" />
            )}
          </div>
          <div>
            <p className="text-xs font-medium text-[#100703]">
              {uploading ? "Ingesting and chunking documents..." : "Click or drag documents to upload"}
            </p>
            <p className="text-[11px] text-[#665E59] mt-0.5">
              Supports <span className="font-mono text-[#100703]">.pdf</span>,{" "}
              <span className="font-mono text-[#100703]">.md</span>,{" "}
              <span className="font-mono text-[#100703]">.txt</span> up to 20MB
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
