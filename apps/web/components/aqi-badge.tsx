import { aqiInfo } from "@/lib/weather"
import { cn } from "@/lib/utils"

export function AqiBadge({ aqi, className }: { aqi: number | null | undefined; className?: string }) {
  const info = aqiInfo(aqi)
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        info.className,
        className,
      )}
      title={aqi ? `Air Quality Index: ${aqi}` : "Air quality data unavailable"}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", info.dot)} aria-hidden="true" />
      AQI {info.label}
    </span>
  )
}
