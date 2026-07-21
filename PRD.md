s updated engineering specification optimizes the architecture for a zero-trust local environment. By shifting to a hardened, single-container setup, you drastically reduce the attack surface while keeping maintenance as simple as copying a file.

## 1. Security & Maintenance Strategy

* **Single-Container Monolith:** Serving the compiled React SPA directly through FastAPI eliminates the need for a separate web server container or complex internal networking. You only maintain and secure one image.
* **Principle of Least Privilege:** The container runs as an unprivileged user, drops all Linux kernel capabilities, and blocks privilege escalation. This neutralizes the majority of container escape vulnerabilities (such as CVE-2024-21626).
* **Immutable Execution:** The container's root filesystem is mounted as strictly read-only. This prevents malicious scripts or runaway processes from modifying the application code at runtime.

## 2. Hardened Multi-Stage `Dockerfile`

This Dockerfile uses a multi-stage build to compile the frontend, guaranteeing that all Node.js build tools are stripped from the final production image. It creates a dedicated user and ensures all execution happens without root access.

```dockerfile
# Stage 1: Frontend Builder
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
# Optional: Point to local npm registry if operating fully offline
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Production Backend
FROM python:3.11-slim
WORKDIR /app

# Create a dedicated, non-root system user and group
RUN groupadd -r cataloggrp && useradd -r -g cataloggrp catalogusr

# Install dependencies
COPY backend/requirements.txt .
# Optional: Append '-i http://local-pypi-mirror/simple' for offline builds
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python backend and pre-compiled React static files
COPY backend/ ./
COPY --from=frontend-builder /app/dist ./static

# Prepare the data directory for the SQLite database mount
# This directory MUST be owned by the non-root user to allow writing SQLite journal files
RUN mkdir -p /app/data && chown -R catalogusr:cataloggrp /app

# Switch to the restricted user before execution
USER catalogusr

# Listen on a high port (capabilities drop prevents binding to ports < 1024)
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

```

## 3. Secure `docker-compose.yml`

This configuration locks down the runtime environment. By enforcing a read-only filesystem, any temporary file writes required by Python or FastAPI must happen in an isolated memory space (`/tmp`), and the database state is safely externalized to the host.

```yaml
services:
  catalog:
    build: .
    image: local-ai-catalog:latest
    container_name: local_ai_catalog
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      # Stateful DB mount: Externalizes the database to the host machine
      - ./data:/app/data
      # Optional: Read-only mount to shared network storage to allow the API 
      # to verify file existence before returning paths to the user
      - /mnt/network_shares/ai_assets:/mnt/assets:ro
    environment:
      - DATABASE_URL=sqlite:////app/data/catalog.db
      - ASSET_SCAN_PATH=/mnt/assets
    
    # --- Security Hardening Directives ---
    
    # Prevents modification of the container's internal filesystem
    read_only: true
    
    # Provides an ephemeral, writable space in memory for FastAPI temp files
    tmpfs:
      - /tmp
      
    # Drops all default Linux capabilities (e.g., chown, raw network binding)
    cap_drop:
      - ALL
      
    # Prevents any process from gaining new privileges via setuid/setgid binaries
    security_opt:
      - no-new-privileges:true

```

## 4. Operational Maintenance & Backups

This setup is designed for near-zero operational overhead:

* **Database Backups:** Because the database is a single SQLite file (`catalog.db`) residing in the mounted `./data` directory on the host machine, backing it up requires no database administration tools. You can simply schedule an `rsync` task over SSH to push the directory directly to a local NAS or secondary drive.
* **Offline Updates:** The architecture expects no outbound internet calls. When iterating on the tool, you pull code from your local repository and rebuild the image against your internal package mirrors.
* **Disaster Recovery:** If the application host fails or the database becomes corrupted, restoring from the last NAS sync and restarting the Docker container instantly recovers the entire catalog.
