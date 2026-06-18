# Weather App

A weather application built for the PM Accelerator AI Engineer Intern assessment (full-stack / dual-role track). This repository is a monorepo: a FastAPI backend that integrates OpenWeatherMap, YouTube, Google Places, and OpenAI, backed by Postgres; and a Next.js frontend that consumes the backend's API.

## Layout

```
weather_app/
├── ARCHITECTURE_DESIGN_DOCUMENT.md   # source of truth: stack, schema, API, caching, errors
├── docker-compose.yml                # full stack: web + api + postgres + redis
├── apps/
│   ├── api/                          # FastAPI backend (everything in the architecture doc)
│   │   └── Dockerfile
│   └── web/                          # Next.js frontend (consumes the API)
│       └── Dockerfile
```

The backend lives in [apps/api/](apps/api/) and the frontend in [apps/web/](apps/web/). The fastest way to run both together is Docker (below).

## Tech stack

**Backend:** Python 3.12 · FastAPI · async SQLAlchemy 2.0 + asyncpg · Alembic · Pydantic v2 · Loguru · httpx · LangChain v1 + OpenAI (`gpt-4o-mini`) · cachetools (local) / Redis (deployment) · fpdf2 (PDF export) · pytest. Dependencies are managed with [uv](https://docs.astral.sh/uv/).

**Frontend:** Next.js 16 (React 19) · TypeScript · Tailwind CSS · shadcn/ui · TanStack Query. Dependencies are managed with [pnpm](https://pnpm.io/).

## API surface

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness probe |
| `GET /meta` | App name + PM Accelerator description (frontend footer) |
| `GET /weather/current` · `GET /weather/forecast` | Live lookups, not persisted |
| `POST /records` · `GET /records` · `GET /records/{id}` · `PATCH /records/{id}` · `DELETE /records/{id}` | Record CRUD |
| `GET /records/{id}/export?format=` | Export as json, xml, csv, markdown, or pdf |
| `GET /records/{id}/media` | YouTube videos + Google Places points of interest |
| `GET /records/{id}/briefing` | OpenAI-generated narrative briefing |

Interactive docs are served at `/docs` once the app is running.

## Running with Docker (recommended)

Brings up the whole application together: the Next.js **web** frontend, the FastAPI **api**, **Postgres**, and **Redis**. Database migrations are applied automatically on API startup.

```bash
# 1. Provide API keys (optional, but needed for the external integrations):
cp apps/api/.env.example apps/api/.env   # then fill in the keys

# 2. Build and start the full stack:
docker compose up --build
```

Once it's up:

| Service | URL |
|---|---|
| Web frontend | <http://localhost:3000> |
| API | <http://localhost:8000> |
| API docs (Swagger UI) | <http://localhost:8000/docs> |

The compose file overrides `DATABASE_URL`, `CACHE_BACKEND=redis`, and `REDIS_URL` so the API points at the bundled Postgres and Redis services; everything else (the API keys) is read from `apps/api/.env` if present. The web container is built with `NEXT_PUBLIC_API_BASE_URL` defaulting to `http://localhost:8000`, which the browser uses to reach the API; override it via the same env var if you expose the API elsewhere.

Stop and remove the stack with `docker compose down` (add `-v` to also drop the Postgres volume and start from a clean database).

## Running locally (without Docker)

### Backend

Requires a local Postgres instance and [uv](https://docs.astral.sh/uv/).

```bash
cd apps/api

# 1. Configure environment:
cp .env.example .env                     # fill in API keys; defaults point at local Postgres

# 2. Create the dev and test databases (defaults: weatherapp / weatherapp_test):
createdb weatherapp
createdb weatherapp_test

# 3. Install dependencies and apply migrations:
uv sync
uv run alembic upgrade head

# 4. Run the API:
uv run uvicorn app.main:app --reload     # serves on http://localhost:8000
```

`CACHE_BACKEND` defaults to `memory` locally (no Redis needed); set it to `redis` to use a Redis backend.

### Frontend

Requires Node.js 20+ and [pnpm](https://pnpm.io/) (`corepack enable` will provision the pinned version). Run the backend first so the API is reachable.

```bash
cd apps/web

# 1. Install dependencies:
pnpm install

# 2. (Optional) point the app at a non-default API:
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local

# 3. Run the dev server:
pnpm dev                                  # serves on http://localhost:3000
```

The frontend defaults to `http://localhost:8000` for the API, and the backend allows the `http://localhost:3000` origin via CORS out of the box, so no extra configuration is needed for the standard local setup.

## Testing

External calls (OpenWeatherMap, YouTube, Places, OpenAI) are mocked at the HTTP layer, and tests run against the dedicated `weatherapp_test` database, each inside a rolled-back transaction (ARCHITECTURE §9). From `apps/api/`:

```bash
uv run pytest          # full suite
uv run ruff check      # lint
```

## Documentation

See [ARCHITECTURE_DESIGN_DOCUMENT.md](ARCHITECTURE_DESIGN_DOCUMENT.md) for the complete engineering reference (tech stack and versions, database schema, API surface, external integrations, caching strategy, error handling, testing, and deployment).
