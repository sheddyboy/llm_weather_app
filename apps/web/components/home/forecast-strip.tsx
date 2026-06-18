"use client"

import { motion } from "framer-motion"
import { format, parseISO } from "date-fns"
import { Skeleton } from "@/components/ui/skeleton"
import { WeatherIcon } from "@/components/weather-icon"
import { useUnits } from "@/lib/units-context"
import { formatTemp } from "@/lib/weather"
import type { ForecastDay } from "@/lib/types"

function dayLabel(dateStr: string, index: number) {
  try {
    const d = parseISO(dateStr)
    return index === 0 ? "Today" : format(d, "EEE")
  } catch {
    return dateStr
  }
}

export function ForecastStrip({ days }: { days: ForecastDay[] }) {
  const { unit } = useUnits()

  return (
    <section aria-label="Forecast">
      <h2 className="mb-3 px-1 text-sm font-medium uppercase tracking-wide text-white/70">Forecast</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {days.map((day, i) => (
          <motion.div
            key={day.date}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: i * 0.05 }}
            whileHover={{ y: -4 }}
            className="glass flex flex-col items-center gap-2 rounded-2xl p-4 text-center"
          >
            <p className="text-sm font-medium text-white/90">{dayLabel(day.date, i)}</p>
            <p className="text-xs text-white/55">
              {(() => {
                try {
                  return format(parseISO(day.date), "MMM d")
                } catch {
                  return day.date
                }
              })()}
            </p>
            <WeatherIcon conditions={day.conditions} className="my-1 h-9 w-9 text-white" strokeWidth={1.5} />
            <p className="text-xs text-white/70">{day.conditions}</p>
            <p className="text-sm font-semibold text-white">
              {formatTemp(day.temp_max, unit)}
              <span className="ml-1 font-normal text-white/55">{formatTemp(day.temp_min, unit)}</span>
            </p>
          </motion.div>
        ))}
      </div>
    </section>
  )
}

export function ForecastSkeleton() {
  return (
    <section aria-label="Loading forecast">
      <Skeleton className="mb-3 h-4 w-24 bg-white/10" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-40 w-full rounded-2xl bg-white/10" />
        ))}
      </div>
    </section>
  )
}
