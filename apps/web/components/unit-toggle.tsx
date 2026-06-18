"use client"

import { useUnits } from "@/lib/units-context"
import { cn } from "@/lib/utils"

export function UnitToggle() {
  const { unit, setUnit } = useUnits()

  return (
    <div
      role="group"
      aria-label="Temperature unit"
      className="glass inline-flex items-center rounded-full p-0.5 text-sm font-medium"
    >
      <button
        type="button"
        aria-pressed={unit === "c"}
        onClick={() => setUnit("c")}
        className={cn(
          "rounded-full px-3 py-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60",
          unit === "c" ? "bg-white text-slate-900" : "text-white/70 hover:text-white",
        )}
      >
        °C
      </button>
      <button
        type="button"
        aria-pressed={unit === "f"}
        onClick={() => setUnit("f")}
        className={cn(
          "rounded-full px-3 py-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60",
          unit === "f" ? "bg-white text-slate-900" : "text-white/70 hover:text-white",
        )}
      >
        °F
      </button>
    </div>
  )
}
