"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { format, parseISO } from "date-fns";
import { ArrowLeft, CalendarRange, MapPin, Pencil, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SkyBackground } from "@/components/sky-background";
import { WeatherIcon } from "@/components/weather-icon";
import { AqiBadge } from "@/components/aqi-badge";
import { EmptyState, ErrorState } from "@/components/ui-states";
import { EditRecordDialog } from "@/components/records/edit-record-dialog";
import { ExportMenu } from "@/components/records/export-menu";
import { TemperatureChart } from "@/components/records/temperature-chart";
import { BriefingPanel } from "@/components/records/briefing-panel";
import { MediaPanel } from "@/components/records/media-panel";
import { DeleteRecordDialog } from "@/components/delete-record-dialog";
import { api } from "@/lib/api";
import { useUnits } from "@/lib/units-context";
import { formatTemp } from "@/lib/weather";
import type { DailyReadingRead } from "@/lib/types";

function fmt(dateStr: string) {
  try {
    return format(parseISO(dateStr), "MMM d, yyyy");
  } catch {
    return dateStr;
  }
}

function ReadingDayCard({ reading }: { reading: DailyReadingRead }) {
  const { unit } = useUnits();
  let day = reading.date;
  try {
    day = format(parseISO(reading.date), "EEE, MMM d");
  } catch {
    // keep raw
  }
  return (
    <div className="glass flex items-center justify-between gap-3 rounded-2xl p-4">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10">
          <WeatherIcon
            conditions={reading.conditions}
            className="h-5 w-5 text-white"
            strokeWidth={1.5}
          />
        </span>
        <div>
          <p className="text-sm font-medium text-white">{day}</p>
          <p className="text-xs text-white/65">{reading.conditions}</p>
        </div>
      </div>
      <div className="flex flex-col items-end gap-1.5">
        <p className="text-sm font-semibold text-white">
          {formatTemp(reading.temp_max, unit)}
          <span className="ml-1 font-normal text-white/55">
            {formatTemp(reading.temp_min, unit)}
          </span>
        </p>
        <AqiBadge aqi={reading.aqi} />
      </div>
    </div>
  );
}

export function RecordDetailView({ recordId }: { recordId: string }) {
  const router = useRouter();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const query = useQuery({
    queryKey: ["record", recordId],
    queryFn: () => api.getRecord(recordId),
  });

  const record = query.data;
  const heroCondition = record?.readings[0]?.conditions;

  return (
    <>
      <SkyBackground conditions={heroCondition ?? "clear"} />

      <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
        <Link
          href="/records"
          className={buttonVariants({
            variant: "ghost",
            size: "sm",
            className: "mb-4 text-white/80 hover:bg-white/10 hover:text-white",
          })}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to records
        </Link>
        {query.isLoading ? (
          <div className="space-y-6">
            <Skeleton className="h-40 w-full rounded-3xl bg-white/10" />
            <Skeleton className="h-72 w-full rounded-3xl bg-white/10" />
          </div>
        ) : query.isError ? (
          <ErrorState error={query.error} onRetry={() => query.refetch()} />
        ) : record ? (
          <>
            {/* Hero */}
            <motion.section
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45 }}
              className="glass-strong rounded-3xl p-6 sm:p-8"
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="flex items-start gap-4">
                  <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10">
                    <WeatherIcon
                      conditions={heroCondition}
                      className="h-7 w-7 text-white"
                      strokeWidth={1.4}
                    />
                  </span>
                  <div>
                    <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                      <MapPin
                        className="h-5 w-5 text-white/70"
                        aria-hidden="true"
                      />
                      {record.location.resolved_name}
                      {record.location.country && (
                        <span className="text-base font-normal text-white/60">
                          {record.location.country}
                        </span>
                      )}
                    </h1>
                    <p className="mt-1 flex items-center gap-2 text-sm text-white/75">
                      <CalendarRange
                        className="h-4 w-4 text-white/60"
                        aria-hidden="true"
                      />
                      {fmt(record.start_date)} – {fmt(record.end_date)}
                      <span className="text-white/40">·</span>
                      {record.readings.length} reading
                      {record.readings.length === 1 ? "" : "s"}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    variant="secondary"
                    onClick={() => setEditOpen(true)}
                    className="bg-white/15 text-white hover:bg-white/25"
                  >
                    <Pencil className="h-4 w-4" /> Edit
                  </Button>
                  <ExportMenu recordId={record.id} />
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Delete record"
                    onClick={() => setDeleteOpen(true)}
                    className="text-white/70 hover:bg-red-500/20 hover:text-red-100"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </motion.section>

            {/* Tabs */}
            <div className="mt-6">
              <Tabs defaultValue="readings">
                <TabsList className="glass h-auto rounded-2xl p-1 text-white">
                  <TabsTrigger
                    value="readings"
                    className="rounded-xl px-4 py-2 text-white/70 data-[state=active]:bg-white data-[state=active]:text-slate-900"
                  >
                    Readings
                  </TabsTrigger>
                  <TabsTrigger
                    value="briefing"
                    className="rounded-xl px-4 py-2 text-white/70 data-[state=active]:bg-white data-[state=active]:text-slate-900"
                  >
                    AI Briefing
                  </TabsTrigger>
                  <TabsTrigger
                    value="media"
                    className="rounded-xl px-4 py-2 text-white/70 data-[state=active]:bg-white data-[state=active]:text-slate-900"
                  >
                    Media
                  </TabsTrigger>
                </TabsList>

                <TabsContent
                  value="readings"
                  className="mt-5 space-y-6 focus-visible:outline-none"
                >
                  {record.readings.length > 0 ? (
                    <>
                      <div className="glass-strong rounded-3xl p-5 sm:p-6">
                        <h2 className="mb-2 text-sm font-medium uppercase tracking-wide text-white/70">
                          Temperature range
                        </h2>
                        <TemperatureChart readings={record.readings} />
                      </div>
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        {[...record.readings]
                          .sort((a, b) => a.date.localeCompare(b.date))
                          .map((r) => (
                            <ReadingDayCard key={r.id} reading={r} />
                          ))}
                      </div>
                    </>
                  ) : (
                    <EmptyState
                      icon={CalendarRange}
                      title="No readings stored"
                      description="This date range falls outside the forecast horizon, so no daily readings were saved. Edit the record to pick dates within the next few days."
                      action={
                        <Button
                          onClick={() => setEditOpen(true)}
                          className="bg-white text-slate-900 hover:bg-white/90"
                        >
                          <Pencil className="h-4 w-4" /> Edit dates
                        </Button>
                      }
                    />
                  )}
                </TabsContent>

                <TabsContent
                  value="briefing"
                  className="mt-5 focus-visible:outline-none"
                >
                  <BriefingPanel recordId={record.id} />
                </TabsContent>

                <TabsContent
                  value="media"
                  className="mt-5 focus-visible:outline-none"
                >
                  <MediaPanel recordId={record.id} />
                </TabsContent>
              </Tabs>
            </div>

            <EditRecordDialog
              open={editOpen}
              onOpenChange={setEditOpen}
              record={record}
            />
            <DeleteRecordDialog
              open={deleteOpen}
              onOpenChange={setDeleteOpen}
              recordId={record.id}
              recordLabel={record.location.resolved_name}
              onDeleted={() => router.push("/records")}
            />
          </>
        ) : null}
      </main>
    </>
  );
}
