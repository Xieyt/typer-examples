# typer-examples — Design Document

> A standalone library that adds beautiful, structured example rendering to Typer CLI help output via a decorator-first API.

---

## 1. Problem Statement

Typer has no built-in mechanism for attaching usage examples to commands. The standard workarounds are:

- **`epilog=` strings** — flat text only, no structured panels, layouts collapse in Typer's Rich path
- **Inline `help=` strings** — clutters the description, no visual separation
- **Manual `rich_format_help` monkey-patching** — works but requires per-project boilerplate and is not composable across libraries

The fm CLI (`frappe-manager`) built a working solution: a JSON file keyed by command paths, a module-level monkey-patch of `typer.rich_utils.rich_format_help`, and a Rich `Panel` renderer. It works well but is coupled to fm's internals and requires maintaining a separate `examples.json` alongside the command code.

`typer-examples` generalizes this pattern into a reusable, zero-dependency-overhead library with a decorator-first API.

---

## 2. Core Insight: Typer's Help Pipeline

Understanding why this library is non-trivial to implement correctly:

Typer's Rich help path is a **console-printing monolith**. `TyperCommand.format_help` calls `typer.rich_utils.rich_format_help(obj, ctx, markup_mode)` which prints directly to a Rich `Console` and returns `None`. Click's four sub-hooks (`format_usage`, `format_help_text`, `format_options`, `format_epilog`) are **never called** in the Rich path.

Consequences:
- `epilog=` on `@app.command()` renders as flat markup text — no panels, no tables
- Subclassing `TyperCommand` and overriding `format_epilog` does nothing when Rich is enabled
- The only reliable injection point is `typer.rich_utils.rich_format_help` itself
- The patch must be **chain-safe**: wrap the previous value rather than hardcoding the original, so multiple libraries can coexist

---

## 3. API Design

### 3.1 Primary API — Decorator

Examples live with the command that owns them. Co-location prevents drift.

```python
from typer_examples import example
import typer

app = typer.Typer()

@app.command()
@example(
    "Create with ERPNext and HRMS",
    "fm create {name} --apps erpnext --apps hrms",
)
@example(
    "Create production bench",
    "fm create {name} --env prod",
    detail="Sets nginx to serve directly and disables the Frappe debugger.",
)
def create(name: str, apps: list[str] = [], env: str = "dev"):
    ...
```

`desc` is the short heading — 5–8 words, imperative. `detail` is an optional second line that answers *why* or *when* to use this specific invocation — the thing the heading can't fit.

**Decorator ordering rule**: `@example` goes *below* `@app.command()` (closest to `def`). This ensures it runs before Typer processes the function, so `._typer_examples` is stored on the raw callable that Typer keeps as `command.callback`.

```python
@app.command()        # ← outer: Typer processes last, wraps the already-decorated fn
@example("...", "...")  # ← inner: runs first, attaches metadata to the raw fn
def my_command(...): ...
```

### 3.2 Install — Explicit, One Line

```python
from typer_examples import install

app = typer.Typer()
install(app)  # installs the chain-safe hook; idempotent
```

Call `install(app)` once, typically right after creating the root `typer.Typer()`. The `@example` decorator is free-standing (not bound to a specific app object), so it works cleanly across sub-apps and nested command groups.

### 3.3 Global Style Configuration

```python
from typer_examples import configure, ExamplesConfig

configure(ExamplesConfig(
    panel_title="Examples",
    heading_style="bold",
    detail_style="dim",
    syntax_highlight=True,
))
```

If `configure()` is never called, defaults produce the standard layout automatically.

---

## 4. Template Variable System

Examples often reference runtime context — a bench name, a domain, a version. The template system resolves `{name}` placeholders in example strings at render time.

### Resolution Priority (highest → lowest)

1. **Per-example kwargs** on the `@example(...)` decorator:
   ```python
   @example("Create bench", "fm create {name} --env prod", name="mybench")
   ```

2. **App-level defaults** set via `configure()`:
   ```python
   configure(vars={"name": "mybench", "domain": "example.com"})
   ```
   Values can also be **callables** evaluated lazily at render time — useful for dynamic data like a version read from a config file:
   ```python
   configure(vars={
       "name": "mybench",
       "version": lambda ctx: get_current_version(),   # called once per --help invocation
   })
   ```

3. **Auto-fill from `sys.argv`** (default behavior, no config needed):
   - Scans args before `--help` in `sys.argv`
   - Strips flags (`-*`) and known subcommand names
   - Maps remaining positional args to the command's `click.Argument` params in order
   - Example: `fm create mybench --help` → `{name}` = `"mybench"`
   - Falls back to param's `default` value if no arg was passed

4. **Param-name defaults** from the Click command's own parameter definitions:
   ```python
   # If name has default="myapp", {name} falls back to "myapp"
   def create(name: str = "myapp", ...): ...
   ```

### Positional Arg Auto-Detection

The library auto-detects which commands have positional arguments by inspecting `obj.params` at render time:

```python
positional_params = [p for p in obj.params if isinstance(p, click.Argument)]
```

No hardcoded `COMMANDS_WITHOUT_BENCHNAME` list needed. If a command has no `click.Argument` params, no positional injection happens.

---

## 5. Hook Architecture

### 5.1 Chain-Safe Monkey-Patch

```python
# typer_examples/_hook.py

import typer.rich_utils as ut

_MARKER = "_typer_examples_installed"

def install_hook():
    if getattr(ut, _MARKER, False):
        return  # idempotent — safe to call multiple times

    _upstream = ut.rich_format_help  # capture current value, not the original

    def _patched(*, obj, ctx, markup_mode):
        _upstream(obj=obj, ctx=ctx, markup_mode=markup_mode)  # always call upstream first
        _render_examples(obj, ctx)

    ut.rich_format_help = _patched
    setattr(ut, _MARKER, True)
```

Key properties:
- **Idempotent** — calling `install()` twice is safe
- **Chain-safe** — captures `_upstream` at install time, not the module original. If rich-click also patches `rich_format_help`, the chain is: `typer_examples → rich_click → typer_original`. Neither library clobbers the other.
- **Append-only** — always calls upstream first, then appends examples. Examples always appear last, after all standard help sections.

### 5.2 Example Lookup at Render Time

```python
def _render_examples(obj: click.Command, ctx: click.Context):
    examples = getattr(getattr(obj, "callback", None), "_typer_examples", None)

    if not examples:
        return

    _print_examples_panel(examples, obj, ctx)
```

---

## 6. Data Model

```python
# typer_examples/_models.py
from dataclasses import dataclass, field

@dataclass
class Example:
    desc: str                          # short heading: "Create with ERPNext and HRMS"
    code: str                          # CLI invocation (may contain {placeholders})
    detail: str = ""                   # optional second line — explains *why* or *when*
    vars: dict[str, str] = field(default_factory=dict)  # per-example template overrides

@dataclass
class ExamplesConfig:
    panel_title: str = "Examples"
    panel_border_style: str = ""       # empty = auto-match typer's STYLE_OPTIONS_PANEL_BORDER
    panel_padding: tuple = ()          # empty = auto-match typer's STYLE_OPTIONS_TABLE_PADDING
    title_align: str = ""              # empty = auto-match typer's ALIGN_OPTIONS_PANEL
    heading_style: str = "bold"        # style for the desc line
    detail_style: str = "dim"          # style for the optional detail line
    syntax_theme: str = "ansi_dark"    # Pygments theme passed to rich.syntax.Syntax
    syntax_highlight: bool = True      # shell-highlight the code line
    show_command_prefix: bool = True   # prepend full command path before example code
```

When `panel_border_style`, `panel_padding`, `title_align` are empty strings, the renderer reads them from `typer.rich_utils` at render time — automatically matching Typer's installed version and any user patches to those constants.

`detail` is intentionally optional — most examples don't need a second line. When omitted the heading sits directly above the code with no gap, keeping the panel compact.

---

## 7. Rendering

### Visual Layout

Each example renders as a 2-line block (3-line when `detail` is present), with a blank separator between examples:

```
╭─ Examples ──────────────────────────────────────────────────────────╮
│                                                                      │
│  Create with ERPNext and HRMS                                        │  ← desc  (bold)
│  $ fm create mybench --apps erpnext --apps hrms                      │  ← code  (Syntax bash)
│                                                                      │
│  Create production bench                                             │  ← desc  (bold)
│  Sets nginx to serve directly, disables the Frappe debugger.         │  ← detail (dim)  — optional
│  $ fm create mybench --env prod                                      │  ← code  (Syntax bash)
│                                                                      │
│  Open shell in nginx container as root                               │
│  $ fm shell mybench --service nginx --user root                      │
│                                                                      │
╰──────────────────────────────────────────────────────────────────────╯
```

Visual hierarchy deliberately mirrors kubectl/gh — the industry standard for developer tools:
- **desc** (bold) — the heading. Answers: *what is this example for?*
- **detail** (dim, optional) — the prose. Answers: *why or when would I use this?*
- **code** (Syntax bash) — the command. Always last; always copyable.

### Implementation

```python
# typer_examples/_renderer.py
from rich.console import Group
from rich.text import Text
from rich.syntax import Syntax
from rich.table import Table
from rich.panel import Panel

def _print_examples_panel(examples, obj, ctx):
    import typer.rich_utils as ut

    console = ut._get_rich_console()  # same console Typer uses
    config = _get_config()
    template_vars = _resolve_vars(obj, ctx)

    rows = []

    for i, ex in enumerate(examples):
        merged_vars = {**template_vars, **ex.vars}

        desc = ex.desc.format_map(_safe_format(merged_vars))
        code = _build_code(ex.code, obj, ctx, merged_vars, config)
        detail = ex.detail.format_map(_safe_format(merged_vars)) if ex.detail else None

        parts = []
        parts.append(Text(desc, style=config.heading_style))

        if detail:
            parts.append(Text(detail, style=config.detail_style))

        if config.syntax_highlight:
            parts.append(Syntax(
                f"$ {code}",
                "bash",
                theme=config.syntax_theme,
                background_color="default",  # ← no dark box; blends into Panel background
            ))
        else:
            parts.append(Text(f"$ {code}"))

        rows.append(Group(*parts))

        # blank line between examples, not after the last one
        if i < len(examples) - 1:
            rows.append(Text(""))

    console.print(Panel(
        Group(*rows),
        padding=config.panel_padding,
        border_style=config.panel_border_style,
        title=config.panel_title,
        title_align=config.title_align,
    ))
```

`background_color="default"` on `Syntax` is critical — without it Rich renders a dark-background box that clashes with the Panel border. With it, the highlighted code sits flush on the same background as the heading and detail lines.

`_safe_format` uses a `defaultdict`-style mapper so missing `{placeholder}` keys render as the literal string `{placeholder}` rather than raising `KeyError`.

---

## 8. Docs Generation API

The library exposes a first-class API for offline docs generation (same use case as fm's `scripts/update_cli_docs.py`):

```python
from typer_examples import get_all_examples

# Returns: dict mapping command path tuples to example lists
all_examples = get_all_examples(app)
# { ("create",): [Example(...)], ("ssl", "add"): [Example(...)] }
```

This walks `app.registered_commands` and `app.registered_groups` recursively, collecting examples from `command.callback._typer_examples`.

Format helpers for docs output:

```python
from typer_examples.docs import to_markdown, to_rst

md = to_markdown(app)   # returns str
rst = to_rst(app)       # returns str
```

---

## 9. Module Structure

```
typer_examples/
├── __init__.py       ← public API surface
├── _models.py        ← Example, ExamplesConfig dataclasses
├── _hook.py          ← chain-safe install_hook(), _render_examples()
├── _renderer.py      ← Rich Panel/Table builder
├── _providers.py     ← template variable resolution (sys.argv scan, lazy callables, defaults)
└── docs.py           ← get_all_examples(), to_markdown(), to_rst()
```

Public surface exported from `__init__.py`:

```python
from typer_examples import (
    example,          # decorator
    install,          # hook installer
    configure,        # global style config
    ExamplesConfig,   # config dataclass
    get_all_examples, # docs generation
)
```

---

## 10. Packaging

```toml
# pyproject.toml
[project]
name = "typer-examples"
version = "0.1.0"
description = "Beautiful example rendering for Typer CLI help output"
requires-python = ">=3.9"
dependencies = [
    "typer>=0.9.0",   # rich_utils API stable since 0.9
]

[project.optional-dependencies]
dev = ["pytest", "typer[all]"]
```

No new runtime dependencies. `rich` is already required by `typer[all]` and is a transitive dep in any project using Typer with Rich enabled. The library imports `rich` conditionally and degrades gracefully if Rich is not installed (no panel rendered, no error).

---

## 11. Compatibility

| Concern | Approach |
|---|---|
| Typer versions | Tested against Typer `0.9`, `0.10`, `0.12`. Pin `typer>=0.9` in deps. `rich_utils.rich_format_help` signature has been stable since 0.9. |
| rich-click coexistence | Chain-safe patch composes correctly. `typer_examples` appends after `rich_format_help` regardless of who else patched it. |
| No Rich installed | `install()` detects `HAS_RICH` from `typer.rich_utils`. Falls back silently — no examples panel, no crash. |
| Multiple `install()` calls | Idempotent via `_MARKER` attribute on `typer.rich_utils`. |
| Sub-apps | Hook is global (patches the module-level function). Works across all `typer.Typer()` instances in the same process without any additional setup. |

---

## 12. Resolved Design Decisions

| # | Topic | Decision |
|---|-------|----------|
| 1 | Syntax highlighting default | `True` — shell-highlighted code via `rich.syntax.Syntax(lexer="bash", background_color="default")` |
| 2 | Console for output | `typer.rich_utils._get_rich_console()` — same console Typer uses, consistent piping/redirect behaviour |
| 3 | Lazy callable vars | Supported — `configure(vars={"version": lambda ctx: ...})` evaluated at render time |
| 4 | Command prefix in examples | Auto-prepended from `ctx.command_path` by default, disable via `ExamplesConfig(show_command_prefix=False)` |
| 5 | Per-example layout | Three visual lines: **desc** (bold heading) → **detail** (dim prose, optional) → **code** (Syntax bash). Blank line between examples. Mirrors kubectl/gh pattern. |
| 6 | `$` prefix vs `▶` | `$` prefix on code lines — universally understood shell convention, immediately signals copy-paste intent |
