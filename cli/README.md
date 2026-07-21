# manifest-cli

An agent-native command-line interface for a [Manifest](../README.md) model &
dataset repository server. Anything the web UI can do, the CLI can do — so an
automated agent can operate the site with zero browser.

Design follows the [CLI-Anything](https://github.com/HKUDS/CLI-Anything)
conventions: hierarchical `group action` commands, a universal `--json` flag for
structured agent output, `--help` for capability discovery, and an interactive
REPL. See [`SKILL.md`](./SKILL.md) for the agent-facing quick reference.

## Install

```bash
pip install -e .
# point it at your server (default http://localhost:8080)
manifest cfg set-url http://your-host:8080
```

## Quick start

```bash
manifest health
manifest stats
manifest repo list --type model --sort trending

manifest login alice --name "Alice"
manifest repo create alice/my-model --type model --task text-generation \
  -t demo --readme "# my-model"
manifest file add alice/my-model model.safetensors https://host/model.safetensors --size-mb 440
manifest repo get alice/my-model

manifest repl          # interactive session
```

## Agent usage

Add `--json` to any command for structured output and rely on exit codes for
success/failure:

```bash
manifest --json repo search whisper --limit 3
manifest --json repo get openai/whisper-large-v3
```

Configuration resolves in this order: CLI flag → environment
(`MANIFEST_URL`, `MANIFEST_USER`) → `~/.manifest/config.json` → defaults.

Run `manifest --help` (and `manifest <group> --help`) for the full surface.
