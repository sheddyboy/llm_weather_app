"use client"

import { useQuery } from "@tanstack/react-query"
import { motion } from "framer-motion"
import { MapPin, Search } from "lucide-react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { SkyBackground } from "@/components/sky-background"
import { SaveRecordDialog } from "@/components/save-record-dialog"
import { ErrorState, EmptyState } from "@/components/ui-states"
import { CurrentWeatherCard, CurrentWeatherSkeleton } from "@/components/home/current-weather-card"
import { ForecastStrip, ForecastSkeleton } from "@/components/home/forecast-strip"
import { api } from "@/lib/api"

export function HomeView() {
  const [input, setInput] = useState("")
  const [location, setLocation] = useState("")
  const [saveOpen, setSaveOpen] = useState(false)

  const enabled = location.trim().length > 0

  const currentQuery = useQuery({
    queryKey: ["current", location],
    queryFn: () => api.currentWeather(location),
    enabled,
  })

  const forecastQuery = useQuery({
    queryKey: ["forecast", location],
    queryFn: () => api.forecast(location),
    enabled,
  })

  const conditions = currentQuery.data?.current.conditions
  const resolved = currentQuery.data?.location ?? forecastQuery.data?.location

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLocation(input.trim())
  }

  return (
    <>
      <SkyBackground conditions={conditions} />

      <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mx-auto max-w-2xl text-center"
        >
          <h1 className="text-balance text-3xl font-semibold tracking-tight text-white sm:text-5xl">
            Weather, beautifully clear
          </h1>
          <p className="mx-auto mt-3 max-w-md text-pretty text-white/75">
            Search any city, place, or zip for live conditions and a multi-day forecast.
          </p>

          <form onSubmit={handleSubmit} className="glass mt-6 flex items-center gap-2 rounded-2xl p-2">
            <div className="relative flex-1">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-white/60"
                aria-hidden="true"
              />
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Search any city, place, or zip"
                aria-label="Search location"
                className="border-0 bg-transparent pl-9 text-white placeholder:text-white/50 focus-visible:ring-0"
              />
            </div>
            <Button type="submit" className="bg-white text-slate-900 hover:bg-white/90">
              Search
            </Button>
          </form>
        </motion.div>

        {/* Results */}
        <div className="mt-10 space-y-6">
          {!enabled && (
            <EmptyState
              icon={MapPin}
              title="Start with a search"
              description="Enter a location above to see current conditions and the days ahead."
              className="mx-auto max-w-lg"
            />
          )}

          {enabled && (
            <>
              {/* Current weather */}
              {currentQuery.isLoading ? (
                <CurrentWeatherSkeleton />
              ) : currentQuery.isError ? (
                <ErrorState error={currentQuery.error} onRetry={() => currentQuery.refetch()} />
              ) : currentQuery.data ? (
                <CurrentWeatherCard
                  data={currentQuery.data}
                  onSave={() => setSaveOpen(true)}
                />
              ) : null}

              {/* Forecast */}
              {forecastQuery.isLoading ? (
                <ForecastSkeleton />
              ) : forecastQuery.isError ? (
                <ErrorState error={forecastQuery.error} onRetry={() => forecastQuery.refetch()} />
              ) : forecastQuery.data && forecastQuery.data.days.length > 0 ? (
                <ForecastStrip days={forecastQuery.data.days} />
              ) : forecastQuery.data ? (
                <EmptyState title="No forecast available" description="The provider didn't return upcoming days for this location." />
              ) : null}
            </>
          )}
        </div>
      </main>

      <SaveRecordDialog
        open={saveOpen}
        onOpenChange={setSaveOpen}
        defaultLocation={resolved?.resolved_name ?? location}
        navigateOnSuccess
      />
    </>
  )
}
