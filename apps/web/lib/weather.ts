export type Unit = "c" | "f"

/** Coerce the API's `number | string | null` numerics into a number or null. */
export function toNum(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined) return null
  const n = typeof value === "string" ? Number.parseFloat(value) : value
  return Number.isFinite(n) ? n : null
}

/** Convert a metric (°C) temperature to the selected unit and round. */
export function formatTemp(celsius: number | string | null | undefined, unit: Unit, withDegree = true): string {
  const c = toNum(celsius)
  if (c === null) return "--"
  const value = unit === "f" ? c * (9 / 5) + 32 : c
  const rounded = Math.round(value)
  return withDegree ? `${rounded}°` : `${rounded}`
}

export function unitLabel(unit: Unit): string {
  return unit === "f" ? "°F" : "°C"
}

/** Convert m/s (metric) to the selected unit's wind speed and format. */
export function formatWind(metersPerSecond: number | string | null | undefined, unit: Unit): string {
  const ms = toNum(metersPerSecond)
  if (ms === null) return "--"
  if (unit === "f") {
    return `${Math.round(ms * 2.237)} mph`
  }
  return `${ms.toFixed(1)} m/s`
}

export function formatHumidity(humidity: number | null | undefined): string {
  const h = toNum(humidity ?? null)
  if (h === null) return "--"
  return `${Math.round(h)}%`
}

// ---- AQI ----

export interface AqiInfo {
  label: string
  /** Tailwind classes for a badge background + text. */
  className: string
  /** Solid dot color class. */
  dot: string
}

export function aqiInfo(aqi: number | null | undefined): AqiInfo {
  switch (aqi) {
    case 1:
      return { label: "Good", className: "bg-emerald-500/20 text-emerald-100 border-emerald-300/30", dot: "bg-emerald-400" }
    case 2:
      return { label: "Fair", className: "bg-lime-500/20 text-lime-100 border-lime-300/30", dot: "bg-lime-400" }
    case 3:
      return { label: "Moderate", className: "bg-amber-500/20 text-amber-100 border-amber-300/30", dot: "bg-amber-400" }
    case 4:
      return { label: "Poor", className: "bg-orange-500/20 text-orange-100 border-orange-300/30", dot: "bg-orange-400" }
    case 5:
      return { label: "Very Poor", className: "bg-red-500/20 text-red-100 border-red-300/30", dot: "bg-red-400" }
    default:
      return { label: "No data", className: "bg-white/10 text-white/60 border-white/20", dot: "bg-white/40" }
  }
}

// ---- Condition theming ----

export type ConditionGroup = "clear" | "clouds" | "rain" | "snow" | "thunderstorm" | "mist"

export function conditionGroup(conditions: string | null | undefined): ConditionGroup {
  const c = (conditions || "").toLowerCase()
  if (c.includes("thunder") || c.includes("storm")) return "thunderstorm"
  if (c.includes("snow") || c.includes("sleet")) return "snow"
  if (c.includes("rain") || c.includes("drizzle")) return "rain"
  if (c.includes("cloud") || c.includes("overcast")) return "clouds"
  if (c.includes("mist") || c.includes("fog") || c.includes("haze") || c.includes("smoke")) return "mist"
  return "clear"
}

export function isNight(date = new Date()): boolean {
  const h = date.getHours()
  return h < 6 || h >= 19
}

/**
 * Returns the CSS gradient stops (as CSS custom property values) for a given
 * condition + time of day. Used to drive the animated sky background.
 */
export function skyGradient(conditions: string | null | undefined, night = isNight()): { from: string; via: string; to: string } {
  const group = conditionGroup(conditions)

  if (night) {
    switch (group) {
      case "clear":
        return { from: "#1e1b4b", via: "#312e81", to: "#4c1d95" }
      case "clouds":
        return { from: "#1e293b", via: "#334155", to: "#475569" }
      case "rain":
        return { from: "#0f2027", via: "#203a43", to: "#2c5364" }
      case "snow":
        return { from: "#1e293b", via: "#475569", to: "#64748b" }
      case "thunderstorm":
        return { from: "#1a1a2e", via: "#16213e", to: "#0f0f1a" }
      case "mist":
        return { from: "#283048", via: "#3a4a5c", to: "#4b5563" }
    }
  }

  switch (group) {
    case "clear":
      return { from: "#2563eb", via: "#0ea5e9", to: "#22d3ee" }
    case "clouds":
      return { from: "#475569", via: "#64748b", to: "#94a3b8" }
    case "rain":
      return { from: "#334155", via: "#475569", to: "#5b7c8a" }
    case "snow":
      return { from: "#bcd2e8", via: "#cde0f0", to: "#e8f1f8" }
    case "thunderstorm":
      return { from: "#312e3f", via: "#3b3556", to: "#1f1b2e" }
    case "mist":
      return { from: "#94a3b8", via: "#a8b2bd", to: "#cbd5e1" }
    default:
      return { from: "#2563eb", via: "#0ea5e9", to: "#22d3ee" }
  }
}
