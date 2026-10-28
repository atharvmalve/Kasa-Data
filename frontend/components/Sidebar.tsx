"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FolderGit2, Layers, Server } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function Sidebar() {
  const pathname = usePathname();
  const [dbStatus, setDbStatus] = useState<string>("checking");

  useEffect(() => {
    let isMounted = true;
    api.getHealth()
      .then((res) => {
        if (isMounted) {
          setDbStatus(res.database.status === "healthy" ? "online" : "degraded");
        }
      })
      .catch(() => {
        if (isMounted) setDbStatus("offline");
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const isDataPacksActive = pathname === "/" || pathname.startsWith("/datapacks") || pathname.startsWith("/documents");

  return (
    <aside className="w-[240px] border-r border-[#E8E2DF] bg-[#FAFAFA] flex flex-col justify-between h-screen shrink-0 sticky top-0 select-none">
      <div>
        {/* Brand / Logo */}
        <div className="h-14 px-5 flex items-center gap-2.5 border-b border-[#E8E2DF]">
          <div className="w-7 h-7 rounded-[7px] bg-[#9B1C1C] flex items-center justify-center text-white shadow-xs">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <span className="font-semibold text-sm tracking-tight text-[#100703]">Kasa</span>
            <span className="text-[10px] ml-1.5 px-1.5 py-0.5 rounded bg-[#F3EFEF] text-[#665E59] font-mono">v0.1</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-3 space-y-1">
          <Link
            href="/"
            className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
              isDataPacksActive
                ? "bg-[#9B1C1C]/10 text-[#9B1C1C] font-semibold"
                : "text-[#665E59] hover:bg-[#F3EFEF] hover:text-[#100703]"
            }`}
          >
            <FolderGit2 className={`w-4 h-4 ${isDataPacksActive ? "text-[#9B1C1C]" : "text-[#665E59]"}`} />
            Data Packs
          </Link>
        </nav>
      </div>

      {/* Footer Status Indicators */}
      <div className="p-3.5 border-t border-[#E8E2DF] text-[11px] text-[#665E59] space-y-2">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Server className="w-3.5 h-3.5" />
            <span>YugabyteDB (YSQL)</span>
          </span>
          <span className="flex items-center gap-1">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                dbStatus === "online" ? "bg-emerald-600" : dbStatus === "checking" ? "bg-amber-500 animate-pulse" : "bg-rose-500"
              }`}
            />
            <span className="text-[10px] capitalize font-mono text-[#100703]">{dbStatus}</span>
          </span>
        </div>
        <div className="pt-1 text-[10px] text-[#665E59] flex items-center justify-between border-t border-[#E8E2DF]/60">
          <span>Port 5433</span>
          <span className="font-mono text-[#9B1C1C] font-medium">Phase 1 Local</span>
        </div>
      </div>
    </aside>
  );
}
