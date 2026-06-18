import type {
  BriefingResponse,
  CreateRecordInput,
  CurrentWeatherResponse,
  ExportFormat,
  ForecastResponse,
  HealthResponse,
  MediaResponse,
  MetaResponse,
  UpdateRecordInput,
  WeatherRecordRead,
} from "./types"

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "")

/**
 * Typed error thrown by the API layer. Carries the backend error `code`,
 * a human-friendly `message`, and the HTTP `status`.
 */
export class ApiError extends Error {
  code: string
  status: number

  constructor(message: string, code: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.code = code
    this.status = status
  }
}

function isErrorEnvelope(value: unknown): value is { error: { code: string; message: string } } {
  if (!value || typeof value !== "object") return false
  const err = (value as Record<string, unknown>).error
  if (!err || typeof err !== "object") return false
  const e = err as Record<string, unknown>
  return typeof e.code === "string" && typeof e.message === "string"
}

interface ApiFetchOptions extends RequestInit {
  /** When true, returns the raw Response instead of parsed JSON (used for blob exports). */
  raw?: boolean
}

async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { raw, headers, ...rest } = options
  const url = `${API_BASE_URL}${path}`

  let res: Response
  try {
    res = await fetch(url, {
      ...rest,
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
    })
  } catch {
    throw new ApiError(
      `Could not reach the weather service at ${API_BASE_URL}. Make sure the backend is running and CORS is configured.`,
      "network_error",
      0,
    )
  }

  if (!res.ok) {
    let code = "http_error"
    let message = `Request failed with status ${res.status}.`
    try {
      const body = await res.json()
      if (isErrorEnvelope(body)) {
        code = body.error.code
        message = body.error.message
      }
    } catch {
      // Body wasn't JSON / envelope shaped — keep generic message.
    }
    throw new ApiError(message, code, res.status)
  }

  if (raw) {
    return res as unknown as T
  }

  if (res.status === 204) {
    return undefined as T
  }

  return (await res.json()) as T
}

function buildQuery(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, value)
  }
  const str = search.toString()
  return str ? `?${str}` : ""
}

export const api = {
  health: () => apiFetch<HealthResponse>("/health"),

  meta: () => apiFetch<MetaResponse>("/meta"),

  currentWeather: (location: string) =>
    apiFetch<CurrentWeatherResponse>(`/weather/current${buildQuery({ location })}`),

  forecast: (location: string) => apiFetch<ForecastResponse>(`/weather/forecast${buildQuery({ location })}`),

  createRecord: (input: CreateRecordInput) =>
    apiFetch<WeatherRecordRead>("/records", {
      method: "POST",
      body: JSON.stringify(input),
    }),

  listRecords: (filters: { location_id?: string; start_date?: string; end_date?: string } = {}) =>
    apiFetch<WeatherRecordRead[]>(`/records${buildQuery(filters)}`),

  getRecord: (id: string) => apiFetch<WeatherRecordRead>(`/records/${id}`),

  updateRecord: (id: string, input: UpdateRecordInput) =>
    apiFetch<WeatherRecordRead>(`/records/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),

  deleteRecord: (id: string) =>
    apiFetch<void>(`/records/${id}`, {
      method: "DELETE",
    }),

  briefing: (id: string) => apiFetch<BriefingResponse>(`/records/${id}/briefing`),

  media: (id: string) => apiFetch<MediaResponse>(`/records/${id}/media`),

  exportUrl: (id: string, format: ExportFormat) => `${API_BASE_URL}/records/${id}/export${buildQuery({ format })}`,

  exportRecord: (id: string, format: ExportFormat) =>
    apiFetch<Response>(`/records/${id}/export${buildQuery({ format })}`, {
      raw: true,
      headers: {},
    }),
}
