# How It Works

This document explains the internal mechanics of `typer-examples` — how the hook is installed, how the app-to-config registry works, and how examples are rendered at help time.

---

## Why `rich_format_help`?

Typer's `--help` output is produced entirely by `typer.rich_utils.rich_format_help()`. This function renders directly to a Rich console and returns `None` — it never passes through Click's standard `format_help` / `format_epilog` path.

That means the only reliable injection point is `rich_format_help` itself. There is no Click hook, no epilog override, and no subclassing path that works reliably across all supported Typer versions.

---

## The Patch Mechanism

`install()` wraps the current value of `rich_format_help` using a closure. The original is always captured first and called first — making the patch **chain-safe**:

```python
# Simplified from typer_examples/_hook.py

_upstream = typer.rich_utils.rich_format_help

def _patched(*, obj: click.Command, ctx: click.Context, markup_mode: str) -> None:
    _upstream(obj=obj, ctx=ctx, markup_mode=markup_mode)  # always runs first
    _render_examples(obj, ctx)                            # appended after

typer.rich_utils.rich_format_help = _patched
```

A sentinel attribute (`_typer_examples_installed`) is set on the module after patching, so calling `install()` multiple times has no effect — the patch is only applied once.

### Properties

| Property | Behaviour |
|----------|-----------|
| **Idempotent** | Calling `install()` N times applies the patch exactly once |
| **Chain-safe** | Captures and calls whatever `rich_format_help` currently is — composes safely with `rich-click` or any other patch applied before or after |
| **Append-only** | Examples panel always appears *after* all standard help sections |
| **Graceful degradation** | If `rich` is not installed, `install()` returns immediately without patching or raising |

---

## App-to-Config Registry

Each `Typer()` instance can carry its own `ExamplesConfig`. The registry is a `WeakKeyDictionary` keyed by the `Typer` app object, so registrations are automatically garbage-collected when an app goes out of scope:

```python
# typer_examples/_hook.py

_app_config_map: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

def register_app(app: Any, cfg: ExamplesConfig) -> None:
    _app_config_map[app] = cfg
```

`install(app, config=cfg)` calls `register_app(app, cfg)` and then calls `install_hook()` (which is a no-op after the first call).

### Config Lookup at Render Time

When `_render_examples` fires for a command, it needs to find which config to use. It walks the registered apps and checks whether the command's callback belongs to any of them:

```python
def _get_config_for_callback(callback: Any) -> ExamplesConfig:
    # unwrap Typer's wrapper layers to get the original function
    original = callback
    while hasattr(original, "__wrapped__"):
        original = original.__wrapped__

    for app, cfg in list(_app_config_map.items()):
        if _app_directly_has_callback(app, original):
            return cfg

    return _config  # fall back to global config
```

`_app_directly_has_callback` iterates `app.registered_commands` and matches by identity — no name matching or string comparison. If no registered app claims the callback, the global `ExamplesConfig` instance is used.

---

## Rendering Pipeline

Once the config is resolved, `_render_examples` hands off to `print_examples_panel` in `_renderer.py`. The rendering steps are:

1. **Acquire console** — uses `typer.rich_utils._get_rich_console()` so output goes to the same stream Typer uses (respects `NO_COLOR`, redirections, etc.)

2. **Resolve template variables** — calls `resolve_vars(obj, ctx, config.vars)` which builds the variable namespace from four tiers (see [Template Variables](template-variables.md)):
   - Per-example `kwargs` (highest priority)
   - App-level `config.vars`
   - `sys.argv` tokens
   - Click parameter defaults (lowest priority)

3. **Build rows** — for each `Example`:
   - `safe_format_map(ex.desc, merged_vars)` → description line
   - `safe_format_map(ex.detail, merged_vars)` → optional detail line
   - `_build_code(ex.code, ...)` → resolves the command string and optionally prepends `ctx.command_path` if `show_command_prefix=True`

4. **Syntax highlight** — if `config.syntax_highlight=True`, the command string is wrapped in a `rich.syntax.Syntax` block with `language="bash"` and `background_color="default"` (inherits terminal background)

5. **Print panel** — all rows are grouped into a `rich.panel.Panel` with title, border style, padding, and alignment taken from `ExamplesConfig` (falling back to Typer's own style constants when `None`)

---

## Safe Formatting

`safe_format_map` is a thin wrapper around `str.format_map` that silently leaves `{unknown}` placeholders as-is rather than raising `KeyError`. This means partially-resolved templates still render cleanly:

```python
safe_format_map("$ deploy {env} --tag {version}", {"env": "staging"})
# → "$ deploy staging --tag {version}"
```

No example is ever suppressed due to a missing variable — the raw placeholder is shown instead.

---

## Example Metadata Storage

`@example(...)` attaches metadata to the decorated function via a `_typer_examples` attribute:

```python
# Appended by each @example call, in bottom-up decorator order
func._typer_examples: List[Example]
```

`_render_examples` reads this attribute from `obj.callback` (the Click command's callback). If the attribute is absent or empty, the function returns early — no panel is printed.

---

## Sequence Diagram

```
user runs: myapp deploy --help
    │
    ▼
click.BaseCommand.main()
    │
    ▼
typer.rich_utils.rich_format_help()   ← patched by install_hook()
    │
    ├─► _upstream(obj, ctx, markup_mode)    # original Typer help output
    │
    └─► _render_examples(obj, ctx)
            │
            ├─► _get_config_for_callback(obj.callback)
            │       └─► WeakKeyDictionary lookup → ExamplesConfig
            │
            └─► print_examples_panel(examples, obj, ctx, config)
                    │
                    ├─► resolve_vars(obj, ctx, config.vars)
                    ├─► safe_format_map(desc / detail / code, vars)
                    └─► console.print(Panel(...))
```
