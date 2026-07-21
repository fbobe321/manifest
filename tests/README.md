# Test suite

End-to-end tests that boot a dedicated backend (fresh SQLite DB, demo seeding
off) and drive it through the installed `manifest` CLI, cross-checking with
direct API calls. Covers users, repositories, files, search/sort/pagination,
facets, validation, CLI behavior, and edge-case bug probes.

## Run

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r ../backend/requirements.txt      # server under test
pip install -e ../cli                            # the `manifest` command
pip install -r requirements-test.txt             # pytest + requests
pytest -v
```

The harness picks a free port and manages the server process itself; nothing
external needs to be running.
