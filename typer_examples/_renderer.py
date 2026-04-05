from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    import click

from rich.console import Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from ._hook import get_config
from ._models import Example
from ._providers import resolve_vars, safe_format_map


def print_examples_panel(
    examples: List[Example],
    obj: "click.Command",
    ctx: "click.Context",
) -> None:
    import typer.rich_utils as ut

    console = ut._get_rich_console()  # type: ignore[attr-defined]
    config = get_config()
    template_vars = resolve_vars(obj, ctx, config.vars)

    border_style = config.panel_border_style or getattr(
        ut, "STYLE_OPTIONS_PANEL_BORDER", "dim"
    )
    padding = config.panel_padding or getattr(ut, "STYLE_OPTIONS_TABLE_PADDING", (0, 1))
    title_align = config.title_align or getattr(ut, "ALIGN_OPTIONS_PANEL", "left")

    rows = []

    for i, ex in enumerate(examples):
        merged_vars = {**template_vars, **ex.vars}

        desc = safe_format_map(ex.desc, merged_vars)
        code = _build_code(ex.code, obj, ctx, merged_vars, config)
        detail = safe_format_map(ex.detail, merged_vars) if ex.detail else None

        parts: list = [Text(desc, style=config.heading_style)]

        if detail:
            parts.append(Text(detail, style=config.detail_style))

        if config.syntax_highlight:
            parts.append(
                Syntax(
                    f"$ {code}",
                    "bash",
                    theme=config.syntax_theme,
                    background_color="default",
                )
            )
        else:
            parts.append(Text(f"$ {code}"))

        rows.append(Group(*parts))

        if i < len(examples) - 1:
            rows.append(Text(""))

    console.print(
        Panel(
            Group(*rows),
            padding=padding,
            border_style=border_style,
            title=config.panel_title,
            title_align=title_align,
        )
    )


def _build_code(
    code: str,
    obj: "click.Command",
    ctx: "click.Context",
    vars: dict,
    config: object,
) -> str:
    from ._models import ExamplesConfig

    assert isinstance(config, ExamplesConfig)
    resolved = safe_format_map(code, vars)
    if config.show_command_prefix:
        prefix = ctx.command_path
        resolved = f"{prefix} {resolved}".strip()
    return resolved
