# ─────────────────────────────────────────────
# Stage 1: Build frontend
# ─────────────────────────────────────────────

FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ─────────────────────────────────────────────
# Stage 2: Python application
# ─────────────────────────────────────────────

FROM python:3.12-slim AS backend

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Python dependencies first.
# Keeping this separate from the source code makes Docker's
# layer cache much more effective.
COPY backend/pyproject.toml backend/uv.lock ./

RUN uv sync --frozen --no-dev

# Copy backend source
COPY backend/app ./app

# Copy compiled frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# SQLite/database/cache directory
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
