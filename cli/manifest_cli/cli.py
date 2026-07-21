"""Manifest CLI — drive the whole site from the command line.

Design mirrors the CLI-Anything conventions: hierarchical `group action`
commands, a universal `--json` flag for agent-friendly structured output,
`--help` for discovery, and an interactive `repl`.
"""
from __future__ import annotations

import click

from manifest_cli import __version__, config
from manifest_cli.client import ApiError, Client
from manifest_cli import output as out


# --------------------------------------------------------------------------- #
# Context / root group
# --------------------------------------------------------------------------- #
class Ctx:
    def __init__(self, url, json_mode, user):
        self.url = url
        self.json = json_mode
        self.user = user
        self._client = None

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = Client(self.url)
        return self._client

    def require_user(self):
        if not self.user:
            out.fail(
                "no acting user set — run `manifest login <username>` or pass `--as <username>`",
                self.json,
            )
        return self.user


def resolve_repo(ctx: Ctx, ref: str):
    """Accept `owner/name` or a bare `name` (owner taken from the acting user)."""
    if "/" in ref:
        owner, name = ref.split("/", 1)
        return owner, name
    return ctx.require_user(), ref


def run(ctx: Ctx, fn, human=None):
    try:
        data = fn()
    except ApiError as e:
        out.fail(str(e), ctx.json)
    else:
        out.emit(data, ctx.json, human)
        return data


pass_ctx = click.make_pass_decorator(Ctx)

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__, prog_name="manifest")
@click.option("--url", default=None, help="Server base URL (env MANIFEST_URL).")
@click.option("--as", "user", default=None, help="Act as this username (env MANIFEST_USER).")
@click.option("--json", "json_mode", is_flag=True, help="Emit structured JSON for agents.")
@click.pass_context
def cli(clickctx, url, user, json_mode):
    """Manifest — a self-hosted model & dataset repository.

    An agent can perform every site action through these commands. Global flags
    apply to any subcommand, e.g. `manifest --json repo list`.
    """
    # When driven from the REPL, a live Ctx is injected via `obj=`; keep it so
    # session state (:as, :json, url) persists, letting flags override upward.
    if isinstance(clickctx.obj, Ctx):
        existing = clickctx.obj
        if url:
            existing.url = config.resolve_url(url)
            existing._client = None
        if user:
            existing.user = user
        if json_mode:
            existing.json = True
        return

    clickctx.obj = Ctx(
        url=config.resolve_url(url),
        json_mode=json_mode,
        user=config.resolve_user(user),
    )


# --------------------------------------------------------------------------- #
# Session / config
# --------------------------------------------------------------------------- #
@cli.command()
@click.argument("username")
@click.option("--name", default="", help="Display name.")
@click.option("--bio", default="", help="Short bio.")
@pass_ctx
def login(ctx: Ctx, username, name, bio):
    """Create/select USERNAME as the acting user (no password — local tool)."""
    try:
        user = ctx.client.create_user(username, name, bio)
    except ApiError as e:
        out.fail(str(e), ctx.json)
        return
    data = config.load()
    data["user"] = username
    data["url"] = ctx.url
    config.save(data)
    out.emit(user, ctx.json, lambda u: out.console.print(
        f"[green]✓[/] signed in as [bold]@{u['username']}[/] on {ctx.url}"))


@cli.command()
@pass_ctx
def whoami(ctx: Ctx):
    """Show the current acting user and server."""
    info = {"user": ctx.user, "url": ctx.url}
    out.emit(info, ctx.json, lambda i: out.console.print(
        f"user: [bold]{i['user'] or '(none)'}[/]   server: {i['url']}"))


@cli.command()
@pass_ctx
def logout(ctx: Ctx):
    """Forget the saved acting user."""
    data = config.load()
    data.pop("user", None)
    config.save(data)
    out.emit({"user": None}, ctx.json, lambda _: out.console.print("[green]✓[/] logged out"))


@cli.group()
def cfg():
    """Inspect or change saved configuration."""


@cfg.command("show")
@pass_ctx
def cfg_show(ctx: Ctx):
    """Show resolved configuration."""
    out.emit({"url": ctx.url, "user": ctx.user, "file": str(config.CONFIG_FILE)}, ctx.json,
             lambda d: out.console.print(d))


@cfg.command("set-url")
@click.argument("url")
@pass_ctx
def cfg_set_url(ctx: Ctx, url):
    """Persist the default server URL."""
    data = config.load()
    data["url"] = url
    config.save(data)
    out.emit({"url": url}, ctx.json, lambda d: out.console.print(f"[green]✓[/] url = {d['url']}"))


# --------------------------------------------------------------------------- #
# Meta
# --------------------------------------------------------------------------- #
@cli.command()
@pass_ctx
def health(ctx: Ctx):
    """Check server health."""
    run(ctx, ctx.client.health, lambda d: out.console.print(f"[green]{d['status']}[/]"))


@cli.command()
@pass_ctx
def stats(ctx: Ctx):
    """Show site-wide statistics."""
    run(ctx, ctx.client.stats, out.render_stats)


@cli.command()
@click.option("--type", "repo_type", type=click.Choice(["model", "dataset"]), default=None)
@pass_ctx
def facets(ctx: Ctx, repo_type):
    """List available filter facets (tasks, libraries, licenses, tags)."""
    run(ctx, lambda: ctx.client.facets(repo_type), out.render_facets)


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
@cli.group()
def user():
    """Manage and inspect users."""


@user.command("create")
@click.argument("username")
@click.option("--name", default="")
@click.option("--bio", default="")
@pass_ctx
def user_create(ctx: Ctx, username, name, bio):
    """Create a user."""
    run(ctx, lambda: ctx.client.create_user(username, name, bio),
        lambda u: out.console.print(f"[green]✓[/] created @{u['username']}"))


@user.command("list")
@pass_ctx
def user_list(ctx: Ctx):
    """List all users."""
    run(ctx, ctx.client.list_users, lambda users: out.console.print(
        "\n".join(f"@{u['username']}  [dim]{u.get('full_name','')}[/]" for u in users) or "[dim]none[/]"))


@user.command("get")
@click.argument("username")
@pass_ctx
def user_get(ctx: Ctx, username):
    """Show a user profile and their repositories."""
    run(ctx, lambda: ctx.client.get_user(username), out.render_user)


# --------------------------------------------------------------------------- #
# Repositories
# --------------------------------------------------------------------------- #
@cli.group()
def repo():
    """Create, browse, edit, and delete repositories."""


@repo.command("list")
@click.option("-q", "--query", default=None, help="Full-text search.")
@click.option("--type", "repo_type", type=click.Choice(["model", "dataset"]), default=None)
@click.option("--owner", default=None)
@click.option("--task", default=None)
@click.option("--library", default=None)
@click.option("--license", default=None)
@click.option("--tag", default=None)
@click.option("--sort", type=click.Choice(
    ["trending", "recent", "downloads", "likes", "created", "name"]), default="trending")
@click.option("--limit", default=30, type=int)
@click.option("--offset", default=0, type=int)
@pass_ctx
def repo_list(ctx: Ctx, query, repo_type, owner, task, library, license, tag, sort, limit, offset):
    """List/search repositories with filters."""
    run(ctx, lambda: ctx.client.list_repos(
        q=query, repo_type=repo_type, owner=owner, task=task, library=library,
        license=license, tag=tag, sort=sort, limit=limit, offset=offset),
        out.render_repo_list)


@repo.command("search")
@click.argument("query")
@click.option("--type", "repo_type", type=click.Choice(["model", "dataset"]), default=None)
@click.option("--limit", default=30, type=int)
@pass_ctx
def repo_search(ctx: Ctx, query, repo_type, limit):
    """Search repositories (shortcut for `repo list -q`)."""
    run(ctx, lambda: ctx.client.list_repos(q=query, repo_type=repo_type, limit=limit),
        out.render_repo_list)


@repo.command("get")
@click.argument("ref")
@pass_ctx
def repo_get(ctx: Ctx, ref):
    """Show a repository (REF = owner/name)."""
    owner, name = resolve_repo(ctx, ref)
    run(ctx, lambda: ctx.client.get_repo(owner, name), out.render_repo)


@repo.command("card")
@click.argument("ref")
@pass_ctx
def repo_card(ctx: Ctx, ref):
    """Print the raw Markdown model/dataset card."""
    owner, name = resolve_repo(ctx, ref)
    try:
        r = ctx.client.get_repo(owner, name)
    except ApiError as e:
        out.fail(str(e), ctx.json)
        return
    if ctx.json:
        out.emit({"repo_id": r["repo_id"], "readme": r.get("readme", "")}, True)
    else:
        out.console.print(r.get("readme") or "[dim](no card)[/]")


def _read_readme(readme, readme_file):
    if readme_file:
        with open(readme_file, encoding="utf-8") as fh:
            return fh.read()
    return readme


@repo.command("create")
@click.argument("ref")
@click.option("--type", "repo_type", type=click.Choice(["model", "dataset"]), default="model")
@click.option("--desc", "description", default="", help="One-line description.")
@click.option("--task", default=None)
@click.option("--library", default=None)
@click.option("--license", default=None)
@click.option("-t", "--tag", "tags", multiple=True, help="Repeatable.")
@click.option("--readme", default="", help="Markdown card text.")
@click.option("--readme-file", type=click.Path(exists=True), default=None)
@pass_ctx
def repo_create(ctx: Ctx, ref, repo_type, description, task, library, license, tags, readme, readme_file):
    """Create a repository (REF = owner/name or just name for the acting user)."""
    owner, name = resolve_repo(ctx, ref)
    body = dict(
        owner=owner, name=name, repo_type=repo_type, description=description,
        task=task, library=library, license=license, tags=list(tags),
        readme=_read_readme(readme, readme_file),
    )
    run(ctx, lambda: ctx.client.create_repo(**body),
        lambda r: out.console.print(f"[green]✓[/] created [cyan]{r['repo_id']}[/]"))


@repo.command("update")
@click.argument("ref")
@click.option("--desc", "description", default=None)
@click.option("--task", default=None)
@click.option("--library", default=None)
@click.option("--license", default=None)
@click.option("-t", "--tag", "tags", multiple=True, help="Replaces all tags if given.")
@click.option("--readme", default=None)
@click.option("--readme-file", type=click.Path(exists=True), default=None)
@pass_ctx
def repo_update(ctx: Ctx, ref, description, task, library, license, tags, readme, readme_file):
    """Update repository fields (REF = owner/name)."""
    owner, name = resolve_repo(ctx, ref)
    body = dict(description=description, task=task, library=library, license=license)
    if tags:
        body["tags"] = list(tags)
    rd = _read_readme(readme, readme_file) if (readme is not None or readme_file) else None
    if rd is not None:
        body["readme"] = rd
    run(ctx, lambda: ctx.client.update_repo(owner, name, **body),
        lambda r: out.console.print(f"[green]✓[/] updated [cyan]{r['repo_id']}[/]"))


@repo.command("delete")
@click.argument("ref")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation.")
@pass_ctx
def repo_delete(ctx: Ctx, ref, yes):
    """Delete a repository (REF = owner/name)."""
    owner, name = resolve_repo(ctx, ref)
    if not yes and not ctx.json:
        click.confirm(f"Delete {owner}/{name}?", abort=True)
    run(ctx, lambda: ctx.client.delete_repo(owner, name),
        lambda _: out.console.print(f"[green]✓[/] deleted {owner}/{name}"))


@repo.command("like")
@click.argument("ref")
@pass_ctx
def repo_like(ctx: Ctx, ref):
    """Like a repository."""
    owner, name = resolve_repo(ctx, ref)
    run(ctx, lambda: ctx.client.like_repo(owner, name),
        lambda r: out.console.print(f"[green]♥[/] {r['repo_id']} now has {r['likes']} likes"))


@repo.command("download")
@click.argument("ref")
@pass_ctx
def repo_download(ctx: Ctx, ref):
    """Register a download and print the file links."""
    owner, name = resolve_repo(ctx, ref)
    try:
        ctx.client.register_download(owner, name)
        r = ctx.client.get_repo(owner, name)
    except ApiError as e:
        out.fail(str(e), ctx.json)
        return
    payload = {"repo_id": r["repo_id"], "downloads": r["downloads"],
               "files": [{"filename": f["filename"], "url": f["url"]} for f in r["files"]]}
    out.emit(payload, ctx.json, lambda p: out.console.print(
        f"[green]↓[/] {p['repo_id']} ({p['downloads']} downloads)\n" +
        "\n".join(f"  {f['filename']}  [dim]{f['url']}[/]" for f in p["files"])))


@repo.command("url")
@click.argument("ref")
@pass_ctx
def repo_url(ctx: Ctx, ref):
    """Print the web URL for a repository."""
    owner, name = resolve_repo(ctx, ref)
    url = f"{ctx.url}/{owner}/{name}"
    out.emit({"url": url}, ctx.json, lambda d: out.console.print(d["url"]))


# --------------------------------------------------------------------------- #
# Files
# --------------------------------------------------------------------------- #
@cli.group()
def file():
    """Manage a repository's external file links."""


@file.command("list")
@click.argument("ref")
@pass_ctx
def file_list(ctx: Ctx, ref):
    """List files in a repository."""
    owner, name = resolve_repo(ctx, ref)
    try:
        r = ctx.client.get_repo(owner, name)
    except ApiError as e:
        out.fail(str(e), ctx.json)
        return
    out.emit(r["files"], ctx.json, lambda files: out.console.print(
        "\n".join(f"[dim]{f['id']}[/] {f['filename']}  "
                  f"{out.human_size(f['size_bytes'])}  [dim]{f['url']}[/]" for f in files)
        or "[dim]no files[/]"))


@file.command("add")
@click.argument("ref")
@click.argument("filename")
@click.argument("url")
@click.option("--size", type=int, default=None, help="Size in bytes.")
@click.option("--size-mb", type=float, default=None, help="Size in MB (convenience).")
@pass_ctx
def file_add(ctx: Ctx, ref, filename, url, size, size_mb):
    """Add an external file link: manifest file add REF FILENAME URL."""
    owner, name = resolve_repo(ctx, ref)
    size_bytes = size if size is not None else (int(size_mb * 1024 * 1024) if size_mb else 0)
    run(ctx, lambda: ctx.client.add_file(owner, name, filename, url, size_bytes),
        lambda f: out.console.print(f"[green]✓[/] added {f['filename']} (id {f['id']})"))


@file.command("rm")
@click.argument("ref")
@click.argument("file_id", type=int)
@click.option("-y", "--yes", is_flag=True)
@pass_ctx
def file_rm(ctx: Ctx, ref, file_id, yes):
    """Remove a file by id: manifest file rm REF FILE_ID."""
    owner, name = resolve_repo(ctx, ref)
    if not yes and not ctx.json:
        click.confirm(f"Remove file {file_id} from {owner}/{name}?", abort=True)
    run(ctx, lambda: ctx.client.delete_file(owner, name, file_id),
        lambda _: out.console.print(f"[green]✓[/] removed file {file_id}"))


# --------------------------------------------------------------------------- #
# REPL
# --------------------------------------------------------------------------- #
@cli.command()
@pass_ctx
def repl(ctx: Ctx):
    """Start an interactive session."""
    from manifest_cli.repl import run_repl

    run_repl(cli, ctx)


def main():
    cli()


if __name__ == "__main__":
    main()
