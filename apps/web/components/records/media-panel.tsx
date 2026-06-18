"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ExternalLink,
  MapPin,
  PlayCircle,
  Star,
  VideoIcon,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState, ErrorState } from "@/components/ui-states";
import { api } from "@/lib/api";
import type { PointOfInterest, VideoItem } from "@/lib/types";

function VideoCard({ video }: { video: VideoItem }) {
  return (
    <a
      href={video.url}
      target="_blank"
      rel="noopener noreferrer"
      className="glass group flex flex-col overflow-hidden rounded-2xl transition-transform hover:-translate-y-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
    >
      <div className="relative aspect-video w-full overflow-hidden bg-white/10">
        {video.thumbnail ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={video.thumbnail || "/placeholder.svg"}
            alt=""
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            crossOrigin="anonymous"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <VideoIcon className="h-10 w-10 text-white/50" aria-hidden="true" />
          </div>
        )}
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 transition-opacity group-hover:opacity-100">
          <PlayCircle className="h-12 w-12 text-white" aria-hidden="true" />
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-1 p-4">
        <h4 className="line-clamp-2 text-sm font-medium text-white">
          {video.title}
        </h4>
        <p className="mt-auto flex items-center gap-1 pt-1 text-xs text-white/60">
          <VideoIcon className="h-3.5 w-3.5" aria-hidden="true" />
          {video.channel ?? "Video"}
          <ExternalLink className="ml-auto h-3.5 w-3.5" aria-hidden="true" />
        </p>
      </div>
    </a>
  );
}

function Stars({ rating }: { rating: number }) {
  return (
    <span
      className="flex items-center gap-0.5"
      aria-label={`Rated ${rating} out of 5`}
    >
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={`h-3.5 w-3.5 ${i < Math.round(rating) ? "fill-amber-400 text-amber-400" : "text-white/30"}`}
          aria-hidden="true"
        />
      ))}
      <span className="ml-1 text-xs text-white/70">{rating.toFixed(1)}</span>
    </span>
  );
}

function PoiItem({ poi }: { poi: PointOfInterest }) {
  return (
    <li className="glass flex items-start gap-3 rounded-xl p-4">
      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10">
        <MapPin className="h-4 w-4 text-white/80" aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="font-medium text-white">{poi.name}</p>
          {poi.rating !== null && <Stars rating={poi.rating} />}
        </div>
        {poi.address && (
          <p className="mt-0.5 text-xs text-white/60">{poi.address}</p>
        )}
        {poi.types.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {poi.types.slice(0, 4).map((t) => (
              <span
                key={t}
                className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] text-white/70"
              >
                {t.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        )}
      </div>
    </li>
  );
}

export function MediaPanel({ recordId }: { recordId: string }) {
  const query = useQuery({
    queryKey: ["media", recordId],
    queryFn: () => api.media(recordId),
    staleTime: 5 * 60_000,
  });

  if (query.isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-52 w-full rounded-2xl bg-white/10" />
          ))}
        </div>
      </div>
    );
  }

  if (query.isError) {
    return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  }

  const videos = query.data?.videos ?? [];
  const pois = query.data?.points_of_interest ?? [];

  return (
    <div className="space-y-8">
      <section>
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium uppercase tracking-wide text-white/70">
          <VideoIcon className="h-4 w-4" aria-hidden="true" /> Videos
        </h3>
        {videos.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {videos.map((v) => (
              <VideoCard key={v.video_id} video={v} />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={VideoIcon}
            title="No videos to show"
            description="Video results aren't available for this location right now."
          />
        )}
      </section>

      <section>
        <h3 className="mb-3 flex items-center gap-2 text-sm font-medium uppercase tracking-wide text-white/70">
          <MapPin className="h-4 w-4" aria-hidden="true" /> Nearby points of
          interest
        </h3>
        {pois.length > 0 ? (
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {pois.map((p, i) => (
              <PoiItem key={`${p.name}-${i}`} poi={p} />
            ))}
          </ul>
        ) : (
          <EmptyState
            icon={MapPin}
            title="No nearby places"
            description="Points of interest aren't available for this location right now."
          />
        )}
      </section>
    </div>
  );
}
