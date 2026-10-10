# OfferProof: one container serves the API and the built frontend (same origin, no CORS).

# ---- stage 1: build the frontend (type-check + vite build)
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- stage 2: the API, with the built frontend next to it
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/ backend/
# app/main.py looks for ../../frontend/dist relative to itself, i.e. /app/frontend/dist
COPY --from=web /web/dist frontend/dist

# the search cache is written at runtime; the app user must be able to write it
RUN useradd --create-home --uid 10001 app && mkdir -p backend/cache && chown -R app:app backend/cache
USER app
WORKDIR /app/backend

# Safe defaults for a public site: recorded searches only, and no live searches unless the host sets a limit.
# The SerpApi key is NEVER baked in: set SERPAPI_API_KEY in the host's environment.
ENV MODE=cached LIVE_DAILY_CAP=0 SEARCH_TIMEOUT_SECONDS=8

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
