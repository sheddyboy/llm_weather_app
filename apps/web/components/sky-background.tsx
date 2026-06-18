"use client"

import { skyGradient } from "@/lib/weather"
import type { CSSProperties } from "react"

interface SkyBackgroundProps {
  conditions: string | null | undefined
  /** Force night styling; defaults to local time inside skyGradient. */
  night?: boolean
}

/**
 * Full-screen fixed animated sky gradient that reacts to weather conditions
 * and time of day, with gently floating parallax blobs behind the glass UI.
 */
export function SkyBackground({ conditions, night }: SkyBackgroundProps) {
  const g = skyGradient(conditions, night)

  const style = {
    "--sky-from": g.from,
    "--sky-via": g.via,
    "--sky-to": g.to,
  } as CSSProperties

  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="sky-gradient absolute inset-0" style={style} />

      {/* Floating parallax blobs for depth. */}
      <div
        className="sky-blob absolute -left-32 -top-24 h-[28rem] w-[28rem] rounded-full opacity-40 blur-3xl"
        style={{ background: g.via, animationDelay: "0s" }}
      />
      <div
        className="sky-blob absolute -right-24 top-1/3 h-[24rem] w-[24rem] rounded-full opacity-30 blur-3xl"
        style={{ background: g.to, animationDelay: "-6s" }}
      />
      <div
        className="sky-blob absolute bottom-[-8rem] left-1/4 h-[30rem] w-[30rem] rounded-full opacity-25 blur-3xl"
        style={{ background: g.from, animationDelay: "-12s" }}
      />

      {/* Subtle scrim to guarantee text contrast over light gradients. */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/10 via-transparent to-black/30" />
    </div>
  )
}
