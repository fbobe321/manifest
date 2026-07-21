# Manifest — Product & Engineering Specification

**Manifest** is a self-hosted repository for **AI models and datasets**. Users
create a repository, write a Markdown card, tag it, and list its files as
**external links** — the catalog stores the metadata and the link, never the
bytes. It ships as a single hardened container (a compiled React SPA served by
FastAPI over SQLite) and is fully operable from an **agent-native CLI**.

This spec optimizes the architecture for a zero-trust local environment. By
shipping a hardened, single-container setup, you drastically reduce the attack
surface while keeping maintenance as simple as copying a file.

> **Change from the original draft:** the first draft specified a filesystem
> *scanner* over a mounted asset share (`ASSET_SCAN_PATH`,
> `/mnt/network_shares`). Manifest instead uses a **user-driven catalog model**:
> people create repositories and add file links; there is no scanning. The
> scan-related volume and env var were removed from `docker-compose.yml`. All
> security-hardening directives and the single-container design are unchanged.
> See the [Changelog](#11-changelog) for the full delta.

---

## 1. Product Overview

- **Repositories** are `owner/name` (e.g. `openai/whisper-large-v3`) and are one
  of two types: **model** or **dataset**.
- Each repository has a **Markdown card**, a short description, and metadata:
  `task` (pipeline tag), `library`, `license`, and free-form `tags`.
- **Files are external links.** A file record is `{filename, url, size}`. The
  actual bytes live wherever the owner hosts them (object store, mirror, another
  server); Manifest just records and links to them.
- **Users** own repositories. Identity is intentionally lightweight for a local
  zero-trust tool: no passwords — a username is created on first use and
  remembered client-side.
- **Engagement:** repositories track `likes` and `downloads`.
- **Discovery:** faceted browse and full-text search over tasks, libraries,
  licenses, and tags; sortable by trending / recent / downloads / likes / name.

## 2. Architecture

| Layer     | Technology                                                      |
|-----------|-----------------------------------------------------------------|
| Frontend  | React 18 + Vite + React Router, compiled to static assets       |
| Backend   | FastAPI + SQLAlchemy 2; serves the JSON API **and** the SPA     |
| Storage   | SQLite — a single file on the mounted `./data` volume           |
| CLI       | Python + Click (`manifest`), talks to the REST API              |
| Delivery  | One multi-stage Docker image: non-root, read-only root FS       |

The SPA is compiled in a Node build stage and copied into the Python image as
static files, so the final container carries no Node tooling. FastAPI serves the
API under `/api` and the SPA (with client-side routing fallback) for every other
path. In development, the Vite dev server proxies `/api` to the backend, so the
browser sees a single origin (no CORS).

## 3. Security & Maintenance Strategy

* **Single-Container Monolith:** Serving the compiled React SPA directly through
  FastAPI eliminates the need for a separate web server container or complex
  internal networking. You maintain and secure one image.
* **Principle of Least Privilege:** The container runs as an unprivileged user,
  drops all Linux kernel capabilities, and blocks privilege escalation. This
  neutralizes the majority of container-escape vulnerabilities (such as
  CVE-2024-21626).
* **Immutable Execution:** The container's root filesystem is mounted strictly
  read-only. The only writable locations are the mounted `./data` volume
  (SQLite + WAL) and an in-memory `tmpfs` at `/tmp`. This prevents malicious or
  runaway processes from modifying application code at runtime.
* **No outbound calls:** The application makes no outbound internet requests;
  file links are stored and surfaced to the user, never fetched server-side.

## 4. Data Model

```
User            (id, username·unique, full_name, bio, created_at)
  └─ Repository (id, repo_id="owner/name"·unique, owner_id→User, owner_username,
                 name, repo_type∈{model,dataset}, description, readme·markdown,
                 license, task, library, tags_csv, likes, downloads,
                 created_at, updated_at)
       └─ RepoFile (id, repo_pk→Repository, filename, url, size_bytes,
                    created_at)   # unique(repo, filename)
```

`num_files` and `total_size_bytes` are derived from a repository's files.

## 5. REST API

Base path `/api`. All responses are JSON.

| Method & path | Purpose |
|---|---|
| `GET /health` · `GET /stats` · `GET /facets[?repo_type=]` | Liveness · counts · filter facets |
| `POST /users` · `GET /users` · `GET /users/{username}` | Create (idempotent) · list · profile+repos |
| `GET /repos` | List/search (`q, repo_type, owner, task, library, license, tag, sort, limit, offset`) |
| `POST /repos` | Create a repository |
| `GET /repos/{owner}/{name}` | Detail (card + files) |
| `PUT /repos/{owner}/{name}` | Update fields |
| `DELETE /repos/{owner}/{name}` | Delete |
| `POST /repos/{owner}/{name}/like` | Increment likes |
| `POST /repos/{owner}/{name}/download` | Register a download |
| `POST /repos/{owner}/{name}/files` | Add a file (external URL) |
| `DELETE /repos/{owner}/{name}/files/{id}` | Remove a file |

Interactive docs are served at `/api/docs`.

## 6. Agent-Native CLI

`manifest` (in [`cli/`](./cli)) exposes **every** site action so an automated
agent can operate Manifest without a browser. It follows the
[CLI-Anything](https://github.com/HKUDS/CLI-Anything) conventions:

- **Hierarchical commands:** `manifest <group> <action>` (`repo`, `file`,
  `user`, `cfg`, plus top-level `health/stats/facets/login/whoami/repl`).
- **Universal `--json` flag** for structured, machine-readable output; rich
  human tables otherwise.
- **`--help` discovery** at every level, plus a [`SKILL.md`](./cli/SKILL.md)
  agent reference.
- **Interactive `repl`** with persistent session state (`:as`, `:json on/off`).
- **Config resolution:** flag → env (`MANIFEST_URL`, `MANIFEST_USER`) →
  `~/.manifest/config.json` → defaults. Non-zero exit on any API error.

```bash
pip install -e cli/
manifest login alice --name "Alice"
manifest repo create alice/my-model --type model --task text-generation -t demo \
  --readme "# my-model"
manifest file add alice/my-model model.safetensors https://host/model.safetensors --size-mb 440
manifest --json repo get alice/my-model      # structured output for agents
```

## 7. Hardened Multi-Stage `Dockerfile`

A multi-stage build compiles the frontend and guarantees all Node build tools
are stripped from the final production image. It creates a dedicated user and
runs without root.

```dockerfile
# Stage 1: Frontend Builder
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Production Backend
FROM python:3.11-slim
WORKDIR /app
RUN groupadd -r cataloggrp && useradd -r -g cataloggrp catalogusr
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-builder /app/dist ./static
# Data dir must be owned by the non-root user for SQLite journal/WAL writes.
RUN mkdir -p /app/data && chown -R catalogusr:cataloggrp /app
USER catalogusr
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

## 8. Secure `docker-compose.yml`

This locks down the runtime. With a read-only root filesystem, temp writes go to
an in-memory `tmpfs`, and database state is externalized to the host for backup.

```yaml
services:
  catalog:
    build: .
    image: fbobe3/manifest:latest
    container_name: local_ai_catalog
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      # Stateful DB mount: externalizes SQLite to the host for easy backup.
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:////app/data/catalog.db
      - SEED_DEMO_DATA=true          # seed example repos on first (empty) run

    # --- Security Hardening Directives ---
    read_only: true                  # immutable container filesystem
    tmpfs:
      - /tmp                         # ephemeral in-memory scratch
    cap_drop:
      - ALL                          # drop all Linux capabilities
    security_opt:
      - no-new-privileges:true       # block setuid/setgid escalation
```

> **Host volume permissions:** `./data` must be writable by the container's
> non-root user (e.g. `mkdir -p data && chmod 777 data` on first run), or switch
> to a named volume, which Docker initializes with the image's ownership.

## 9. Operational Maintenance & Backups

* **Database Backups:** The database is a single SQLite file (`catalog.db`) in
  the mounted `./data` directory. Back it up with a plain `rsync` over SSH to a
  NAS or secondary drive — no database tooling required.
* **Offline Updates:** The architecture expects no outbound internet calls. Pull
  code from your local repository and rebuild the image against internal package
  mirrors (append a `--registry` / `-i` mirror to the `npm ci` / `pip install`
  lines in the Dockerfile).
* **Disaster Recovery:** If the host or database fails, restore the last
  `./data` sync and restart the container to instantly recover the catalog.

## 10. Publishing / Distribution

- **Source:** GitHub — `https://github.com/fbobe321/manifest`.
- **Image:** Docker Hub — `fbobe3/manifest:latest`. Run without cloning:

  ```bash
  docker pull fbobe3/manifest:latest
  mkdir -p data && chmod 777 data
  docker run -d --name manifest -p 8080:8080 -v "$PWD/data:/app/data" \
    --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges \
    fbobe3/manifest:latest
  ```

- **Launcher (PyPI):** `manifest-hub` (in [`launcher/`](./launcher)) — a
  zero-dependency wrapper so the whole app is a `pip install` away. It runs the
  Docker image above with the same hardening flags:

  ```bash
  pip install manifest-hub
  manifest-hub up            # pull (if needed) + start → http://localhost:8080
  manifest-hub down
  ```

- **Agent CLI (PyPI):** `manifest-cli` (in [`cli/`](./cli)) — drives the
  running server's API from scripts (see §6). `pip install manifest-cli`.

## 11. Testing & Quality

A CLI-driven end-to-end suite lives in [`tests/`](./tests). It boots a dedicated
backend (fresh SQLite DB, demo seeding **off**) on a random port and exercises
the product through the installed `manifest` command, cross-checking with direct
API calls.

```bash
cd tests
python3 -m venv .venv && . .venv/bin/activate
pip install -r ../backend/requirements.txt -e ../cli -r requirements-test.txt
pytest -v
```

**Coverage (75 tests):** users (create/list/profile/idempotency/validation),
repositories (CRUD, duplicate/404 handling, likes/downloads, cards, bare-name
resolution), files (add/list/remove, size conversion, cascade delete, bad URL /
negative size), search / sort / pagination, facets, API validation & boundaries,
CLI behavior (JSON vs human output, exit codes, login/config flow), and
edge-case **bug probes**.

**Issues the suite found and fixed:**

| # | Issue | Fix |
|---|-------|-----|
| 1 | User search input leaked SQL `LIKE` wildcards — a query of `%` or `_` matched everything. | Escape `% _ \` in `q` and add `escape="\\"` to every `like`/`ilike`. |
| 2 | `--tag` filter matched substrings — `cat` matched a repo tagged `category`. | Exact-token match against a delimiter-wrapped CSV (`,tags,`). |
| 3 | A tag value containing a comma was silently split by CSV storage. | Normalize tags on write (split on commas, trim, dedupe); document that tags cannot contain commas. |

All 75 tests pass after the fixes.

## 12. Changelog

Delta from the original single-container draft:

- **Removed the filesystem scanner** and its `ASSET_SCAN_PATH` env +
  `/mnt/network_shares` read-only mount. Repositories are user-created; files
  are external links.
- **Added users** and a lightweight (password-less) identity model; repositories
  are owned as `owner/name`.
- **Added the full product surface:** faceted browse/search, Markdown cards,
  likes/downloads, and demo seed data (`SEED_DEMO_DATA`).
- **Added the agent-native `manifest` CLI** (see §6) with a `SKILL.md`.
- **Published** the Docker image (`fbobe3/manifest`) and two PyPI packages
  (`manifest-hub`, `manifest-cli`); rebranded to a naval theme (anchor logo,
  ocean-blue palette).
- **Added an end-to-end test suite** (§11) and fixed the three search/tag defects
  it uncovered.
- **Retained** the hardened single-container architecture and every security
  directive from the original spec (§3, §7, §8).
