# Local AI Hub — a self-hosted Hugging Face clone

A small, offline-friendly hub for cataloging **models** and **datasets**. Users
create a repository, write a Markdown model-/dataset-card, tag it, and list its
files as **external links** — the hub stores the metadata and the link, never
the bytes. Ships as a single hardened container (React SPA served by FastAPI),
per [`PRD.md`](./PRD.md).

## What it does

- **Browse** models and datasets with faceted filters (task, library, license, tags), search, and sort (trending / recent / downloads / likes).
- **Repository pages** with a rendered Markdown card and a "Files and versions" tab.
- **Files are links**: each file points at wherever it actually lives (object store, mirror, another server). Downloads open the external URL and bump a counter.
- **Users**: pick a username (no password — this is a local, zero-trust tool) and publish repositories under it. Like repos, edit/delete your own.
- **Profiles** listing a user's models and datasets.

## Architecture

| Layer     | Tech                                            |
|-----------|-------------------------------------------------|
| Frontend  | React 18 + Vite + React Router (compiled to static files) |
| Backend   | FastAPI + SQLAlchemy 2, serves the API **and** the SPA |
| Storage   | SQLite (single file on the mounted `./data` volume) |
| Delivery  | One multi-stage Docker image, non-root, read-only rootfs |

The SPA is compiled in a Node build stage and copied into the Python image as
static assets, so the final container has no Node tooling. FastAPI serves the
JSON API under `/api` and the SPA for every other path.

## Run the pre-built image (Docker Hub)

The image is published as [`fbobe321/manifest`](https://hub.docker.com/r/fbobe321/manifest).
Pull and run it directly — no need to clone this repo:

```bash
docker pull fbobe321/manifest:latest

# The SQLite DB is written by the container's non-root user into ./data,
# so make sure that directory is writable by it:
mkdir -p data && chmod 777 data

docker run -d --name manifest -p 8080:8080 \
  -v "$PWD/data:/app/data" \
  --read-only --tmpfs /tmp --cap-drop ALL \
  --security-opt no-new-privileges \
  fbobe321/manifest:latest
# open http://localhost:8080
```

Prefer Compose? Use the same `docker-compose.yml` but swap `build: .` for the
published image:

```yaml
services:
  catalog:
    image: fbobe321/manifest:latest   # instead of `build: .`
    # ...keep the rest of the service definition unchanged
```

## Build and run from source

```bash
# The SQLite DB is written by the container's non-root user into ./data,
# so make sure that directory is writable by it:
mkdir -p data && chmod 777 data

docker compose up --build
# open http://localhost:8080
```

The first start seeds a few example repositories (set `SEED_DEMO_DATA=false` in
`docker-compose.yml` to disable). The database lives at `./data/catalog.db` on
the host — back it up by copying/rsyncing that directory.

### Security hardening (from the PRD)

`docker-compose.yml` runs the container with `read_only: true`, `cap_drop: ALL`,
`no-new-privileges`, a tmpfs `/tmp`, and an unprivileged user. The only writable
location is the mounted `./data` volume (SQLite + WAL).

## Run locally for development

Two terminals — the Vite dev server proxies `/api` to the backend (no CORS):

```bash
# 1) Backend
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8080

# 2) Frontend
cd frontend
npm install
npm run dev            # http://localhost:5173
```

By default the backend writes `backend/data/catalog.db` and static-serving is
disabled until you build the SPA (`npm run build`), which is fine in dev because
Vite serves the UI.

## API overview

| Method & path | Purpose |
|---|---|
| `GET /api/repos` | List/search repos (`q`, `repo_type`, `owner`, `task`, `library`, `license`, `tag`, `sort`, paging) |
| `POST /api/repos` | Create a repository |
| `GET /api/repos/{owner}/{name}` | Repo detail (card + files) |
| `PUT /api/repos/{owner}/{name}` | Update a repository |
| `DELETE /api/repos/{owner}/{name}` | Delete a repository |
| `POST /api/repos/{owner}/{name}/like` | Increment likes |
| `POST /api/repos/{owner}/{name}/download` | Register a download |
| `POST /api/repos/{owner}/{name}/files` | Add a file (external URL) |
| `DELETE /api/repos/{owner}/{name}/files/{id}` | Remove a file |
| `POST /api/users` / `GET /api/users/{username}` | Create user / profile |
| `GET /api/facets` · `GET /api/stats` | Filter facets · summary counts |

Interactive docs: `http://localhost:8080/api/docs`.

## Note on the PRD

The PRD described a filesystem *scanner* over a mounted asset share
(`ASSET_SCAN_PATH`, `/mnt/network_shares`). This build instead follows the
requested Hugging Face model: **no scanning** — users create repositories and
add file links. The scan-related volume/env were therefore dropped from
`docker-compose.yml`; all of the PRD's security-hardening directives and the
single-container architecture are kept intact.
