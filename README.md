# Weather App

A weather application built for the PM Accelerator AI Engineer Intern assessment (full-stack / dual-role track). This repository is a monorepo: a FastAPI backend that integrates OpenWeatherMap, YouTube, Google Places, and OpenAI, backed by Postgres; and a Next.js frontend that is generated separately later.

## Layout

```
weather_app/
├── ARCHITECTURE_DESIGN_DOCUMENT.md   # source of truth: stack, schema, API, caching, errors
├── apps/
│   ├── api/                          # the backend (everything in the architecture doc)
│   └── web/                          # Next.js frontend, generated later via a separate v0 prompt
└── docker-compose.yml                # added later (deployment)
```

The backend lives entirely in [apps/api/](apps/api/). The frontend ([apps/web/](apps/web/)) is **out of scope** for this work and is produced later from a v0 prompt derived from the backend's API surface; do not build it here.

## Status

Bootstrapped. The backend is built incrementally. Full setup and run instructions are finalized once the backend is complete.

## Documentation

See [ARCHITECTURE_DESIGN_DOCUMENT.md](ARCHITECTURE_DESIGN_DOCUMENT.md) for the complete engineering reference (tech stack and versions, database schema, API surface, external integrations, caching strategy, error handling, testing, and deployment).
