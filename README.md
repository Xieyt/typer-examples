# typer-examples

[![CI](https://github.com/Xieyt/typer-examples/actions/workflows/ci.yml/badge.svg)](https://github.com/Xieyt/typer-examples/actions/workflows/ci.yml)
[![Typer Compatibility](https://github.com/Xieyt/typer-examples/actions/workflows/typer-compat.yml/badge.svg)](https://github.com/Xieyt/typer-examples/actions/workflows/typer-compat.yml)
[![Python](https://img.shields.io/badge/python-3.9--3.12-blue)](#compatibility)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](#license)

Attach structured, syntax-highlighted usage examples to [Typer](https://typer.tiangolo.com/) commands. They appear automatically in `--help` output as a Rich panel — no subclassing, no epilog hacks.

```
 Usage: myapp deploy [OPTIONS] ENV

╭─ Options ──────────────────────────────────────────────────────────╮
│ --tag    TEXT  Docker image tag to deploy.  [default: latest]      │
│ --yes          Skip confirmation prompt.                           │
│ --help         Show this message and exit.                         │
╰────────────────────────────────────────────────────────────────────╯
╭─ Examples ─────────────────────────────────────────────────────────╮
│ Deploy to staging with a pinned tag                                │
│ Pulls the image, runs migrations, and restarts services.           │
│ $ myapp deploy staging --tag 1.4.2                                 │
│                                                                    │
│ Deploy to production and skip confirmation                         │
│ Pass --yes in CI pipelines to avoid interactive prompts.           │
│ $ myapp deploy production --tag 2.0.0 --yes                        │
╰────────────────────────────────────────────────────────────────────╯
```

## Installation

```bash
pip install typer-examples
# or
uv add typer-examples
```

Requires Python ≥ 3.9 and Typer ≥ 0.9.

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

> **Decorator order**: `@example` must sit *below* `@app.command()` — closest to `def`. This ensures the metadata is attached to the raw function before Typer wraps it.

## Features

- **Decorator-first** — examples live next to the command, not buried in docstrings or epilog strings
- **Template variables** — `{placeholders}` resolved from per-example kwargs, app-level defaults, `sys.argv`, or Click parameter defaults → [details](docs/template-variables.md)
- **Per-app config** — each `Typer()` instance gets its own panel title, style theme, and variable defaults → [details](docs/configuration.md)
- **Docs generation** — export all examples to Markdown or reStructuredText for CI doc pipelines → [API](docs/api.md)
- **Chain-safe** — composes with `rich-click` and any other `rich_format_help` patch without clobbering
- **Graceful degradation** — if `rich` is absent, `install()` returns silently with no error

## Documentation

| Topic | |
|-------|--|
| [Template variables](docs/template-variables.md) | Resolution chain: per-example → app-level → argv → defaults |
| [Configuration](docs/configuration.md) | `ExamplesConfig` fields, global config, per-app config for sub-commands |
| [API reference](docs/api.md) | Full public API with signatures and return types |
| [How it works](docs/how-it-works.md) | Internal implementation and the `rich_format_help` hook |

## Try the examples

```bash
# Minimal single-app setup — three commands, each with examples
uv run python examples/simple.py deploy --help
uv run python examples/simple.py logs --help
uv run python examples/simple.py shell --help

# Root app + two sub-apps with independent per-app config
uv run python examples/app.py deploy --help
uv run python examples/app.py db migrate --help
uv run python examples/app.py server start --help

# Static docs generation
uv run python examples/app.py docs
uv run python examples/app.py docs --format rst
```

## Compatibility

| Typer | Python | rich-click |
|-------|--------|------------|
| ≥ 0.9 | 3.9 – 3.12 | Supported |

Compatibility is verified daily across all supported Typer × Python combinations in CI.

## License

MIT
