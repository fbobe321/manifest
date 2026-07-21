"""Minimal interactive REPL that re-dispatches Click commands with kept state."""
from __future__ import annotations

import shlex

import click

from manifest_cli import output as out


BANNER = """[bold cyan]Manifest REPL[/] — type commands without the leading `manifest`.
Examples:  repo list --type model   ·   repo get openai/whisper-large-v3
Meta:  help  ·  :json on|off  ·  :as <user>  ·  quit"""


def run_repl(group: click.Group, ctx) -> None:
    out.console.print(BANNER)
    out.console.print(f"[dim]server {ctx.url}  ·  user {ctx.user or '(none)'}[/]\n")

    while True:
        try:
            line = input("manifest> ").strip()
        except (EOFError, KeyboardInterrupt):
            out.console.print("\n[dim]bye[/]")
            return
        if not line:
            continue
        if line in ("quit", "exit", ":q"):
            return
        if line in ("help", "?"):
            with click.Context(group) as c:
                out.console.print(group.get_help(c))
            continue

        # REPL meta-commands that mutate session state.
        if line.startswith(":json"):
            ctx.json = line.endswith("on")
            out.console.print(f"[dim]json output {'on' if ctx.json else 'off'}[/]")
            continue
        if line.startswith(":as "):
            ctx.user = line[4:].strip() or None
            out.console.print(f"[dim]acting user = {ctx.user}[/]")
            continue

        try:
            args = shlex.split(line)
        except ValueError as e:
            out.console.print(f"[red]{e}[/]")
            continue

        # Re-invoke the full command tree via Click's own dispatcher, reusing the
        # live Ctx (obj=ctx) so URL/user/json state persist across the session.
        try:
            group.main(args=args, prog_name="manifest", standalone_mode=False, obj=ctx)
        except click.exceptions.Abort:
            out.console.print("[dim]aborted[/]")
        except click.ClickException as e:
            out.console.print(f"[red]{e.format_message()}[/]")
        except SystemExit:
            pass  # out.fail() calls sys.exit; keep the REPL alive
