"use client"

import { motion } from "framer-motion"
import { BookmarkPlus, Droplets, MapPin, Thermometer, Wind } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { WeatherIcon } from "@/components/weather-icon"
import { useUnits } from "@/lib/units-context"
import { formatHumidity, formatTemp, formatWind, unitLabel } from "@/lib/weather"
import type { CurrentWeatherResponse } from "@/lib/types"

function Stat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
  return (
    <div className="glass flex items-center gap-3 rounded-xl px-4 py-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/10 text-white/80">{icon}</div>
      <div>
        <p className="text-xs text-white/60">{label}</p>
        <p className="text-sm font-semibold text-white">{value}</p>
      </div>
    </div>
  )
}

export function CurrentWeatherCard({
  data,
  onSave,
}: {
  data: CurrentWeatherResponse
  onSave: () => void
}) {
  const { unit } = useUnits()
  const { location, current } = data

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
      className="glass-strong rounded-3xl p-6 sm:p-8"
      aria-label="Current weather"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-2 text-white/80">
          <MapPin className="h-4 w-4" aria-hidden="true" />
          <span className="font-medium text-white">{location.resolved_name}</span>
          {location.country && <span className="text-white/60">{location.country}</span>}
        </div>
        <Button onClick={onSave} className="bg-white text-slate-900 hover:bg-white/90">
          <BookmarkPlus className="h-4 w-4" /> Save this as a record
        </Button>
      </div>

      <div className="mt-6 flex flex-col items-center gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-5">
          <WeatherIcon conditions={current.conditions} className="h-20 w-20 text-white" strokeWidth={1.25} />
          <div>
            <div className="flex items-start">
              <span className="text-6xl font-semibold tracking-tighter text-white sm:text-7xl">
                {formatTemp(current.temp, unit, false)}
              </span>
              <span className="mt-2 text-2xl font-medium text-white/70">{unitLabel(unit)}</span>
            </div>
            <p className="text-lg font-medium text-white/90">{current.conditions}</p>
          </div>
        </div>

        <div className="text-center text-sm text-white/70 sm:text-right">
          <p>
            High {formatTemp(current.temp_max, unit)} · Low {formatTemp(current.temp_min, unit)}
          </p>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Stat
          icon={<Thermometer className="h-5 w-5" />}
          label="Feels range"
          value={`${formatTemp(current.temp_min, unit)} – ${formatTemp(current.temp_max, unit)}`}
        />
        <Stat icon={<Droplets className="h-5 w-5" />} label="Humidity" value={formatHumidity(current.humidity)} />
        <Stat icon={<Wind className="h-5 w-5" />} label="Wind" value={formatWind(current.wind_speed, unit)} />
      </div>
    </motion.section>
  )
}

export function CurrentWeatherSkeleton() {
  return (
    <div className="glass-strong rounded-3xl p-6 sm:p-8">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-40 bg-white/10" />
        <Skeleton className="h-9 w-44 bg-white/10" />
      </div>
      <div className="mt-6 flex items-center gap-5">
        <Skeleton className="h-20 w-20 rounded-full bg-white/10" />
        <div className="space-y-2">
          <Skeleton className="h-16 w-40 bg-white/10" />
          <Skeleton className="h-5 w-28 bg-white/10" />
        </div>
      </div>
      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-16 w-full rounded-xl bg-white/10" />
        ))}
      </div>
    </div>
  )
}
