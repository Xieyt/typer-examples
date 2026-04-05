# Configuration

`ExamplesConfig` controls the visual style and variable defaults for the examples panel. You can set it globally (as a project-wide fallback) or per-app (independent config on each `Typer()` instance).

## ExamplesConfig fields

```python
from typer_examples import ExamplesConfig

ExamplesConfig(
    panel_title="Examples",      # Panel header text
    heading_style="bold",        # Rich style applied to the example description line
    detail_style="dim",          # Rich style applied to the optional detail line
    syntax_theme="ansi_dark",    # Pygments theme used for shell syntax highlighting
    syntax_highlight=True,       # Whether to syntax-highlight the code line at all
    show_command_prefix=True,    # Prepend ctx.command_path before the code string
    panel_border_style=None,     # None = inherit Typer's own border style at render time
    panel_padding=None,          # None = inherit Typer's own panel padding
    title_align=None,            # None = inherit Typer's own title alignment
    vars={},                     # App-level template variable defaults (see below)
)
```

Fields set to `None` are read from `typer.rich_utils` at render time, so they automatically match whatever version of Typer (and any Rich theme) is installed.

### `vars`

A dict mapping placeholder names to values. Values can be plain strings or **callables** — the callable receives the Click `Context` and is called once per `--help` invocation:

```python
ExamplesConfig(vars={
    "env": "staging",
    "version": lambda ctx: read_version_from_pyproject(),
})
```

## Global config

`configure()` sets a project-wide fallback used by every app that does not have its own config:

```python
from typer_examples import ExamplesConfig, configure

configure(ExamplesConfig(
    panel_title="Examples",
    syntax_theme="monokai",
    vars={"env": "staging"},
))
```

Call `configure()` once at application startup, before any `--help` is rendered. All apps that were `install()`-ed without an explicit config will use it.

## Per-app config

Pass a config directly to `install()` to scope it to a single `Typer()` instance. Commands in that app use their app's config — not the global fallback and not the root app's config.

```python
import typer
from typer_examples import ExamplesConfig, example, install

app = typer.Typer()
install(app, config=ExamplesConfig(
    panel_title="Platform Examples",
    vars={"env": "staging", "version": "1.4.2"},
))

db_app = typer.Typer()
install(db_app, config=ExamplesConfig(
    panel_title="DB Examples",
    syntax_theme="monokai",
    vars={"db_url": "postgres://localhost/mydb"},
))
app.add_typer(db_app, name="db")

@app.command()
@example("Deploy to staging", "{env} --tag {version}")
def deploy(env: str, tag: str = typer.Option("latest")): ...

@db_app.command()
@example("Run pending migrations", "--url {db_url}")
def migrate(url: str = typer.Option(..., help="Database URL.")): ...
```

```
$ python myapp.py deploy --help
╭─ Platform Examples ─╮   ← root app's config

$ python myapp.py db migrate --help
╭─ DB Examples ───────╮   ← db_app's config; {db_url} resolved from db_app's vars
```

See [`examples/app.py`](../examples/app.py) for a full working demo with root app, two sub-apps, per-example overrides, and docs generation.

## Config resolution order

When rendering examples for a command, the config is resolved as follows:

1. Config explicitly passed to `install(app, config=...)` for the app that owns the command
2. Global fallback set via `configure()`
3. Built-in defaults (`panel_title="Examples"`, `syntax_theme="ansi_dark"`, etc.)
