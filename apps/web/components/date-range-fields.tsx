"use client"

import { Label } from "@/components/ui/label"

interface DateRangeFieldsProps {
  startDate: string
  endDate: string
  onStartChange: (value: string) => void
  onEndChange: (value: string) => void
  idPrefix?: string
}

const inputClass =
  "w-full rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-sm text-white outline-none [color-scheme:dark] placeholder:text-white/50 focus-visible:ring-2 focus-visible:ring-white/60"

export function DateRangeFields({
  startDate,
  endDate,
  onStartChange,
  onEndChange,
  idPrefix = "range",
}: DateRangeFieldsProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div className="space-y-1.5">
        <Label htmlFor={`${idPrefix}-start`} className="text-white/80">
          Start date
        </Label>
        <input
          id={`${idPrefix}-start`}
          type="date"
          value={startDate}
          max={endDate || undefined}
          onChange={(e) => onStartChange(e.target.value)}
          className={inputClass}
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor={`${idPrefix}-end`} className="text-white/80">
          End date
        </Label>
        <input
          id={`${idPrefix}-end`}
          type="date"
          value={endDate}
          min={startDate || undefined}
          onChange={(e) => onEndChange(e.target.value)}
          className={inputClass}
        />
      </div>
    </div>
  )
}
