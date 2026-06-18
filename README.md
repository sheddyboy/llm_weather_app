# Weather App

A weather application built for the PM Accelerator AI Engineer Intern assessment (full-stack / dual-role track). This repository is a monorepo: a FastAPI backend that integrates OpenWeatherMap, YouTube, Google Places, and OpenAI, backed by Postgres; and a Next.js frontend that is generated separately later.

## Layout

```
weather_app/
├── ARCHITECTURE_DESIGN_DOCUMENT.md   # source of truth: stack, schema, API, caching, errors
├── docker-compose.yml                # deployment stack: api + postgres + redis
├── apps/
│   ├── api/                          # the backend (everything in the architecture doc)
│   │   └── Dockerfile
│   └── web/                          # Next.js frontend, generated later via a separate v0 prompt
```

The backend lives entirely in [apps/api/](apps/api/). The frontend ([apps/web/](apps/web/)) is **out of scope** for this work and is produced later from a v0 prompt derived from the backend's API surface; do not build it here.

## Tech stack

Python 3.12 · FastAPI · async SQLAlchemy 2.0 + asyncpg · Alembic · Pydantic v2 · Loguru · httpx · LangChain v1 + OpenAI (`gpt-4o-mini`) · cachetools (local) / Redis (deployment) · fpdf2 (PDF export) · pytest. Dependencies are managed with [uv](https://docs.astral.sh/uv/).

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

Brings up the API, Postgres, and Redis together; migrations are applied automatically on startup.

```bash
# 1. Provide API keys (optional but needed for the external integrations):
cp apps/api/.env.example apps/api/.env   # then fill in the keys

# 2. Build and start the stack:
docker compose up --build
```

The API is then available at <http://localhost:8000> (docs at <http://localhost:8000/docs>). The compose file overrides `DATABASE_URL`, `CACHE_BACKEND=redis`, and `REDIS_URL` to point at the bundled services; everything else (the API keys) is read from `apps/api/.env` if present.

## Running locally (without Docker)

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
uv run uvicorn app.main:app --reload
```

`CACHE_BACKEND` defaults to `memory` locally (no Redis needed); set it to `redis` to use a Redis backend.

## Testing

External calls (OpenWeatherMap, YouTube, Places, OpenAI) are mocked at the HTTP layer, and tests run against the dedicated `weatherapp_test` database, each inside a rolled-back transaction (ARCHITECTURE §9). From `apps/api/`:

```bash
uv run pytest          # full suite
uv run ruff check      # lint
```

## Documentation

See [ARCHITECTURE_DESIGN_DOCUMENT.md](ARCHITECTURE_DESIGN_DOCUMENT.md) for the complete engineering reference (tech stack and versions, database schema, API surface, external integrations, caching strategy, error handling, testing, and deployment).
