# Skill: Manifest CLI

Drive a Manifest model & dataset repository server entirely from the command
line. Every action available in the web UI is reachable here, so an agent can
browse, create, edit, and delete repositories, files, and users without a
browser.

## Setup

```bash
pip install -e cli/                 # installs the `manifest` command
export MANIFEST_URL=http://localhost:8080   # or use `manifest cfg set-url`
```

## Conventions

- **Structured output:** add `--json` to any command for machine-readable JSON.
  Without it you get human-readable tables.
- **Discovery:** `manifest --help`, `manifest repo --help`, etc. list everything.
- **Acting user:** mutations that create a repo need an owner. Set one once with
  `manifest login <username>` (or `--as <username>` / `MANIFEST_USER`). Then a
  bare `name` means `<user>/<name>`; an explicit `owner/name` overrides it.
- **Exit codes:** non-zero on any API error; the message goes to stderr (or the
  `{"error": ...}` JSON object with `--json`).
- **REF** arguments are `owner/name` (e.g. `openai/whisper-large-v3`).

## Command map

| Group | Command | Purpose |
|-------|---------|---------|
| — | `health`, `stats`, `facets [--type]` | Server status, counts, filter facets |
| — | `login USER [--name --bio]`, `whoami`, `logout` | Session identity |
| `cfg` | `show`, `set-url URL` | Saved config (`~/.manifest/config.json`) |
| `user` | `create USER`, `get USER`, `list` | Users & profiles |
| `repo` | `list [filters]`, `search QUERY` | Browse/search (filters: `--type --owner --task --library --license --tag -q --sort --limit --offset`) |
| `repo` | `get REF`, `card REF`, `url REF` | Inspect one repo / its Markdown card / web URL |
| `repo` | `create REF ...`, `update REF ...`, `delete REF` | CRUD (`--type --desc --task --library --license -t/--tag --readme/--readme-file`) |
| `repo` | `like REF`, `download REF` | Like / register a download + list links |
| `file` | `list REF`, `add REF FILENAME URL [--size/--size-mb]`, `rm REF ID` | External file links |
| — | `repl` | Interactive session (state persists; `:as`, `:json on/off`, `help`, `quit`) |

## Recipes

```bash
# Publish a model end-to-end as a user
manifest login acme --name "Acme Corp"
manifest repo create acme/tiny-llm --type model --task text-generation \
  --library transformers --license apache-2.0 -t llm -t tiny \
  --readme-file CARD.md
manifest file add acme/tiny-llm model.safetensors https://cdn.acme.com/tiny-llm/model.safetensors --size-mb 440
manifest repo get acme/tiny-llm

# Agent-style structured queries
manifest --json repo list --type dataset --sort downloads --limit 5
manifest --json stats

# Search then act
manifest repo search whisper --type model
manifest repo like openai/whisper-large-v3
```
