# syntax=docker/dockerfile:1

# Stage 1: Frontend Builder — compiles the React SPA. All Node tooling is
# discarded after this stage, keeping it out of the final image.
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
# Optional: point npm at a local registry for fully-offline builds:
#   RUN npm ci --registry http://local-npm-mirror/
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Production Backend
FROM python:3.11-slim
WORKDIR /app

# Create a dedicated, non-root system user and group.
RUN groupadd -r cataloggrp && useradd -r -g cataloggrp catalogusr

# Install Python dependencies.
COPY backend/requirements.txt .
# Optional: append '-i http://local-pypi-mirror/simple' for offline builds.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Python backend and the pre-compiled React static files.
COPY backend/ ./
COPY --from=frontend-builder /app/dist ./static

# Prepare the data directory for the SQLite database mount. It MUST be owned by
# the non-root user so SQLite can write its database and WAL/journal files.
RUN mkdir -p /app/data && chown -R catalogusr:cataloggrp /app

# Switch to the restricted user before execution.
USER catalogusr

# Listen on a high port (dropped capabilities forbid binding ports < 1024).
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
