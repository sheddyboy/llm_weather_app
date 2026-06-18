# Weather App API image, built with uv (ARCHITECTURE §10).
#
# Uses the official uv base image (Python 3.12) and installs dependencies in a
# separate, cache-friendly layer before copying the source, so day-to-day code
# changes do not re-resolve the lockfile. The container runs the FastAPI app with
# uvicorn; database migrations are applied by the compose `command` at startup.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Byte-compile installed packages for faster cold starts; copy (not symlink) into
# the venv since the build cache mount lives on a different filesystem layer.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install only third-party dependencies first (no project, no dev group); this
# layer is reused as long as pyproject.toml / uv.lock are unchanged.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Now bring in the application source and install the project itself.
COPY . .
RUN uv sync --frozen --no-dev

# Put the project's virtualenv on PATH so `uvicorn`/`alembic` resolve directly.
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
