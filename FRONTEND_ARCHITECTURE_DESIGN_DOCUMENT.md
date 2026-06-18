# Weather App Frontend — Architecture Design Document

Engineering reference for the frontend portion of the PM Accelerator AI Engineer Intern weather app assessment (full stack / dual role track). The frontend is a Next.js single-page-style app ("Skyglass") that consumes the FastAPI backend documented in `ARCHITECTURE_DESIGN_DOCUMENT.md`. It was scaffolded from a v0 prompt and lives entirely in `apps/web/`.

## 1. Scope

**In scope**: live current-weather search, multi-day forecast, saved-record CRUD (create, list, read, update, delete), per-record AI briefing, per-record media (videos + points of interest), multi-format export download, unit (°C/°F) switching, immersive glassmorphic UI with a weather-reactive animated background, loading/empty/error states, and containerized deployment.

**Explicitly out of scope**: authentication and per-user data segregation. The backend stores records with no row-level security by design, so the frontend treats all records as globally visible and never sends credentials. No server-side rendering of data either: every data view is a client component that fetches from the browser.

## 2. Tech stack

| Layer | Choice | Version (as of build time) |
|---|---|---|
| Language | TypeScript | 5.7.3 |
| Package manager | pnpm | pinned 10.18.1 (`packageManager` field) |
| Framework | Next.js (App Router) | 16.2.6 |
| UI runtime | React | 19 |
| Server data / caching | TanStack Query (`@tanstack/react-query`) | 5.101.x |
| Styling | Tailwind CSS v4 (`@tailwindcss/postcss`) | 4.2.x |
| Component primitives | shadcn + `@base-ui/react` | shadcn 4.8.x / base-ui 1.5.x |
| Icons | lucide-react | 1.16.x |
| Animation | framer-motion | 12.40.x |
| Charts | recharts | 3.8.x |
| Date utilities | date-fns | 4.4.x |
| Date picker | react-day-picker | 10.x |
| Toasts | sonner | 2.0.x |
| Theming | next-themes | 0.4.x |
| Class utilities | clsx + tailwind-merge + class-variance-authority | latest |

Build is configured for `output: "standalone"` so the Docker runner ships only the traced bundle. `typescript.ignoreBuildErrors` and `images.unoptimized` are enabled (see `next.config.mjs`), a v0 default that keeps the build unblocked at this assessment scope.

## 3. System architecture

Browser (Next.js client components) → FastAPI backend (`NEXT_PUBLIC_API_BASE_URL`, default `http://localhost:8000`).

There is no Next.js API route or backend-for-frontend layer; the browser talks to FastAPI directly. CORS on the backend is the contract that makes this work. The app is structured in three concentric layers:

```
app/ (routes, layout)
  └─ components/ (views + UI)
       └─ lib/ (api client, types, domain helpers, contexts)
              └─ fetch → FastAPI
```

- **`lib/`** is the only place that knows the backend exists. `lib/api.ts` is the single typed gateway; nothing else calls `fetch`.
- **`components/`** holds feature "views" (one per route) and shared/presentational pieces. Views own data fetching via TanStack Query hooks; presentational components receive props.
- **`app/`** is thin: each route file renders one view component.

## 4. Routing and page structure

App Router, three routes, all rendering client-side feature views:

| Route | File | View | Purpose |
|---|---|---|---|
| `/` | `app/page.tsx` | `home/home-view.tsx` | Search a location, show current weather + forecast, save as record |
| `/records` | `app/records/page.tsx` | `records/records-view.tsx` | List/filter saved records, create, delete |
| `/records/[id]` | `app/records/[id]/page.tsx` | `records/record-detail-view.tsx` | One record: readings, chart, AI briefing, media, edit/delete/export |

`app/layout.tsx` is the shared shell: forces dark mode (`<html className="dark">`), loads the Geist sans/mono fonts, wraps everything in `Providers`, and renders a persistent `SiteHeader` / `SiteFooter` around the routed content. Metadata brands the app as "Skyglass — Immersive Weather"; Vercel Analytics mounts only in production.

## 5. Data layer (API client)

`lib/api.ts` exposes a single `api` object with one method per backend endpoint, all going through a private `apiFetch<T>` helper. Responsibilities of that helper:

- Prefix every path with `API_BASE_URL` (env-driven, trailing slash stripped).
- Set `Content-Type: application/json` and serialize bodies.
- **Normalize errors into a typed `ApiError`** carrying `{ message, code, status }`. It recognizes the backend's `{ error: { code, message } }` envelope and surfaces the human-friendly message; a thrown `fetch` (backend down / CORS) becomes a `network_error` with status `0` and a "make sure the backend is running" hint.
- Handle `204 No Content` (delete) and a `raw: true` mode that returns the bare `Response` for blob exports.

Endpoint methods mirror the backend surface exactly: `health`, `meta`, `currentWeather`, `forecast`, `createRecord`, `listRecords`, `getRecord`, `updateRecord`, `deleteRecord`, `briefing`, `media`, `exportRecord` / `exportUrl`.

### Types contract

`lib/types.ts` mirrors the FastAPI response shapes in **snake_case**, deliberately not camel-casing, so the boundary is a 1:1 reflection of the API and there is no translation layer to drift. Numeric fields are typed `number | string` because the backend serializes SQLAlchemy `numeric` columns as strings; `lib/weather.ts#toNum` coerces them at the point of use. `ApiErrorCode` enumerates the known backend codes plus the two client-only codes (`http_error`, `network_error`) with an open `(string & {})` escape hatch.

## 6. Server-state management

TanStack Query owns all server state; there is no Redux/Zustand global store. The client is created once in `components/providers.tsx` with these defaults:

- `staleTime: 60_000` (1 min) and `refetchOnWindowFocus: false`, since weather data is already cached server-side and does not need aggressive refetching.
- A `retry` predicate that **does not retry 4xx** (a `not_found` or bad-input `ApiError`) and retries other failures at most twice.

Query key conventions:

| Key | Where | Notes |
|---|---|---|
| `["current", location]` | home | enabled only when a location string is set |
| `["forecast", location]` | home | same gating |
| `["records", { start_date, end_date }]` | records list | date filters are server-side |
| `["record", id]` | record detail | |
| `["briefing", id]` / `["media", id]` | detail tabs | lazy, per tab |

Mutations (`createRecord`, `updateRecord`, `deleteRecord`) invalidate `["records"]` (and the specific `["record", id]`) on success, then fire a `sonner` toast. Errors are caught and shown as a toast using the `ApiError` message. Location filtering on the list is **client-side** (the backend filters by `location_id` only), done with a `useMemo` over the fetched set against name/query/country.

## 7. State and context

Two small client contexts, both in `lib/` and mounted in `Providers`:

- **`UnitsProvider` (`lib/units-context.tsx`)**: holds the `"c" | "f"` temperature unit, persisted to `localStorage` under `weather-app:unit`, exposed via `useUnits()`. All temperatures are stored/fetched in metric and converted at render time by `lib/weather.ts#formatTemp` / `formatWind`, so switching units never refetches.
- **Theme**: the app is dark-only by design (`next-themes` is present, `<html>` is hard-coded `dark`).

Local UI state (search input, dialog open/closed, active filter values) lives in `useState` inside the relevant view; it is intentionally not lifted into context.

## 8. Domain helpers (`lib/weather.ts`)

Pure presentation logic kept out of components:

- **Numeric coercion**: `toNum` for the `number | string | null` API quirk.
- **Formatting**: `formatTemp`, `formatWind`, `formatHumidity`, `unitLabel`, all unit-aware.
- **AQI**: `aqiInfo(1..5)` maps the backend's air-quality index to a label ("Good".."Very Poor") and Tailwind badge classes; anything else is "No data".
- **Condition theming**: `conditionGroup` buckets a free-text condition string into one of six groups (`clear`, `clouds`, `rain`, `snow`, `thunderstorm`, `mist`); `isNight` and `skyGradient` turn that group + time-of-day into the three gradient stops that drive the animated background.

## 9. Design system and visual language

A glassmorphic dark UI over a living sky.

- **Glass surfaces**: two utility classes in `globals.css`, `.glass` and `.glass-strong`, provide the frosted `backdrop-filter` blur, translucent border, and layered shadow used by every card, panel, dialog, and dropdown.
- **Animated sky background** (`components/sky-background.tsx`): a fixed, `-z-10`, full-screen layer rendering a CSS gradient (`.sky-gradient`) that slowly pans, plus three blurred parallax "blobs" that float. Gradient stops are CSS custom properties (`--sky-from/via/to`, registered via `@property` so they can transition) set from `skyGradient(conditions)`. The background reacts to the current/first-reading weather condition and to day vs night, with a scrim overlay guaranteeing text contrast. All motion is disabled under `prefers-reduced-motion`.
- **Tokens**: shadcn's oklch token set in `globals.css` (`--background`, `--card`, `--primary`, chart colors, radius scale). Fonts are Geist Sans/Mono via `next/font`.
- **Motion**: `framer-motion` for entrance transitions (hero, record hero) and `AnimatePresence` for list add/remove on the records grid.
- **Charts**: `recharts` powers the per-record temperature-range chart.

## 10. Component inventory

```
components/
├── site-header.tsx / site-footer.tsx     # persistent shell (footer shows /meta)
├── providers.tsx                          # QueryClient + Units + Toaster
├── sky-background.tsx                     # animated weather background
├── unit-toggle.tsx                        # °C/°F switch
├── connection-indicator.tsx              # backend reachability via /health
├── weather-icon.tsx                       # condition → lucide icon
├── aqi-badge.tsx                          # AQI pill
├── date-range-fields.tsx                  # shared start/end date inputs
├── ui-states.tsx                          # EmptyState / ErrorState
├── save-record-dialog.tsx                 # create (reused on home + list)
├── delete-record-dialog.tsx              # confirm + delete mutation
├── home/
│   ├── home-view.tsx                      # search + results orchestration
│   ├── current-weather-card.tsx (+ skeleton)
│   └── forecast-strip.tsx (+ skeleton)
├── records/
│   ├── records-view.tsx                   # list + filters + create/delete
│   ├── record-card.tsx
│   ├── record-detail-view.tsx             # hero + tabbed detail
│   ├── edit-record-dialog.tsx             # update mutation
│   ├── temperature-chart.tsx              # recharts range chart
│   ├── briefing-panel.tsx                 # lazy AI briefing tab
│   ├── media-panel.tsx                    # videos + POIs tab
│   └── export-menu.tsx                    # multi-format download
└── ui/                                    # shadcn primitives (button, dialog, tabs, ...)
```

Each view follows the same shape: render `SkyBackground`, fetch with `useQuery`, and branch into skeleton (`isLoading`) → `ErrorState` (`isError`, with a retry that calls `refetch`) → `EmptyState` (no data) → content. `SaveRecordDialog` and `DeleteRecordDialog` are shared across home/list/detail so create and delete behave identically everywhere.

## 11. Key user flows

- **Search → save**: home holds a controlled `input`; submit commits it to `location`, which enables the current+forecast queries. The current weather card's "Save" button opens `SaveRecordDialog` prefilled with the resolved name; on success it invalidates `["records"]` and navigates to the new record (`navigateOnSuccess`).
- **Record detail tabs**: `Readings` (chart + per-day cards sorted by date, or an empty state explaining out-of-forecast-horizon ranges), `AI Briefing`, and `Media` are tabbed; briefing and media fetch lazily so their quota-constrained backend calls only fire when opened.
- **Export**: `export-menu.tsx` requests the export endpoint in `raw` mode, reads the `Response` as a blob, derives a filename from `Content-Disposition` (falling back to `record-<id>.<ext>`), and triggers a client-side `<a download>` click. Five formats: json, xml, csv, markdown, pdf.

## 12. Error, loading, and offline handling

- **Loading**: dedicated skeleton components per surface (cards, forecast strip, list grid, detail hero) rather than spinners, to preserve layout.
- **Errors**: `ErrorState` renders the `ApiError.message` and a retry button wired to the query's `refetch`. Mutation errors surface as `sonner` toasts. Because `apiFetch` converts a dead backend into a `network_error` `ApiError`, the UI degrades to a clear "can't reach the service" message instead of an unhandled rejection.
- **Connection awareness**: `connection-indicator.tsx` polls `/health` to show backend reachability in the header.
- **Empty states**: `EmptyState` (with contextual icon/title/description and an optional action) covers no-search-yet, no-records, no-matching-filters, and no-readings cases.

## 13. Configuration and environment

- **`NEXT_PUBLIC_API_BASE_URL`**: the single required env var, the backend origin. Because it is `NEXT_PUBLIC_`, it is inlined into the client bundle **at build time**, not read at runtime; the Docker image therefore bakes it via a build `ARG` (default `http://localhost:8000`, correct when the browser shares the host with the compose stack).
- Defaults to `http://localhost:8000` when unset, so local dev needs no `.env`.

## 14. Deployment

Multi-stage `Dockerfile` (`apps/web/Dockerfile`) on `node:22-alpine` with corepack/pnpm:

1. `deps` stage installs from the frozen lockfile (cached on lockfile hash).
2. `builder` stage compiles to the standalone bundle, baking `NEXT_PUBLIC_API_BASE_URL`.
3. `runner` stage copies only `public`, `.next/standalone`, and `.next/static`, runs as a non-root `nextjs` user, exposes `3000`, and starts `node server.js`.

The web service is wired into the repo-root `docker-compose.yml` alongside the API, Postgres, and Redis, so the full stack comes up together. Local dev outside Docker is `pnpm dev` in `apps/web/`.

## 15. Known constraints and decisions

- **TypeScript build errors are ignored** (`ignoreBuildErrors: true`), a v0 scaffold default. Type safety still holds in the editor and via `lib/types.ts`; this only prevents a type error from failing the production build at this assessment scope.
- **Images unoptimized**: avoids needing the Next image optimization server in the standalone container; acceptable since media thumbnails come from external URLs.
- **snake_case all the way through**: chosen so the API contract is literally the type definitions, at the cost of non-idiomatic JS casing.
- **Client-side rendering only for data**: no SSR/streaming of weather data. Simpler given the public, cache-friendly, no-auth backend, and it keeps all data access in one `fetch` gateway.
- **Dark-mode only**: the immersive sky design assumes a dark canvas; a light theme was not in scope.
- **Build-time API URL**: changing the backend origin requires a rebuild, an inherent consequence of using a `NEXT_PUBLIC_` value rather than runtime config.
