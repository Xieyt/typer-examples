# typer-examples

Beautiful, structured example rendering for [Typer](https://typer.tiangolo.com/) CLI help output.

```
╭─ Examples ──────────────────────────────────────────────────────────╮
│ Deploy to staging with a pinned tag                                  │
│ Pulls the image, runs migrations, and restarts services.             │
│ $ myapp deploy staging --tag 1.4.2                                   │
│                                                                      │
│ Deploy to production and skip confirmation                           │
│ Pass --yes in CI pipelines to avoid interactive prompts.             │
│ $ myapp deploy production --tag 2.0.0 --yes                          │
╰──────────────────────────────────────────────────────────────────────╯
```

---

## The problem

Typer has no built-in way to attach usage examples to commands. The common workarounds — `epilog=` strings, inline `help=` text — produce flat, unstructured output with no visual separation. `typer-examples` solves this with a decorator-first API that keeps examples co-located with the command they document.

---

## Installation

```bash
uv add typer-examples
# or
pip install typer-examples
```

Requires Python ≥ 3.9 and Typer ≥ 0.9. `rich` is a transitive dependency of `typer[all]` and is all that's needed for the panel renderer.

---

## Quick start

```python
import typer
from typer_examples import example, install

app = typer.Typer()
install(app)

@app.command()
@example(
    "Deploy to staging with a pinned tag",
    "{env} --tag {version}",
    env="staging",
    version="1.4.2",
    detail="Pulls the image, runs migrations, and restarts services.",
)
@example(
    "Deploy to production and skip confirmation",
    "{env} --tag {version} --yes",
    env="production",
    version="2.0.0",
    detail="Pass --yes in CI pipelines to avoid interactive prompts.",
)
def deploy(env: str, tag: str = typer.Option("latest"), yes: bool = False):
    ...

if __name__ == "__main__":
    app()
```

Run `python myapp.py deploy --help` to see the examples panel appended after the standard help output.

**Decorator ordering**: `@example` must go *below* `@app.command()` (closest to `def`). This ensures the metadata is attached to the raw callable before Typer wraps it.

---

## Template variables

Example code strings can contain `{placeholder}` tokens that are resolved at render time. Resolution priority (highest → lowest):

### 1. Per-example kwargs

Pass keyword arguments directly to `@example()`. They override everything else for that specific example.

```python
@example("Run in production", "{env} --fast", env="production")
```

### 2. App-level vars

Set defaults on the `ExamplesConfig` passed to `install()`. Every example on that app uses these unless overridden.

```python
from typer_examples import ExamplesConfig, install

install(app, config=ExamplesConfig(vars={"env": "staging", "version": "1.4.2"}))
```

Values can also be **callables** — evaluated lazily once per `--help` invocation:

```python
install(app, config=ExamplesConfig(vars={
    "version": lambda ctx: read_version_from_config(),
}))
```

### 3. Auto-fill from `sys.argv`

Positional arguments already present in `sys.argv` before `--help` are automatically mapped to their parameter names.

```bash
myapp deploy staging --help
# → {env} resolved to "staging" automatically
```

### 4. Parameter defaults

If none of the above supply a value, the Click parameter's own `default=` is used as a fallback.

### Safe rendering

Unknown placeholders are left as `{placeholder}` rather than raising `KeyError`, so partial resolution always produces readable output.

---

## Configuration

`ExamplesConfig` controls the visual style of the panel. Pass it to `install()` for per-app config, or to `configure()` for a global default.

```python
from typer_examples import ExamplesConfig, configure

configure(ExamplesConfig(
    panel_title="Examples",        # panel header text
    heading_style="bold",          # Rich style for the desc line
    detail_style="dim",            # Rich style for the detail line
    syntax_theme="ansi_dark",      # Pygments theme for code highlighting
    syntax_highlight=True,         # shell-highlight the code line
    show_command_prefix=True,      # prepend ctx.command_path before code
    panel_border_style=None,       # None = auto-match Typer's border style
    panel_padding=None,            # None = auto-match Typer's panel padding
    title_align=None,              # None = auto-match Typer's title alignment
    vars={},                       # app-level template variable defaults
))
```

Style fields set to `None` are read from `typer.rich_utils` at render time, so they automatically match whatever version of Typer (and any Rich theme) you have installed.

---

## Per-app config (sub-apps)

Each `typer.Typer()` instance can have its own independent config. Commands in a sub-app pick up that sub-app's config — not the root app's.

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
╭─ Platform Examples ─╮   ← root app's panel_title

$ python myapp.py db migrate --help
╭─ DB Examples ───────╮   ← db_app's panel_title, db_url resolved from db_app's vars
```

See [`examples/app.py`](examples/app.py) for a full working demo with root app, two sub-apps, per-example overrides, and docs generation.

---

## Docs generation

Generate static documentation from the live app — useful for CI docs pipelines.

```python
from typer_examples import get_all_examples
from typer_examples.docs import to_markdown, to_rst

# Dict mapping command path tuples to example lists
all_examples = get_all_examples(app)
# { ("deploy",): [...], ("db", "migrate"): [...] }

# Rendered strings — pass vars= to resolve placeholders
md = to_markdown(app, vars={"env": "staging", "version": "1.4.2"})
rst = to_rst(app, vars={"env": "staging", "version": "1.4.2"})
```

`vars` is optional. Without it, `{placeholders}` are left as-is — useful when you want docs that show the template syntax rather than resolved values.

---

## How it works

Typer's Rich help path calls `typer.rich_utils.rich_format_help()` directly and returns `None`. Click's standard `format_epilog` hook is never reached. The only reliable injection point is `rich_format_help` itself.

`install()` wraps the current value of `rich_format_help` (chain-safe — whatever else may have patched it):

```python
_upstream = typer.rich_utils.rich_format_help

def _patched(*, obj, ctx, markup_mode):
    _upstream(obj=obj, ctx=ctx, markup_mode=markup_mode)  # always first
    _render_examples(obj, ctx)                             # appended after

typer.rich_utils.rich_format_help = _patched
```

Properties:
- **Idempotent** — calling `install()` multiple times is safe
- **Chain-safe** — composes correctly with `rich-click` or any other patch
- **Append-only** — examples always appear after all standard help sections
- **Graceful degradation** — if `rich` is not installed, `install()` returns silently with no error

---

## Public API

```python
from typer_examples import (
    example,          # decorator — attaches examples to a command function
    install,          # activates the hook; accepts optional per-app ExamplesConfig
    configure,        # sets the global fallback config
    ExamplesConfig,   # dataclass for all style and template options
    get_all_examples, # walks app tree → dict of (path tuple) → [Example]
)

from typer_examples.docs import (
    to_markdown,      # app → Markdown string
    to_rst,           # app → reStructuredText string
)
```

---

## Examples

| File | What it shows |
|------|---------------|
| [`examples/simple.py`](examples/simple.py) | Minimal single-app setup with per-example vars |
| [`examples/app.py`](examples/app.py) | Root app + two sub-apps, per-app config, app-level vars, docs generation |

```bash
# Run the examples
uv run python examples/simple.py deploy --help
uv run python examples/app.py db migrate --help
uv run python examples/app.py server start --help
uv run python examples/app.py docs
uv run python examples/app.py docs --format rst
```

---

## Compatibility

| Typer | Python | rich-click |
|-------|--------|------------|
| ≥ 0.9 | 3.9 – 3.12 | Supported (chain-safe patch) |

`rich_utils.rich_format_help` has been stable since Typer 0.9. The patch composes correctly with `rich-click` — both libraries append to the help output without clobbering each other.

---

## License

MIT
