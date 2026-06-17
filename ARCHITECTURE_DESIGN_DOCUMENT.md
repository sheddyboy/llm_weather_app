# Weather App Backend — Architecture Design Document

Engineering reference for the backend portion of the PM Accelerator AI Engineer Intern weather app assessment (full stack / dual role track). The frontend is out of scope for this document, it will be generated separately via a v0 prompt derived from this backend's API surface.

## 1. Scope

**In scope**: FastAPI backend, Postgres persistence, OpenWeatherMap integration, YouTube and Google Places enrichment, OpenAI-powered briefing generation, caching, error handling, export, testing, deployment.

**Explicitly out of scope**: authentication and per-user data segregation. The assessment brief states row-level security is not required, anyone can read any stored record. Adding auth would be unscoped work against a stated requirement, not a missing feature.

## 2. Tech stack

| Layer | Choice | Version (as of build time) |
|---|---|---|
| Language | Python | 3.12 |
| Package manager | uv | self-updating, no pin needed |
| Web framework | FastAPI | 0.137.x |
| Validation/config | Pydantic v2 + pydantic-settings | 2.13.x / 2.14.x |
| ORM | SQLAlchemy (async, 2.0 style) | 2.0.51 stable (not the 2.1 beta) |
| DB driver | asyncpg | latest |
| Migrations | Alembic | latest |
| Logging | Loguru | latest |
| HTTP client | httpx | latest |
| LLM orchestration | LangChain v1 (`langchain`, `langchain-openai`) | 1.x, avoid `langchain-classic` |
| LLM provider | OpenAI | gpt-4o-mini for the briefing |
| Cache (local dev) | cachetools (in-memory TTL) | latest |
| Cache (deployment) | Redis via redis.asyncio | latest |
| Testing | pytest, pytest-asyncio, httpx AsyncClient | latest |

## 3. System architecture

Client (Next.js, built later) → FastAPI backend → Postgres + external providers.

Inside the backend, routers handle HTTP concerns only and delegate to services. Services contain the actual logic (calling providers, applying cache-first checks, assembling responses) and call repositories for persistence. Repositories are the only layer that touches SQLAlchemy sessions directly.

```
routers/  ->  services/  ->  repositories/  ->  Postgres
                  |
                  -> cache layer -> external providers (OpenWeatherMap, YouTube, Places, OpenAI)
```

Geocoding is the one exception to "services call external providers through cache": resolved locations are persisted permanently in the `locations` table rather than held in a TTL cache, since a location string resolving to coordinates essentially never changes. This doubles as the foreign key target for records and as a permanent geocoding cache.

## 4. Database schema

Three tables, normalized rather than JSON-blob, so CRUD operations map to real relational operations.

```
locations
  id            uuid pk
  query_text    text          -- original user input, e.g. "Hatfield, UK"
  resolved_name text
  latitude      numeric
  longitude     numeric
  country       text
  created_at    timestamptz

weather_records
  id            uuid pk
  location_id   uuid fk -> locations.id
  start_date    date
  end_date      date
  created_at    timestamptz
  updated_at    timestamptz

daily_readings
  id            uuid pk
  record_id     uuid fk -> weather_records.id
  date          date
  temp_min      numeric
  temp_max      numeric
  conditions    text
  aqi           integer nullable
```

Indexes: `weather_records.location_id`, `daily_readings.record_id`, and a composite on `(record_id, date)` for the export and briefing queries that pull a record's full reading set in date order.

## 5. API surface

| Endpoint | Purpose |
|---|---|
| `GET /weather/current` | Live current weather for a location, not persisted |
| `GET /weather/forecast` | Live 5-day forecast, not persisted |
| `POST /records` | Create: location + date range, resolves and validates both, fetches and stores readings |
| `GET /records` | List stored records, with optional location/date filters |
| `GET /records/{id}` | Read one record with its readings |
| `PATCH /records/{id}` | Update date range or location, re-validates and re-fetches affected readings |
| `DELETE /records/{id}` | Delete a record and its readings |
| `GET /records/{id}/export?format=` | Export as json, xml, csv, pdf, or markdown |
| `GET /records/{id}/media` | YouTube videos + Google Places points of interest for the record's location |
| `GET /records/{id}/briefing` | OpenAI-generated narrative summary, clothing suggestion, AQI note |
| `GET /meta` | Name and PM Accelerator description, consumed by the frontend footer |

## 6. External integrations

**OpenWeatherMap**: Free Access APIs only, current weather, 5-day/3-hour forecast, geocoding, air pollution. Deliberately avoiding One Call API 3.0 since it requires a card on file even on its free tier, not worth the friction for this scope. 1M calls/month, 60/minute, no card needed.

**YouTube Data API v3**: `search.list` to find videos about the resolved location name. This is the tightest constraint in the whole system, a single search costs 100 of the default 10,000 daily quota units, so roughly 100 searches/day before requests start failing. This is the main reason caching exists at all for this integration.

**Google Places API**: Nearby Search (or Text Search) against the resolved coordinates to surface points of interest, plus Place Details where richer info is worth the extra call. Requires a billing account on file per Google's March 2025 pricing change, each SKU carries its own free monthly cap rather than the old pooled $200 credit. Design should degrade gracefully (omit points of interest, don't fail the whole `/media` response) if billing isn't configured or the cap is hit.

**OpenAI via LangChain v1**: `ChatOpenAI(model="gpt-4o-mini").with_structured_output(BriefingResponse)`, a single structured call, not an agent loop, since the briefing only needs to transform data that's already been fetched. v1's structured output is integrated into the main model call rather than triggering a hidden second call the way pre-1.0 LangChain did.

## 7. Caching strategy

`CacheBackend` abstract interface with async `get`/`set`/`delete`, two implementations:

- `InMemoryCache` (cachetools TTLCache, wrapped async-safe) for local development now, zero extra infra.
- `RedisCache` (redis.asyncio) for deployment, swapped in via a settings flag once Docker is in the picture.

Calling code only ever talks to the interface, never to a concrete backend.

| Data | TTL | Reasoning |
|---|---|---|
| Current weather | 10-15 min | Conditions don't change faster than this |
| Forecast / air pollution | 30-60 min | Same reasoning, slightly longer horizon |
| YouTube search results | 7-30 days | Quota-driven, results barely change |
| Places results | 7-14 days | Billing-driven, points of interest are stable |
| LLM briefing | Until the underlying record changes | Cost-driven, keyed by a hash of the record's weather + AQI data |
| Geocoding | Not cached, stored permanently | Lives in the `locations` table instead |

## 8. Error handling

Custom exceptions mapped to consistent JSON error responses via FastAPI exception handlers, rather than letting raw provider exceptions leak through:

- `LocationNotFoundError` (no geocoding match, or fuzzy match below confidence threshold)
- `InvalidDateRangeError` (end before start, range too large, dates in the past where that's not meaningful)
- `WeatherProviderError` (OpenWeatherMap failure)
- `ExternalAPIQuotaExceededError` (YouTube or Places quota/billing limit hit, response degrades rather than fails)

## 9. Testing strategy

A dedicated Postgres test schema (`weatherapp_test`) on the same local instance, separate from the dev database. Alembic migrations run against it once per test session via a session-scoped fixture. Each test runs inside a transaction that's rolled back afterward, so tests stay isolated and fast without rebuilding schema state per test.

External calls (OpenWeatherMap, YouTube, Places, OpenAI) are mocked at the HTTP layer, not hit live, both to avoid burning real quota and to keep test runs deterministic and free.

## 10. Deployment

Local now: local Postgres, in-memory cache, secrets in `.env`. `DATABASE_URL` and `REDIS_URL` read from environment variables from day one specifically so the swap to Docker later is a config change, not a refactor. Deployment later: docker-compose bringing up the API, Postgres, and Redis together.

## 11. Project structure

```
app/
├── main.py
├── core/
│   ├── config.py
│   ├── database.py
│   ├── cache.py            # CacheBackend + implementations
│   └── logging.py
├── models/                  # SQLAlchemy models
├── schemas/                  # Pydantic request/response models
├── routers/
│   ├── weather.py
│   ├── records.py
│   ├── export.py
│   └── meta.py
├── services/
│   ├── weather_provider.py
│   ├── geocoding.py
│   ├── youtube.py
│   ├── places.py
│   ├── briefing_service.py
│   └── export_service.py
├── repositories/
│   └── weather_repository.py
└── exceptions.py
alembic/
tests/
pyproject.toml
uv.lock
Dockerfile
docker-compose.yml
README.md
```

## 12. Known constraints

- YouTube quota (100 units/search, 10,000/day default) is the most likely thing to break under repeated testing, mitigated by the 7-30 day cache TTL.
- Google Places requires billing enabled on the Cloud project, mitigated by graceful degradation in `/records/{id}/media` if it's unavailable.
- No auth, by design, per the brief's explicit statement that row-level security isn't needed.
