# manifest-hub

Run the [**Manifest**](https://github.com/fbobe321/manifest) model & dataset hub
with one command. This is a tiny, dependency-free launcher around the published
Docker image [`fbobe3/manifest`](https://hub.docker.com/r/fbobe3/manifest) — so
standing up the whole app is as easy as a `pip install`.

> Requires **Docker** on the host (the app runs as a container). This package
> only orchestrates `docker`; it contains no application code itself.

## Install

```bash
pip install manifest-hub
```

## Use

```bash
manifest-hub up            # pull (if needed) + start → http://localhost:8080
manifest-hub up --open     # ...and open it in your browser
manifest-hub status
manifest-hub logs -f
manifest-hub down          # stop and remove
manifest-hub pull          # update to the latest image
```

The container is started with the same hardening as the project's
`docker-compose.yml`: read-only root filesystem, `--cap-drop ALL`,
`--security-opt no-new-privileges`, a tmpfs `/tmp`, and a non-root user. Your
data (the SQLite database) is persisted to a host directory that survives
restarts.

## Options

| Flag | Applies to | Default | Meaning |
|------|------------|---------|---------|
| `--port` | all | `8080` | Host port to publish |
| `--name` | all | `manifest` | Container name |
| `--data` | `up` | `./manifest-data` | Host directory for the SQLite DB |
| `--tag` | `up`, `pull` | `latest` | Image tag |
| `--pull` | `up` | off | Force `docker pull` before starting |
| `--replace` | `up` | off | Recreate the container if it exists |
| `--foreground` | `up` | off | Run attached and stream logs |
| `--open` | `up`, `open` | — | Open the app in a browser |

Environment overrides: `MANIFEST_HUB_IMAGE`, `MANIFEST_HUB_TAG`,
`MANIFEST_HUB_NAME`, `MANIFEST_HUB_PORT`, `MANIFEST_HUB_DATA`.

## Related

- **Web app + API:** the image served at the port above.
- **Agent CLI:** [`manifest-cli`](https://github.com/fbobe321/manifest/tree/main/cli)
  (`pip install` the `cli/` package) drives the running server from scripts.
