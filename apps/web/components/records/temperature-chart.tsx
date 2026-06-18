"use client"

import { format, parseISO } from "date-fns"
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { useUnits } from "@/lib/units-context"
import { toNum, unitLabel } from "@/lib/weather"
import type { DailyReadingRead } from "@/lib/types"

function convert(c: number | null, unit: "c" | "f"): number | null {
  if (c === null) return null
  return unit === "f" ? c * (9 / 5) + 32 : c
}

interface ChartPoint {
  date: string
  label: string
  min: number | null
  max: number | null
}

function ChartTooltip({
  active,
  payload,
  unit,
}: {
  active?: boolean
  payload?: Array<{ payload: ChartPoint }>
  unit: "c" | "f"
}) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="glass-strong rounded-xl px-3 py-2 text-xs text-white">
      <p className="font-medium">{p.label}</p>
      <p className="mt-1 text-white/80">
        High: {p.max !== null ? `${Math.round(p.max)}${unitLabel(unit)}` : "--"}
      </p>
      <p className="text-white/80">Low: {p.min !== null ? `${Math.round(p.min)}${unitLabel(unit)}` : "--"}</p>
    </div>
  )
}

export function TemperatureChart({ readings }: { readings: DailyReadingRead[] }) {
  const { unit } = useUnits()

  const data: ChartPoint[] = [...readings]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((r) => {
      let label = r.date
      try {
        label = format(parseISO(r.date), "MMM d")
      } catch {
        // keep raw
      }
      return {
        date: r.date,
        label,
        min: convert(toNum(r.temp_min), unit),
        max: convert(toNum(r.temp_max), unit),
      }
    })

  return (
    <div className="h-72 w-full" aria-label="Temperature range chart">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="maxFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#fbbf24" stopOpacity={0.5} />
              <stop offset="100%" stopColor="#fbbf24" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="minFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#7dd3fc" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#7dd3fc" stopOpacity={0.03} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.12)" vertical={false} />
          <XAxis
            dataKey="label"
            stroke="rgba(255,255,255,0.6)"
            tick={{ fontSize: 12, fill: "rgba(255,255,255,0.7)" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="rgba(255,255,255,0.6)"
            tick={{ fontSize: 12, fill: "rgba(255,255,255,0.7)" }}
            tickLine={false}
            axisLine={false}
            width={44}
            unit={unitLabel(unit)}
          />
          <Tooltip content={<ChartTooltip unit={unit} />} cursor={{ stroke: "rgba(255,255,255,0.3)" }} />
          <Area
            type="monotone"
            dataKey="max"
            name="High"
            stroke="#fbbf24"
            strokeWidth={2}
            fill="url(#maxFill)"
            connectNulls
            dot={{ r: 2, fill: "#fbbf24" }}
          />
          <Area
            type="monotone"
            dataKey="min"
            name="Low"
            stroke="#7dd3fc"
            strokeWidth={2}
            fill="url(#minFill)"
            connectNulls
            dot={{ r: 2, fill: "#7dd3fc" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
