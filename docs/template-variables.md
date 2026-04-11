# Template Variables

Example code strings can contain `{placeholder}` tokens that are resolved at render time. The resolution chain runs in priority order — the first source that supplies a value wins.

## Resolution order

```
sys.argv  →  per-example kwargs  →  app-level vars  →  parameter defaults
(highest)                                                     (lowest)
```

### 1. Auto-fill from `sys.argv`

Positional arguments already present in `sys.argv` before `--help` are automatically mapped to their parameter names and always win — even over per-example kwargs. No code changes needed.

```bash
myapp deploy staging --help
#                ↑
# {env} is resolved to "staging" because "staging" appears
# in the position matching the `env` parameter.
```

This lets users see contextually relevant examples when they're already mid-command. Per-example kwargs serve as the fallback value shown when no positional is present.

### 2. Per-example kwargs

Pass keyword arguments directly to `@example()`. They are used when no value was typed in `sys.argv` and override app-level vars and parameter defaults.

```python
@example("Run in production", "{env} --fast", env="production")
@example("Run in staging", "{env} --fast", env="staging")
def deploy(env: str): ...
```

### 3. App-level vars

Set variable defaults on the `ExamplesConfig` passed to `install()`. Every example on that app uses these unless a per-example kwarg or argv overrides them.

```python
from typer_examples import ExamplesConfig, install

install(app, config=ExamplesConfig(vars={
    "env": "staging",
    "version": "1.4.2",
}))
```

Values can also be **callables** — evaluated lazily once per `--help` invocation. The callable receives the Click `Context`:

```python
install(app, config=ExamplesConfig(vars={
    "version": lambda ctx: read_version_from_pyproject(),
    "user": lambda ctx: ctx.obj.get("username") if ctx.obj else "alice",
}))
```

This is useful for values that aren't known at import time (e.g. config file contents, environment variables, authenticated user names).

### 4. Parameter defaults

If none of the above supply a value, the Click parameter's own `default=` is used as a final fallback:

```python
@app.command()
@example("List recent events", "--limit {limit}")
def events(limit: int = typer.Option(20, help="Max results.")): ...
# {limit} → "20" from the parameter default
```

## Safe rendering

Unknown placeholders — ones that aren't resolved by any tier — are left as `{placeholder}` in the output rather than raising `KeyError`. This means partial resolution always produces readable output:

```
$ myapp deploy --help

╭─ Examples ──────────────────╮
│ $ myapp deploy {env} --fast │  ← {env} unresolved, shown as-is
╰─────────────────────────────╯
```

## Scope isolation

Each `Typer()` instance has its own `vars` dict. A sub-app's vars are not visible to the root app, and vice versa.

```python
install(app, config=ExamplesConfig(vars={"env": "staging"}))
install(db_app, config=ExamplesConfig(vars={"db_url": "postgres://localhost/mydb"}))

# {db_url} is only resolved for commands registered on db_app.
# Commands on the root app will leave {db_url} as-is.
```
