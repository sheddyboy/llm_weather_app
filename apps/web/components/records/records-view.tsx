"use client"

import { useQuery } from "@tanstack/react-query"
import { AnimatePresence } from "framer-motion"
import { CalendarPlus, Inbox, Plus, Search, X } from "lucide-react"
import { useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { SkyBackground } from "@/components/sky-background"
import { SaveRecordDialog } from "@/components/save-record-dialog"
import { DeleteRecordDialog } from "@/components/delete-record-dialog"
import { RecordCard } from "@/components/records/record-card"
import { EmptyState, ErrorState } from "@/components/ui-states"
import { api } from "@/lib/api"
import type { WeatherRecordRead } from "@/lib/types"

const dateInputClass =
  "w-full rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-sm text-white outline-none [color-scheme:dark] focus-visible:ring-2 focus-visible:ring-white/60"

export function RecordsView() {
  const [locationFilter, setLocationFilter] = useState("")
  const [startFilter, setStartFilter] = useState("")
  const [endFilter, setEndFilter] = useState("")
  const [createOpen, setCreateOpen] = useState(false)
  const [toDelete, setToDelete] = useState<WeatherRecordRead | null>(null)

  const query = useQuery({
    queryKey: ["records", { start_date: startFilter, end_date: endFilter }],
    queryFn: () =>
      api.listRecords({
        start_date: startFilter || undefined,
        end_date: endFilter || undefined,
      }),
  })

  // Location filtering is client-side (the API filters by location_id only).
  const filtered = useMemo(() => {
    const records = query.data ?? []
    const term = locationFilter.trim().toLowerCase()
    if (!term) return records
    return records.filter(
      (r) =>
        r.location.resolved_name.toLowerCase().includes(term) ||
        r.location.query_text.toLowerCase().includes(term) ||
        (r.location.country ?? "").toLowerCase().includes(term),
    )
  }, [query.data, locationFilter])

  const hasFilters = Boolean(locationFilter || startFilter || endFilter)

  function clearFilters() {
    setLocationFilter("")
    setStartFilter("")
    setEndFilter("")
  }

  return (
    <>
      <SkyBackground conditions="clear" />

      <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">Saved records</h1>
            <p className="mt-2 text-white/75">Your stored weather snapshots, newest first.</p>
          </div>
          <Button onClick={() => setCreateOpen(true)} className="bg-white text-slate-900 hover:bg-white/90">
            <Plus className="h-4 w-4" /> New record
          </Button>
        </div>

        {/* Filters */}
        <div className="glass mt-6 grid grid-cols-1 gap-4 rounded-2xl p-4 sm:grid-cols-4">
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="filter-location" className="text-white/80">
              Location
            </Label>
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/60"
                aria-hidden="true"
              />
              <Input
                id="filter-location"
                value={locationFilter}
                onChange={(e) => setLocationFilter(e.target.value)}
                placeholder="Filter by location"
                className="border-white/20 bg-white/10 pl-9 text-white placeholder:text-white/50 focus-visible:ring-white/60"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="filter-start" className="text-white/80">
              From
            </Label>
            <input
              id="filter-start"
              type="date"
              value={startFilter}
              onChange={(e) => setStartFilter(e.target.value)}
              className={dateInputClass}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="filter-end" className="text-white/80">
              To
            </Label>
            <input
              id="filter-end"
              type="date"
              value={endFilter}
              onChange={(e) => setEndFilter(e.target.value)}
              className={dateInputClass}
            />
          </div>
          {hasFilters && (
            <div className="sm:col-span-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="text-white/70 hover:bg-white/10 hover:text-white"
              >
                <X className="h-4 w-4" /> Clear filters
              </Button>
            </div>
          )}
        </div>

        {/* Results */}
        <div className="mt-8">
          {query.isLoading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-52 w-full rounded-2xl bg-white/10" />
              ))}
            </div>
          ) : query.isError ? (
            <ErrorState error={query.error} onRetry={() => query.refetch()} />
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={hasFilters ? Search : Inbox}
              title={hasFilters ? "No matching records" : "No records yet"}
              description={
                hasFilters
                  ? "Try adjusting or clearing your filters."
                  : "Save a forecast from the home page, or create one here to get started."
              }
              action={
                <Button onClick={() => setCreateOpen(true)} className="bg-white text-slate-900 hover:bg-white/90">
                  <CalendarPlus className="h-4 w-4" /> Create a record
                </Button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <AnimatePresence mode="popLayout">
                {filtered.map((record) => (
                  <RecordCard key={record.id} record={record} onDelete={setToDelete} />
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>
      </main>

      <SaveRecordDialog open={createOpen} onOpenChange={setCreateOpen} navigateOnSuccess />
      <DeleteRecordDialog
        open={toDelete !== null}
        onOpenChange={(o) => !o && setToDelete(null)}
        recordId={toDelete?.id ?? null}
        recordLabel={toDelete?.location.resolved_name}
      />
    </>
  )
}
