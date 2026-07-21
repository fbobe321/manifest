"""`manifest-hub` — pull and run the Manifest hub Docker image in one command.

This is a thin, dependency-free wrapper around `docker`. The application itself
lives in the published image (`fbobe3/manifest`); this package just makes
starting it as easy as `pip install manifest-hub && manifest-hub up`.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import webbrowser

from manifest_hub import __version__

IMAGE = os.environ.get("MANIFEST_HUB_IMAGE", "fbobe3/manifest")
TAG = os.environ.get("MANIFEST_HUB_TAG", "latest")
NAME = os.environ.get("MANIFEST_HUB_NAME", "manifest")
PORT = int(os.environ.get("MANIFEST_HUB_PORT", "8080"))
DATA = os.environ.get("MANIFEST_HUB_DATA", "./manifest-data")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _die(msg: str, code: int = 1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def _docker() -> str:
    exe = shutil.which("docker")
    if not exe:
        _die(
            "Docker is not installed or not on PATH. Manifest runs as a container;\n"
            "install Docker Desktop / Engine first: https://docs.docker.com/get-docker/",
            code=2,
        )
    return exe


def _run(args: list[str], check: bool = True, quiet: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        check=check,
        text=True,
        stdout=subprocess.DEVNULL if quiet else None,
        stderr=subprocess.DEVNULL if quiet else None,
    )


def _capture(args: list[str]) -> str:
    return subprocess.run(args, text=True, capture_output=True).stdout.strip()


def _image_ref(tag: str | None = None) -> str:
    return f"{IMAGE}:{tag or TAG}"


def _container_state(docker: str, name: str) -> str | None:
    """Return 'running', 'exited', ... or None if the container doesn't exist."""
    out = _capture([docker, "ps", "-a", "--filter", f"name=^{name}$", "--format", "{{.State}}"])
    return out or None


def _image_present(docker: str, ref: str) -> bool:
    return subprocess.run(
        [docker, "image", "inspect", ref], capture_output=True
    ).returncode == 0


def _url(port: int) -> str:
    return f"http://localhost:{port}"


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #
def cmd_up(a):
    docker = _docker()
    ref = _image_ref(a.tag)

    # Pull if asked, or if the image isn't available locally yet.
    if a.pull or not _image_present(docker, ref):
        print(f"Pulling {ref} …")
        _run([docker, "pull", ref])

    state = _container_state(docker, a.name)
    if state is not None:
        if a.replace:
            print(f"Removing existing container '{a.name}' …")
            _run([docker, "rm", "-f", a.name], quiet=True)
        elif state == "running":
            print(f"'{a.name}' is already running → {_url(a.port)}")
            return
        else:
            print(f"Starting existing container '{a.name}' …")
            _run([docker, "start", a.name], quiet=True)
            _report(a)
            return

    # Prepare a writable host data dir (SQLite lives here; survives restarts).
    data_dir = os.path.abspath(a.data)
    os.makedirs(data_dir, exist_ok=True)
    try:
        os.chmod(data_dir, 0o777)  # container runs as a non-root user
    except OSError:
        pass

    run_args = [
        docker, "run",
        "--name", a.name,
        "-p", f"{a.port}:8080",
        "-v", f"{data_dir}:/app/data",
        # Same hardening as the shipped docker-compose.yml.
        "--read-only",
        "--tmpfs", "/tmp",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--restart", "unless-stopped",
    ]
    if a.foreground:
        run_args += ["--rm", ref]
        print(f"Starting Manifest on {_url(a.port)} (Ctrl-C to stop) …")
        os.execv(docker, run_args)  # replace process; stream logs to the terminal
    else:
        run_args += ["-d", ref]
        _run(run_args, quiet=True)
        _report(a)


def _report(a):
    print(f"\n✓ Manifest is running → {_url(a.port)}")
    print(f"  data:   {os.path.abspath(a.data)}")
    print(f"  logs:   manifest-hub logs -f")
    print(f"  stop:   manifest-hub down")
    if a.open:
        webbrowser.open(_url(a.port))


def cmd_down(a):
    docker = _docker()
    if _container_state(docker, a.name) is None:
        print(f"No container named '{a.name}'.")
        return
    _run([docker, "rm", "-f", a.name], quiet=True)
    print(f"✓ stopped and removed '{a.name}'")


def cmd_logs(a):
    docker = _docker()
    if _container_state(docker, a.name) is None:
        _die(f"no container named '{a.name}' (start it with `manifest-hub up`)")
    args = [docker, "logs"]
    if a.follow:
        args.append("-f")
    args.append(a.name)
    try:
        _run(args)
    except KeyboardInterrupt:
        pass


def cmd_status(a):
    docker = _docker()
    state = _container_state(docker, a.name)
    if state is None:
        print(f"'{a.name}': not created")
        return
    print(f"'{a.name}': {state}")
    if state == "running":
        print(f"  url: {_url(a.port)}")
        _run([docker, "ps", "--filter", f"name=^{a.name}$",
              "--format", "table {{.Image}}\t{{.Status}}\t{{.Ports}}"])


def cmd_open(a):
    print(_url(a.port))
    webbrowser.open(_url(a.port))


def cmd_pull(a):
    docker = _docker()
    ref = _image_ref(a.tag)
    print(f"Pulling {ref} …")
    _run([docker, "pull", ref])
    print("✓ up to date")


# --------------------------------------------------------------------------- #
# argument parsing
# --------------------------------------------------------------------------- #
def _add_common(p):
    p.add_argument("--name", default=NAME, help=f"Container name (default: {NAME}).")
    p.add_argument("--port", type=int, default=PORT, help=f"Host port (default: {PORT}).")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="manifest-hub",
        description="Run the Manifest model & dataset hub from its Docker image.",
    )
    p.add_argument("--version", action="version", version=f"manifest-hub {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    up = sub.add_parser("up", help="Pull (if needed) and start the hub.")
    _add_common(up)
    up.add_argument("--data", default=DATA, help=f"Host data directory (default: {DATA}).")
    up.add_argument("--tag", default=None, help=f"Image tag (default: {TAG}).")
    up.add_argument("--pull", action="store_true", help="Force a docker pull first.")
    up.add_argument("--replace", action="store_true", help="Recreate if it already exists.")
    up.add_argument("--foreground", action="store_true", help="Run attached (stream logs).")
    up.add_argument("--open", action="store_true", help="Open the app in a browser.")
    up.set_defaults(func=cmd_up)

    down = sub.add_parser("down", help="Stop and remove the hub container.")
    _add_common(down)
    down.set_defaults(func=cmd_down)

    logs = sub.add_parser("logs", help="Show container logs.")
    _add_common(logs)
    logs.add_argument("-f", "--follow", action="store_true", help="Follow log output.")
    logs.set_defaults(func=cmd_logs)

    status = sub.add_parser("status", help="Show container status.")
    _add_common(status)
    status.set_defaults(func=cmd_status)

    opn = sub.add_parser("open", help="Open the app in a browser.")
    _add_common(opn)
    opn.set_defaults(func=cmd_open)

    pull = sub.add_parser("pull", help="Pull the latest image.")
    pull.add_argument("--tag", default=None)
    pull.set_defaults(func=cmd_pull)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except subprocess.CalledProcessError as e:
        _die(f"docker command failed (exit {e.returncode})")
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
