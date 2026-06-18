"use client"

import { createContext, useCallback, useContext, useEffect, useState } from "react"
import type { Unit } from "./weather"

interface UnitsContextValue {
  unit: Unit
  setUnit: (unit: Unit) => void
  toggleUnit: () => void
}

const UnitsContext = createContext<UnitsContextValue | null>(null)

const STORAGE_KEY = "weather-app:unit"

export function UnitsProvider({ children }: { children: React.ReactNode }) {
  const [unit, setUnitState] = useState<Unit>("c")

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY)
      if (stored === "c" || stored === "f") {
        setUnitState(stored)
      }
    } catch {
      // ignore
    }
  }, [])

  const setUnit = useCallback((next: Unit) => {
    setUnitState(next)
    try {
      window.localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // ignore
    }
  }, [])

  const toggleUnit = useCallback(() => {
    setUnitState((prev) => {
      const next = prev === "c" ? "f" : "c"
      try {
        window.localStorage.setItem(STORAGE_KEY, next)
      } catch {
        // ignore
      }
      return next
    })
  }, [])

  return <UnitsContext.Provider value={{ unit, setUnit, toggleUnit }}>{children}</UnitsContext.Provider>
}

export function useUnits() {
  const ctx = useContext(UnitsContext)
  if (!ctx) throw new Error("useUnits must be used within a UnitsProvider")
  return ctx
}
