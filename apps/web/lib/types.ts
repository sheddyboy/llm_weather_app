// TypeScript interfaces matching the FastAPI backend contract.
// The API is snake_case; we keep snake_case here to mirror it exactly.

export interface ErrorEnvelope {
  error: { code: string; message: string }
}

export type ApiErrorCode =
  | "location_not_found"
  | "record_not_found"
  | "invalid_date_range"
  | "weather_provider_error"
  | "external_api_quota_exceeded"
  | "internal_error"
  | "http_error"
  | "network_error"
  | (string & {})

export interface LocationRead {
  id: string
  query_text: string
  resolved_name: string
  latitude: number | string
  longitude: number | string
  country: string | null
  created_at: string
}

export interface DailyReadingRead {
  id: string
  date: string // YYYY-MM-DD
  temp_min: number | string // °C
  temp_max: number | string // °C
  conditions: string
  aqi: number | null // 1..5 or null
}

export interface WeatherRecordRead {
  id: string
  location: LocationRead
  start_date: string
  end_date: string
  created_at: string
  updated_at: string
  readings: DailyReadingRead[]
}

export interface CurrentWeather {
  conditions: string
  temp: number | null
  temp_min: number | null
  temp_max: number | null
  humidity: number | null
  wind_speed: number | null
}

export interface CurrentWeatherResponse {
  location: LocationRead
  current: CurrentWeather
}

export interface ForecastDay {
  date: string
  temp_min: number | string | null
  temp_max: number | string | null
  conditions: string
}

export interface ForecastResponse {
  location: LocationRead
  days: ForecastDay[]
}

export interface MetaResponse {
  name: string
  description: string
}

export interface HealthResponse {
  status: string
}

export interface BriefingResponse {
  summary: string
  clothing_suggestion: string
  aqi_note: string
}

export interface VideoItem {
  video_id: string
  title: string
  channel: string | null
  url: string
  thumbnail: string | null
}

export interface PointOfInterest {
  name: string
  address: string | null
  rating: number | null
  types: string[]
}

export interface MediaResponse {
  location: LocationRead
  videos: VideoItem[]
  points_of_interest: PointOfInterest[]
}

export interface CreateRecordInput {
  location: string
  start_date: string
  end_date: string
}

export interface UpdateRecordInput {
  location?: string
  start_date?: string
  end_date?: string
}

export type ExportFormat = "json" | "xml" | "csv" | "markdown" | "pdf"
