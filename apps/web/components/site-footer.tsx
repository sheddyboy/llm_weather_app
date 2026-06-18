"use client"

import { useQuery } from "@tanstack/react-query"
import { Fragment } from "react"
import { api } from "@/lib/api"

const URL_REGEX = /(https?:\/\/[^\s]+)/g

/** Split a string into text + anchor segments so embedded URLs become links. */
function linkify(text: string) {
  const parts = text.split(URL_REGEX)
  return parts.map((part, i) => {
    if (URL_REGEX.test(part)) {
      // reset lastIndex because of the global flag
      URL_REGEX.lastIndex = 0
      return (
        <a
          key={i}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium text-white underline decoration-white/40 underline-offset-2 hover:decoration-white"
        >
          {part}
        </a>
      )
    }
    return <Fragment key={i}>{part}</Fragment>
  })
}

export function SiteFooter() {
  const { data } = useQuery({
    queryKey: ["meta"],
    queryFn: api.meta,
    staleTime: Number.POSITIVE_INFINITY,
    retry: false,
  })

  const name = data?.name ?? "Weather App"
  const description = data?.description

  return (
    <footer className="px-3 pb-4 pt-10 sm:px-6">
      <div className="glass mx-auto max-w-6xl rounded-2xl px-5 py-4 text-center text-sm text-white/70">
        <p className="font-medium text-white/90">{name}</p>
        <p className="mt-1 text-balance leading-relaxed">
          {description ? linkify(description) : "Loading attribution…"}
        </p>
      </div>
    </footer>
  )
}
