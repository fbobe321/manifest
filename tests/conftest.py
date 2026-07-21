"""Test harness: boots a dedicated backend instance and drives it via the CLI.

* A fresh SQLite DB per test session, with demo seeding disabled, so state is
  deterministic.
* `run_cli` invokes the installed `manifest` command against that server.
* `api` is a thin requests helper for cross-checking / probing endpoints the
  CLI does not expose directly.
"""
from __future__ import annotations

import json as jsonlib
import os
import socket
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="session")
def base_url(tmp_path_factory):
    port = _free_port()
    db = tmp_path_factory.mktemp("db") / "test.db"
    static = tmp_path_factory.mktemp("nostatic")  # ensures SPA route returns JSON
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db}",
        "SEED_DEMO_DATA": "false",
        "STATIC_DIR": str(static),
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning"],
        cwd=str(BACKEND_DIR),
        env=env,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            if proc.poll() is not None:
                raise RuntimeError("server process exited during startup")
            try:
                if requests.get(f"{url}/api/health", timeout=0.5).status_code == 200:
                    break
            except requests.RequestException:
                time.sleep(0.15)
        else:
            raise RuntimeError("server did not become healthy in time")
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@dataclass
class CliResult:
    code: int
    out: str
    err: str

    @property
    def json(self):
        return jsonlib.loads(self.out)

    def ok(self) -> bool:
        return self.code == 0


@pytest.fixture(scope="session")
def cli_config_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("manifestcfg")


@pytest.fixture(scope="session")
def run_cli(base_url, cli_config_dir):
    def _run(*args, user=None, json=True, config_dir=None, timeout=30) -> CliResult:
        cmd = ["manifest", "--url", base_url]
        if user is not None:
            cmd += ["--as", user]
        if json:
            cmd += ["--json"]
        cmd += [str(a) for a in args]
        env = {
            **os.environ,
            "MANIFEST_CONFIG_DIR": str(config_dir or cli_config_dir),
            "NO_COLOR": "1",
            "TERM": "dumb",
            "COLUMNS": "200",
        }
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout)
        return CliResult(code=p.returncode, out=p.stdout.strip(), err=p.stderr.strip())

    return _run


@pytest.fixture(scope="session")
def api(base_url):
    class Api:
        def __init__(self):
            self.s = requests.Session()

        def _u(self, path):
            return f"{base_url}/api{path}"

        def get(self, path, **params):
            return self.s.get(self._u(path), params=params)

        def post(self, path, body=None):
            return self.s.post(self._u(path), json=body)

        def put(self, path, body=None):
            return self.s.put(self._u(path), json=body)

        def delete(self, path):
            return self.s.delete(self._u(path))

    return Api()


@pytest.fixture
def uniq():
    """A short unique token for names, so tests never collide on the shared DB."""
    return lambda prefix="x": f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def a_user(run_cli, uniq):
    """Create and return a fresh username via the CLI."""
    name = uniq("user")
    r = run_cli("user", "create", name)
    assert r.ok(), r.err
    return name


@pytest.fixture
def a_repo(run_cli, a_user, uniq):
    """Create and return (owner, name, repo_id) for a fresh model repo."""
    name = uniq("model")
    r = run_cli("repo", "create", f"{a_user}/{name}", "--type", "model",
                "--desc", "fixture repo", user=a_user)
    assert r.ok(), r.err
    return a_user, name, f"{a_user}/{name}"
