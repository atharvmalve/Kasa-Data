import { CheckCircle2, Clock, AlertTriangle, XCircle, Loader2 } from "lucide-react";

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className = "" }: StatusBadgeProps) {
  switch (status) {
    case "processed":
    case "completed":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 ${className}`}
        >
          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
          Processed
        </span>
      );
    case "processing":
    case "started":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-amber-50 text-amber-800 border border-amber-200 ${className}`}
        >
          <Loader2 className="w-3 h-3 text-amber-600 animate-spin" />
          Processing
        </span>
      );
    case "partially_processed":
    case "partially_completed":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-yellow-50 text-yellow-800 border border-yellow-200 ${className}`}
        >
          <AlertTriangle className="w-3 h-3 text-yellow-600" />
          Partial
        </span>
      );
    case "failed":
    case "has_failures":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-rose-50 text-rose-700 border border-rose-200 ${className}`}
        >
          <XCircle className="w-3 h-3 text-rose-600" />
          Failed
        </span>
      );
    case "skipped":
    case "not_configured":
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-stone-100 text-[#665E59] border border-[#E8E2DF] ${className}`}
        >
          Skipped
        </span>
      );
    case "uploaded":
    case "pending":
    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-medium bg-stone-50 text-[#665E59] border border-[#E8E2DF] ${className}`}
        >
          <Clock className="w-3 h-3 text-[#665E59]" />
          {status.replace(/_/g, " ")}
        </span>
      );
  }
}

