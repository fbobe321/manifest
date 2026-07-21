"""Rendering helpers: raw JSON for agents, rich tables/panels for humans."""
from __future__ import annotations

import json
import sys

from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)


def human_size(n: int | None) -> str:
    if not n:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    val = float(n)
    while val >= 1024 and i < len(units) - 1:
        val /= 1024
        i += 1
    return f"{val:.0f} {units[i]}" if (i == 0 or val >= 100) else f"{val:.1f} {units[i]}"


def compact(n: int | None) -> str:
    n = n or 0
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n/1000:.1f}k"
    return f"{n/1_000_000:.1f}M"


def emit(data, json_mode: bool, human=None) -> None:
    """Print `data` as JSON, or call `human(data)` for the pretty view."""
    if json_mode or human is None:
        console.print_json(json.dumps(data, default=str))
    else:
        human(data)


def fail(message: str, json_mode: bool, code: int = 1) -> None:
    if json_mode:
        console.print_json(json.dumps({"error": message}))
    else:
        err_console.print(f"[bold red]error:[/] {message}")
    sys.exit(code)


# ---- human renderers ---------------------------------------------------- #
def repo_row_table(repos: list[dict], title: str = "Repositories") -> Table:
    t = Table(title=title, title_style="bold", header_style="bold")
    t.add_column("repo_id", style="cyan", no_wrap=True)
    t.add_column("type")
    t.add_column("task")
    t.add_column("size", justify="right")
    t.add_column("↓", justify="right")
    t.add_column("♥", justify="right")
    for r in repos:
        icon = "📊" if r["repo_type"] == "dataset" else "🧠"
        t.add_row(
            f"{icon} {r['repo_id']}",
            r["repo_type"],
            r.get("task") or "-",
            human_size(r.get("total_size_bytes")),
            compact(r.get("downloads")),
            compact(r.get("likes")),
        )
    return t


def render_repo_list(payload: dict) -> None:
    items = payload.get("items", [])
    if not items:
        console.print("[dim]No repositories match.[/]")
        return
    console.print(repo_row_table(items))
    console.print(
        f"[dim]{len(items)} shown of {payload.get('total', len(items))} total[/]"
    )


def render_repo(repo: dict) -> None:
    icon = "📊" if repo["repo_type"] == "dataset" else "🧠"
    console.print(f"\n[bold cyan]{icon} {repo['repo_id']}[/]  [dim]({repo['repo_type']})[/]")
    if repo.get("description"):
        console.print(f"  {repo['description']}")
    meta = []
    for key in ("task", "library", "license"):
        if repo.get(key):
            meta.append(f"{key}={repo[key]}")
    if repo.get("tags"):
        meta.append("tags=" + ",".join(repo["tags"]))
    if meta:
        console.print("  [dim]" + "  ".join(meta) + "[/]")
    console.print(
        f"  [dim]↓ {compact(repo.get('downloads'))}   "
        f"♥ {compact(repo.get('likes'))}   "
        f"{human_size(repo.get('total_size_bytes'))} in {repo.get('num_files', 0)} files[/]"
    )
    files = repo.get("files")
    if files:
        t = Table(header_style="bold", show_edge=False, pad_edge=False)
        t.add_column("id", justify="right", style="dim")
        t.add_column("file", style="green")
        t.add_column("size", justify="right")
        t.add_column("url", style="dim")
        for f in files:
            t.add_row(str(f["id"]), f["filename"], human_size(f.get("size_bytes")), f["url"])
        console.print(t)
    if repo.get("readme"):
        console.print("\n[bold]card:[/] [dim](use `manifest repo card` for full text)[/]")


def render_stats(s: dict) -> None:
    t = Table(title="Manifest — site stats", header_style="bold")
    t.add_column("metric")
    t.add_column("value", justify="right")
    for k in ("total_repos", "models", "datasets", "users", "total_files"):
        t.add_row(k, str(s.get(k, 0)))
    t.add_row("total_size", human_size(s.get("total_size_bytes")))
    console.print(t)


def render_facets(f: dict) -> None:
    for group in ("tasks", "libraries", "licenses", "tags"):
        vals = f.get(group, [])
        if not vals:
            continue
        console.print(f"[bold]{group}[/]: " + "  ".join(f"{v['value']}({v['count']})" for v in vals))


def render_user(u: dict) -> None:
    console.print(f"[bold]@{u['username']}[/]  {u.get('full_name','')}")
    if u.get("bio"):
        console.print(f"  {u['bio']}")
    repos = u.get("repositories", [])
    if repos:
        console.print(repo_row_table(repos, title=f"{u['username']}'s repositories"))
