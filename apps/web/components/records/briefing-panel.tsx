"use client"

import { useQuery } from "@tanstack/react-query"
import { motion } from "framer-motion"
import { RefreshCw, Shirt, Sparkles, Wind } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState, ErrorState } from "@/components/ui-states"
import { api } from "@/lib/api"

function BriefingCard({
  icon,
  title,
  body,
  delay,
}: {
  icon: React.ReactNode
  title: string
  body: string
  delay: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      className="glass rounded-2xl p-5"
    >
      <div className="flex items-center gap-2 text-white">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/10 text-white/80">{icon}</span>
        <h3 className="font-medium">{title}</h3>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-white/80">{body}</p>
    </motion.div>
  )
}

export function BriefingPanel({ recordId }: { recordId: string }) {
  const query = useQuery({
    queryKey: ["briefing", recordId],
    queryFn: () => api.briefing(recordId),
    enabled: false, // generated on demand (LLM call)
    staleTime: 5 * 60_000,
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">AI briefing</h2>
          <p className="text-sm text-white/65">A natural-language summary generated from the readings.</p>
        </div>
        <Button
          onClick={() => query.refetch()}
          disabled={query.isFetching}
          className="bg-white text-slate-900 hover:bg-white/90"
        >
          {query.isFetching ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin" /> Generating
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" /> {query.data ? "Refresh briefing" : "Generate briefing"}
            </>
          )}
        </Button>
      </div>

      {query.isFetching ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-36 w-full rounded-2xl bg-white/10" />
          ))}
        </div>
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => query.refetch()} />
      ) : query.data ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <BriefingCard
            icon={<Sparkles className="h-4 w-4" />}
            title="Summary"
            body={query.data.summary}
            delay={0}
          />
          <BriefingCard
            icon={<Shirt className="h-4 w-4" />}
            title="What to wear"
            body={query.data.clothing_suggestion}
            delay={0.05}
          />
          <BriefingCard
            icon={<Wind className="h-4 w-4" />}
            title="Air quality"
            body={query.data.aqi_note}
            delay={0.1}
          />
        </div>
      ) : (
        <EmptyState
          icon={Sparkles}
          title="No briefing yet"
          description="Generate an AI briefing to get a summary, clothing tips, and an air-quality note for this record."
        />
      )}
    </div>
  )
}
