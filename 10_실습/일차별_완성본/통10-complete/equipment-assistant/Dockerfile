FROM node:22.18-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app
RUN pip install --no-cache-dir uv==0.12.5
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra documents --extra evaluation
COPY backend/ backend/
COPY mcp_server/ mcp_server/
COPY scripts/ scripts/
COPY supabase/migrations/ supabase/migrations/
COPY config.yaml mapping.json rules.json ./
COPY ontology/ ontology/
COPY data/generated/ data/generated/
COPY data/documents/ data/documents/
ARG CACHE_RAG_MODELS=false
RUN if [ "$CACHE_RAG_MODELS" = "true" ]; then ALLOW_MODEL_DOWNLOADS=true .venv/bin/python scripts/cache_models.py; fi
COPY --from=frontend /build/dist ./frontend/dist
ENV PYTHONUNBUFFERED=1 ALLOW_MODEL_CALLS=false ALLOW_MODEL_DOWNLOADS=false PORT=8080
EXPOSE 8080
CMD [".venv/bin/python", "scripts/serve.py"]
