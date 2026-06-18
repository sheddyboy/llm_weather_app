"use client";

import { motion } from "framer-motion";
import { format, parseISO } from "date-fns";
import { CalendarRange, Eye, MapPin, Trash2 } from "lucide-react";
import Link from "next/link";
import { Button, buttonVariants } from "@/components/ui/button";
import { WeatherIcon } from "@/components/weather-icon";
import type { WeatherRecordRead } from "@/lib/types";

function fmt(dateStr: string) {
  try {
    return format(parseISO(dateStr), "MMM d, yyyy");
  } catch {
    return dateStr;
  }
}

export function RecordCard({
  record,
  onDelete,
}: {
  record: WeatherRecordRead;
  onDelete: (record: WeatherRecordRead) => void;
}) {
  const firstCondition = record.readings[0]?.conditions;

  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
      whileHover={{ y: -4 }}
      transition={{ duration: 0.3 }}
      className="glass flex flex-col rounded-2xl p-5"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-white">
            <MapPin
              className="h-4 w-4 shrink-0 text-white/70"
              aria-hidden="true"
            />
            <h3 className="truncate font-semibold">
              {record.location.resolved_name}
            </h3>
          </div>
          {record.location.country && (
            <p className="mt-0.5 text-xs text-white/60">
              {record.location.country}
            </p>
          )}
        </div>
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/10">
          <WeatherIcon
            conditions={firstCondition}
            className="h-5 w-5 text-white"
            strokeWidth={1.5}
          />
        </span>
      </div>

      <div className="mt-4 flex items-center gap-2 text-sm text-white/80">
        <CalendarRange className="h-4 w-4 text-white/60" aria-hidden="true" />
        <span>
          {fmt(record.start_date)} – {fmt(record.end_date)}
        </span>
      </div>

      <div className="mt-2 flex items-center justify-between text-xs text-white/55">
        <span>
          {record.readings.length} reading
          {record.readings.length === 1 ? "" : "s"}
        </span>
        <span>Saved {fmt(record.created_at)}</span>
      </div>

      <div className="mt-5 flex items-center gap-2">
        <Link
          href={`/records/${record.id}`}
          className={buttonVariants({
            variant: "default",
            className: "flex-1 bg-white text-slate-900 hover:bg-white/90 gap-2",
          })}
        >
          <Eye className="h-4 w-4" />
          View
        </Link>

        <Button
          variant="ghost"
          size="icon"
          aria-label={`Delete record for ${record.location.resolved_name}`}
          onClick={() => onDelete(record)}
          className="text-white/70 hover:bg-red-500/20 hover:text-red-100"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </motion.article>
  );
}
