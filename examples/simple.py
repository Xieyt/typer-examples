import typer
from typer_examples import example, install

app = typer.Typer(name="deploy")
install(app)


@app.command()
@example(
    "Deploy to staging with a specific tag",
    "{env} --tag {version}",
    env="staging",
    version="1.4.2",
)
@example(
    "Deploy to production and skip confirmation",
    "{env} --tag {version} --yes",
    detail="Use --yes in CI pipelines to avoid interactive prompts.",
    env="production",
    version="1.4.2",
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
    "Stream logs from a specific service",
    "{env} --service api --follow",
    detail="Streams live output until you press Ctrl-C.",
    env="staging",
)
def logs(
    env: str,
    service: str = typer.Option("web", help="Service name to read logs from."),
    tail: int = typer.Option(100, help="Number of lines to show."),
    follow: bool = typer.Option(False, "--follow", "-f", help="Stream live output."),
):
    typer.echo(f"Logs for {service!r} in {env!r} (tail={tail}, follow={follow})")


@app.command()
@example(
    "Open a shell in the web container",
    "{env} --service web",
    env="staging",
)
@example(
    "Run a one-off command as root",
    "{env} --service worker --user root --command 'pip list'",
    detail="Useful for inspecting installed packages inside a container.",
    env="staging",
)
def shell(
    env: str,
    service: str = typer.Option("web", help="Container service to connect to."),
    user: str = typer.Option("app", help="User to run as inside the container."),
    command: str = typer.Option(
        "", "--command", "-c", help="Command to run instead of interactive shell."
    ),
):
    typer.echo(f"Connecting to {service!r} in {env!r} as {user!r}")


if __name__ == "__main__":
    app()
