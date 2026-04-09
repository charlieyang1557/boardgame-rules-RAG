# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + frontend static files
FROM python:3.11-slim AS runtime
WORKDIR /app

# Install torch CPU-only first (saves ~1.5GB vs full torch)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install Python deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy backend code
COPY api/ api/
COPY cache/ cache/
COPY conversation/ conversation/
COPY evaluation/ evaluation/
COPY generation/ generation/
COPY ingestion/ ingestion/
COPY query_logging/ query_logging/
COPY retrieval/ retrieval/
COPY routing/ routing/
COPY verification/ verification/

# Create logs dir
RUN mkdir -p logs

# Copy BM25 pickles (required at runtime)
COPY ingestion/cache/ ingestion/cache/

# Copy frontend build output from stage 1
COPY --from=frontend-build /app/frontend/dist frontend/dist

# Download cross-encoder model at build time (not at startup)
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

ENV PORT=8000
EXPOSE 8000
CMD uvicorn api.main:app --host 0.0.0.0 --port $PORT
