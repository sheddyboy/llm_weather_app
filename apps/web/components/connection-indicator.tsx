"use client"

import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"

export function ConnectionIndicator() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 30_000,
    retry: false,
  })

  const status: "connecting" | "online" | "offline" = isLoading
    ? "connecting"
    : isError || data?.status !== "ok"
      ? "offline"
      : "online"

  const meta = {
    connecting: { label: "Connecting", dot: "bg-amber-400" },
    online: { label: "Live", dot: "bg-emerald-400" },
    offline: { label: "Offline", dot: "bg-red-400" },
  }[status]

  return (
    <div
      className="glass hidden items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium text-white/80 sm:inline-flex"
      title={status === "offline" ? "Backend unreachable. Check NEXT_PUBLIC_API_BASE_URL and CORS." : undefined}
    >
      <span className="relative flex h-2 w-2">
        {status === "online" && (
          <span className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-60", meta.dot)} />
        )}
        <span className={cn("relative inline-flex h-2 w-2 rounded-full", meta.dot)} />
      </span>
      {meta.label}
    </div>
  )
}
