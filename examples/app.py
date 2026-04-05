"""
Comprehensive typer-examples showcase.

Patterns demonstrated:
  1. Root app   — install(app, config=ExamplesConfig(vars={...}))
  2. Sub-apps   — each sub-app gets its own install() with an independent config
  3. App-in-app — db_app and server_app added to root via app.add_typer()
  4. Var tiers  — app-level vars, per-example overrides, and raw placeholders
  5. Detail     — optional prose line below each example heading
  6. Docs gen   — `python app.py docs` prints Markdown for all commands
"""

import typer

from typer_examples import ExamplesConfig, example, install
from typer_examples.docs import to_markdown, to_rst

# ── 1. Root app ───────────────────────────────────────────────────────────────
#
# App-level vars ("env", "version") are resolved for every example that uses
# {env} or {version} in its code string.  Per-example vars override these.

app = typer.Typer(name="platform", help="Platform management CLI.")
install(
    app,
    config=ExamplesConfig(
        panel_title="Platform Examples",
        vars={"env": "staging", "version": "1.4.2"},
    ),
)

# ── 2. db sub-app ─────────────────────────────────────────────────────────────
#
# Independent config: different panel title, monokai theme, and its own vars.
# Commands inside db_app pick up db_app's config — not the root app's.

db_app = typer.Typer(help="Database management commands.")
install(
    db_app,
    config=ExamplesConfig(
        panel_title="DB Examples",
        syntax_theme="monokai",
        vars={"db_url": "postgres://localhost/mydb"},
    ),
)
app.add_typer(db_app, name="db")

# ── 3. server sub-app ─────────────────────────────────────────────────────────
#
# Another independent config: cyan headings, no app-level vars (uses per-example).

server_app = typer.Typer(help="Application server lifecycle.")
install(
    server_app,
    config=ExamplesConfig(
        panel_title="Server Examples",
        heading_style="bold cyan",
    ),
)
app.add_typer(server_app, name="server")


# ── Root commands ─────────────────────────────────────────────────────────────


@app.command()
@example(
    "Deploy staging with a pinned tag",
    "{env} --tag {version}",
    detail="Pulls the image, runs migrations, and restarts affected services.",
)
@example(
    "Deploy production and skip confirmation",
    "production --tag {version} --yes",
    detail="Pass --yes in CI pipelines to avoid interactive prompts.",
    version="2.0.0",
)
def deploy(
    env: str,
    tag: str = typer.Option("latest", help="Docker image tag to deploy."),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt."),
):
    typer.echo(f"Deploying tag={tag!r} to {env!r}")


@app.command()
@example(
    "Tail last 50 lines from production",
    "production --tail 50",
)
@example(
    "Stream live logs from a specific service",
    "{env} --service api --follow",
    detail="Streams live output until you press Ctrl-C.",
)
def logs(
    env: str,
    service: str = typer.Option("web", help="Service name to tail."),
    tail: int = typer.Option(100, help="Number of lines to show."),
    follow: bool = typer.Option(False, "--follow", "-f", help="Stream live output."),
):
    typer.echo(f"Logs for {service!r} in {env!r} (tail={tail}, follow={follow})")


# ── db sub-commands ───────────────────────────────────────────────────────────
#
# {db_url} is resolved from db_app's config vars — invisible to the root app.


@db_app.command()
@example(
    "Run all pending migrations",
    "--url {db_url}",
    detail="Applies unapplied migrations in order; safe to run multiple times.",
)
@example(
    "Preview pending migrations without applying",
    "--url {db_url} --dry-run",
)
def migrate(
    url: str = typer.Option(..., help="Database connection URL."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only, no writes."),
):
    typer.echo(f"Migrating {url!r} (dry_run={dry_run})")


@db_app.command()
@example(
    "Seed with default fixtures",
    "--url {db_url}",
)
@example(
    "Seed from a custom fixture file",
    "--url {db_url} --file fixtures/dev.json",
    detail="Useful for bootstrapping fresh local environments.",
)
def seed(
    url: str = typer.Option(..., help="Database connection URL."),
    file: str = typer.Option("", "--file", "-f", help="Custom fixture file path."),
):
    label = file or "defaults"
    typer.echo(f"Seeding {url!r} from {label!r}")


@db_app.command()
@example(
    "Backup production to S3",
    "--url {db_url} --dest s3://backups/prod/latest.dump",
    db_url="postgres://prod-host/mydb",
    detail="Streams a pg_dump directly to S3 without a local temp file.",
)
def backup(
    url: str = typer.Option(..., help="Database connection URL."),
    dest: str = typer.Option(..., help="Destination path (local or s3://)."),
):
    typer.echo(f"Backing up {url!r} → {dest!r}")


# ── server sub-commands ───────────────────────────────────────────────────────


@server_app.command()
@example(
    "Start on a custom port",
    "--port 8080",
)
@example(
    "Start with multiple workers in the background",
    "--port 8080 --workers 4 --detach",
    detail="Spawns workers and returns immediately to the shell.",
)
def start(
    port: int = typer.Option(8000, help="Port to listen on."),
    workers: int = typer.Option(1, help="Number of worker processes."),
    detach: bool = typer.Option(False, "--detach", "-d", help="Run in background."),
):
    typer.echo(f"Starting server on :{port} (workers={workers}, detach={detach})")


@server_app.command()
@example(
    "Stop gracefully with a 30-second timeout",
    "--timeout 30",
    detail="Waits for in-flight requests to drain before shutting down.",
)
def stop(
    timeout: int = typer.Option(10, help="Seconds to wait for graceful shutdown."),
    force: bool = typer.Option(False, "--force", help="Kill immediately."),
):
    typer.echo(f"Stopping server (timeout={timeout}, force={force})")


@server_app.command()
@example(
    "Check server status",
    "",
)
def status():
    typer.echo("Server status: running")


# ── Docs generation command ───────────────────────────────────────────────────
#
# Shows to_markdown() and to_rst() — static doc generation from the live app.


@app.command(hidden=True)
def docs(
    fmt: str = typer.Option("markdown", "--format", "-f", help="markdown or rst"),
):
    resolved_vars = {
        "env": "staging",
        "version": "1.4.2",
        "db_url": "postgres://localhost/mydb",
    }
    if fmt == "rst":
        typer.echo(to_rst(app, vars=resolved_vars))
    else:
        typer.echo(to_markdown(app, vars=resolved_vars))


if __name__ == "__main__":
    app()
