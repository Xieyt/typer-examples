"""Data models for typer-examples."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Tuple, Union


@dataclass
class Example:
    """A single CLI usage example attached to a command.

    Attributes:
        desc:   Short heading (5-8 words, imperative). Answers: *what is this example for?*
        code:   The CLI invocation string. May contain ``{placeholder}`` template variables.
        detail: Optional prose line. Answers: *why or when to use this invocation?*
        vars:   Per-example template variable overrides (highest priority in resolution chain).
    """

    desc: str
    code: str
    detail: str = ""
    vars: Dict[str, str] = field(default_factory=dict)


# Template var values can be a plain string or a lazy callable(ctx) -> str
VarValue = Union[str, Callable[..., str]]


@dataclass
class ExamplesConfig:
    """Global rendering configuration for typer-examples.

    All style fields default to empty string, which means the renderer auto-matches
    the values Typer itself uses (read from ``typer.rich_utils`` at render time).
    """

    panel_title: str = "Examples"
    panel_border_style: str = (
        ""  # empty → auto-match typer's STYLE_OPTIONS_PANEL_BORDER
    )
    panel_padding: Tuple[
        Any, ...
    ] = ()  # empty → auto-match typer's STYLE_OPTIONS_TABLE_PADDING
    title_align: str = ""  # empty → auto-match typer's ALIGN_OPTIONS_PANEL
    heading_style: str = "bold"  # Rich style for the desc line
    detail_style: str = "dim"  # Rich style for the optional detail line
    syntax_theme: str = "ansi_dark"  # Pygments theme passed to rich.syntax.Syntax
    syntax_highlight: bool = (
        True  # shell-highlight the code line via rich.syntax.Syntax
    )
    show_command_prefix: bool = True  # prepend ctx.command_path before example code
    vars: Dict[str, VarValue] = field(
        default_factory=dict
    )  # app-level template defaults
