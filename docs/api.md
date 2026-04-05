# API Reference

## `example`

```python
def example(
    desc: str,
    code: str,
    detail: str = "",
    **vars: str,
) -> Callable
```

Decorator that attaches a usage example to a command function.

| Parameter | Type | Description |
|-----------|------|-------------|
| `desc` | `str` | Short heading (5–8 words, imperative). Shown in bold. |
| `code` | `str` | The CLI invocation string. May contain `{placeholder}` tokens. |
| `detail` | `str` | Optional prose line shown below the heading. Answers *why or when* to use this. |
| `**vars` | `str` | Per-example template variable overrides — highest priority in the resolution chain. |

Multiple `@example` decorators stack on the same function. They are rendered in the order they appear (top to bottom in source):

```python
@app.command()
@example("First example", "foo --flag")   # rendered first
@example("Second example", "foo --other") # rendered second
def foo(): ...
```

**Decorator order**: `@example` must be placed *below* `@app.command()` (closest to `def`). Reversing this order silently drops all examples.

---

## `install`

```python
def install(
    app: typer.Typer,
    config: Optional[ExamplesConfig] = None,
) -> None
```

Activates the `rich_format_help` hook and registers `app` with its config. Safe to call multiple times — subsequent calls on the same `app` are no-ops for the hook installation (idempotent).

| Parameter | Type | Description |
|-----------|------|-------------|
| `app` | `typer.Typer` | The Typer app to activate examples for. |
| `config` | `ExamplesConfig \| None` | Per-app config. Falls back to the global config set via `configure()`, then to built-in defaults. |

---

## `configure`

```python
def configure(config: ExamplesConfig) -> None
```

Sets the global fallback config used by apps that were `install()`-ed without an explicit config. Call once at application startup.

---

## `ExamplesConfig`

```python
@dataclass
class ExamplesConfig:
    panel_title: str = "Examples"
    heading_style: str = "bold"
    detail_style: str = "dim"
    syntax_theme: str = "ansi_dark"
    syntax_highlight: bool = True
    show_command_prefix: bool = True
    panel_border_style: Optional[str] = None
    panel_padding: Optional[tuple] = None
    title_align: Optional[str] = None
    vars: Dict[str, str | Callable[..., str]] = field(default_factory=dict)
```

| Field | Default | Description |
|-------|---------|-------------|
| `panel_title` | `"Examples"` | Panel header text. |
| `heading_style` | `"bold"` | Rich style for the example description line. |
| `detail_style` | `"dim"` | Rich style for the optional detail line. |
| `syntax_theme` | `"ansi_dark"` | Pygments theme for shell syntax highlighting. |
| `syntax_highlight` | `True` | Whether to syntax-highlight the code line. |
| `show_command_prefix` | `True` | Prepend `ctx.command_path` before the code string (e.g. `myapp deploy`). |
| `panel_border_style` | `None` | Border style. `None` = auto-match Typer's own border style at render time. |
| `panel_padding` | `None` | Panel padding. `None` = auto-match Typer's own padding. |
| `title_align` | `None` | Panel title alignment. `None` = auto-match Typer's own alignment. |
| `vars` | `{}` | App-level template variable defaults. Values can be strings or `Callable[[Context], str]`. |

See [configuration.md](configuration.md) for a full guide on global vs per-app config.

---

## `get_all_examples`

```python
def get_all_examples(
    app: typer.Typer,
) -> Dict[Tuple[str, ...], List[Example]]
```

Walks the app's registered commands and sub-apps, returning all attached examples keyed by command path.

```python
from typer_examples import get_all_examples

examples = get_all_examples(app)
# {
#   ("deploy",):        [Example(...), Example(...)],
#   ("db", "migrate"):  [Example(...)],
#   ("db", "seed"):     [Example(...), Example(...)],
# }
```

---

## `typer_examples.docs`

### `to_markdown`

```python
def to_markdown(
    app: typer.Typer,
    vars: Optional[Dict[str, str]] = None,
) -> str
```

Renders all examples on `app` to a Markdown string. Each command becomes an `##` heading; examples become bold headings with fenced `bash` code blocks.

`vars` is optional. Without it, `{placeholders}` are left as-is — useful when you want docs that show the template syntax rather than resolved values. When provided, `vars` are merged with each example's own per-example vars (per-example vars win).

```python
from typer_examples.docs import to_markdown

md = to_markdown(app, vars={"env": "staging", "version": "1.4.2"})
print(md)
```

### `to_rst`

```python
def to_rst(
    app: typer.Typer,
    vars: Optional[Dict[str, str]] = None,
) -> str
```

Same as `to_markdown`, but renders reStructuredText. Each command becomes a subsection heading; examples use `.. code-block:: bash` directives.
